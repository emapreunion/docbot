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

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

BOT_NAME = os.environ.get("BOT_NAME", "DocBot")
SYSTEM_PROMPT = os.environ.get("SYSTEM_PROMPT", (
    "Tu es Emap Bot, un assistant intégré à l'EMAP (École des Métiers de l'Action et du Projet social). "
    "Tu fais partie de l'équipe et tu parles en tant que membre de l'institution, pas comme un outil externe. "
    "Tu disposes d'informations complètes sur les formations et les diplômes d'État (DE) proposés par l'EMAP : "
    "conditions d'accès, contenus de formation, durées, modalités de certification, etc. "
    "Réponds UNIQUEMENT en français, à la première personne, comme si ces informations t'appartenaient. "
    "Par exemple, dis 'Nos formations durent...' ou 'À l'EMAP, nous proposons...' plutôt que 'D'après les documents...'. "
    "Si une information ne figure pas dans tes données, dis-le avec bienveillance en invitant à contacter l'équipe. "
    "Sois précis, chaleureux et professionnel."
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
    if not GROQ_API_KEY:
        return jsonify({"error": "Clé API Groq manquante sur le serveur."}), 500

    data = request.get_json()
    question = (data.get("message") or "").strip()
    history  = data.get("history") or []

    if not question:
        return jsonify({"error": "Message vide."}), 400

    if not SOURCES_CONTEXT:
        return jsonify({"error": "Aucune source chargée sur le serveur."}), 500

    # System message avec le contexte complet
    system_message = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Voici les documents et sources à ta disposition :\n\n"
        f"{SOURCES_CONTEXT[:60000]}\n\n"
        f"---\nRéponds uniquement en français."
    )

    # Construction des messages (format OpenAI compatible)
    messages = [{"role": "system", "content": system_message}]

    # Ajout de l'historique (max 10 derniers échanges)
    for msg in history[-10:]:
        role = "assistant" if msg["role"] == "assistant" else "user"
        messages.append({"role": role, "content": msg["content"]})

    # Question actuelle
    messages.append({"role": "user", "content": question})

    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 2048,
    }

    try:
        resp = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=30
        )
        resp.raise_for_status()
        result = resp.json()
        answer = result["choices"][0]["message"]["content"]
        return jsonify({"answer": answer})
    except requests.exceptions.HTTPError as e:
        err = resp.json().get("error", {}).get("message", str(e))
        return jsonify({"error": f"Erreur Groq : {err}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
