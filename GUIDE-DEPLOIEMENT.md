# 📖 GUIDE DE DÉPLOIEMENT — DocBot
## Étapes complètes, pas à pas

---

## AVANT DE COMMENCER

Vous aurez besoin de :
- Un compte GitHub (gratuit) → github.com
- Un compte Render (gratuit) → render.com
- Une clé API Gemini (gratuite) → aistudio.google.com

---

## ÉTAPE 1 — Obtenir votre clé API Gemini

1. Allez sur : https://aistudio.google.com/app/apikey
2. Connectez-vous avec votre compte Google
3. Cliquez sur « Create API Key »
4. Choisissez « Create API key in new project »
5. Copiez la clé (commence par AIza...) et gardez-la précieusement

---

## ÉTAPE 2 — Créer un compte GitHub

1. Allez sur https://github.com
2. Cliquez « Sign up »
3. Suivez les étapes d'inscription (email, mot de passe)
4. Validez votre adresse email

---

## ÉTAPE 3 — Uploader les fichiers sur GitHub

1. Connectez-vous sur https://github.com
2. Cliquez sur le « + » en haut à droite → « New repository »
3. Donnez un nom : docbot (tout en minuscules)
4. Laissez « Public » coché
5. Cliquez « Create repository »

6. Sur la page du dépôt, cliquez « uploading an existing file »
7. Glissez-déposez TOUS les fichiers du dossier docbot/ :
   - app.py
   - requirements.txt
   - render.yaml
   - Le dossier docs/ avec vos fichiers PDF/DOCX dedans
   - Le dossier templates/ avec index.html dedans

   ⚠️ IMPORTANT : GitHub ne crée pas automatiquement les sous-dossiers.
   Pour créer le dossier docs/ : cliquez « Add file » → « Create new file »
   → tapez docs/LISEZ-MOI.txt → écrivez n'importe quoi → committez.
   Ensuite uploadez vos PDF dans docs/ de la même façon.

8. Cliquez « Commit changes »

---

## ÉTAPE 4 — Ajouter vos documents

Dans votre dépôt GitHub, naviguez dans le dossier docs/ :
1. Cliquez « Add file » → « Upload files »
2. Glissez vos PDF et/ou DOCX
3. Cliquez « Commit changes »

Pour les URLs (sites web), vous les configurerez dans Render (étape 5).

---

## ÉTAPE 5 — Déployer sur Render

1. Allez sur https://render.com
2. Cliquez « Get Started for Free »
3. Inscrivez-vous avec votre compte GitHub (bouton « GitHub »)
4. Autorisez Render à accéder à vos dépôts

5. Sur le dashboard Render, cliquez « New » → « Web Service »
6. Choisissez votre dépôt « docbot »
7. Render détecte automatiquement render.yaml → Cliquez « Apply »

8. IMPORTANT — Configurez les variables d'environnement :
   → Cherchez « Environment » dans le menu gauche
   → Cliquez « Add Environment Variable »
   → Ajoutez :
      Clé : GEMINI_API_KEY
      Valeur : [votre clé AIza...]

   Si vous avez des URLs à inclure comme sources :
      Clé : SOURCE_URLS
      Valeur : https://site1.com,https://site2.com

   Pour personnaliser le nom du bot :
      Clé : BOT_NAME
      Valeur : Mon Assistant (ou le nom de votre choix)

9. Cliquez « Save Changes »
10. Cliquez « Deploy » (ou « Manual Deploy » → « Deploy latest commit »)

---

## ÉTAPE 6 — Attendre le déploiement (3 à 5 minutes)

Render va :
✅ Installer Python
✅ Installer les dépendances
✅ Charger vos documents
✅ Démarrer le serveur

Vous verrez « Live » en vert quand c'est prêt.

---

## ÉTAPE 7 — Partager votre lien !

Render vous donne une URL du type :
  https://docbot.onrender.com

C'est ce lien que vous partagez. Vos utilisateurs :
→ Cliquent le lien
→ Voient le chatbot directement
→ Posent leurs questions
→ Aucun compte, aucun téléchargement requis ✅

---

## METTRE À JOUR VOS DOCUMENTS

Pour changer ou ajouter des documents :
1. Allez sur GitHub → votre dépôt → dossier docs/
2. Uploadez vos nouveaux fichiers
3. Sur Render → « Manual Deploy » → « Deploy latest commit »
4. Attendez 2-3 minutes → les nouveaux docs sont en ligne

---

## LIMITES DU PLAN GRATUIT

Render (plan gratuit) :
- Le serveur « s'endort » après 15 minutes d'inactivité
- Le premier chargement après une période d'inactivité prend ~30 secondes
- Pour éviter ça → Render propose le plan « Starter » à 7$/mois

Gemini (plan gratuit) :
- 1 500 requêtes par jour
- Largement suffisant pour un usage normal

---

## EN CAS DE PROBLÈME

Logs disponibles sur Render → votre service → onglet « Logs »
Cherchez les lignes [OK] pour confirmer que les documents sont bien chargés.

Si vous voyez [ERREUR] → vérifiez que le fichier est bien dans docs/
