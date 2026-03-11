import os
import glob
import requests
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

# --- PDF
import pdfplumber

# --- DOCX
from docx import Document as DocxDocument

# --- Web scraping
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

BOT_NAME = os.environ.get("BOT_NAME", "DocBot")
SYSTEM_PROMPT = os.environ.get("SYSTEM_PROMPT", (
    "Tu es un assistant documentaire. "
    "Réponds UNIQUEMENT en français. "
    "Réponds aux questions en te basant exclusivement sur les documents et sources fournis. "
    "Si la réponse n'est pas dans les sources, dis-le clairement. "
    "Sois précis, structuré et bienveillant."
))

# ── Chargement des sources au démarrage ──────────────────────────────────────

SOURCES_CONTEXT = ""

def load_pdf(path):
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
    return text

def load_docx(path):
    doc = DocxDocument(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

def load_url(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)

def build_context():
    global SOURCES_CONTEXT
    parts = []

    # Fichiers dans /docs
    docs_dir = os.path.join(os.path.dirname(__file__), "docs")
    for path in glob.glob(os.path.join(docs_dir, "**"), recursive=True):
        if not os.path.isfile(path):
            continue
        name = os.path.basename(path)
        ext = name.rsplit(".", 1)[-1].lower()
        try:
            if ext == "pdf":
                content = load_pdf(path)
                parts.append(f"=== DOCUMENT PDF : {name} ===\n{content}")
                print(f"[OK] PDF chargé : {name} ({len(content)} caractères)")
            elif ext in ("docx", "doc"):
                content = load_docx(path)
                parts.append(f"=== DOCUMENT WORD : {name} ===\n{content}")
                print(f"[OK] DOCX chargé : {name} ({len(content)} caractères)")
            elif ext == "txt":
                with open(path, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                parts.append(f"=== DOCUMENT TEXTE : {name} ===\n{content}")
                print(f"[OK] TXT chargé : {name}")
        except Exception as e:
            print(f"[ERREUR] {name} : {e}")

    # URLs définies en variable d'environnement (séparées par des virgules)
    urls_env = os.environ.get("SOURCE_URLS", "")
    if urls_env:
        for url in [u.strip() for u in urls_env.split(",") if u.strip()]:
            try:
                content = load_url(url)
                # Limite à 20 000 caractères par URL
                content = content[:20000]
                parts.append(f"=== SOURCE WEB : {url} ===\n{content}")
                print(f"[OK] URL chargée : {url} ({len(content)} caractères)")
            except Exception as e:
                print(f"[ERREUR] URL {url} : {e}")

    SOURCES_CONTEXT = "\n\n".join(parts)
    total = len(SOURCES_CONTEXT)
    print(f"\n✅ Contexte total : {total} caractères depuis {len(parts)} source(s)\n")

# Chargement au démarrage
build_context()

# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", bot_name=BOT_NAME)

@app.route("/status")
def status():
    sources_count = SOURCES_CONTEXT.count("===") // 2
    return jsonify({
        "ok": bool(SOURCES_CONTEXT),
        "sources": sources_count,
        "chars": len(SOURCES_CONTEXT)
    })

@app.route("/chat", methods=["POST"])
def chat():
    if not GEMINI_API_KEY:
        return jsonify({"error": "Clé API Gemini manquante sur le serveur."}), 500

    data = request.get_json()
    question = (data.get("message") or "").strip()
    history = data.get("history") or []

    if not question:
        return jsonify({"error": "Message vide."}), 400

    if not SOURCES_CONTEXT:
        return jsonify({"error": "Aucune source chargée sur le serveur."}), 500

    # Construction du prompt avec contexte
    context_message = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Voici les documents et sources à ta disposition :\n\n"
        f"{SOURCES_CONTEXT[:60000]}\n\n"  # limite sécurité
        f"---\nRéponds uniquement en français."
    )

    # Historique Gemini
    contents = []

    # Injection du contexte dans le premier message utilisateur
    if history:
        first = history[0]
        contents.append({
            "role": "user",
            "parts": [{"text": context_message + "\n\nQuestion : " + first.get("content", "")}]
        })
        if len(history) > 1:
            for msg in history[1:]:
                role = "model" if msg["role"] == "assistant" else "user"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})
    else:
        contents.append({
            "role": "user",
            "parts": [{"text": context_message + "\n\nQuestion : " + question}]
        })

    # Si on a déjà un historique, ajouter la nouvelle question
    if history:
        contents.append({"role": "user", "parts": [{"text": question}]})

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2048,
        }
    }

    try:
        resp = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            json=payload,
            timeout=30
        )
        resp.raise_for_status()
        result = resp.json()
        answer = result["candidates"][0]["content"]["parts"][0]["text"]
        return jsonify({"answer": answer})
    except requests.exceptions.HTTPError as e:
        err = resp.json().get("error", {}).get("message", str(e))
        return jsonify({"error": f"Erreur Gemini : {err}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
