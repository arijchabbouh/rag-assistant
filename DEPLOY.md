# Déployer sur Hugging Face Spaces

Ce guide met l'assistant en ligne dans un **Space Docker** (page web + API dans un seul conteneur, port 7860).
Rien n'est déployé automatiquement : chaque étape se fait à la main.

Dans les commandes, remplace `<toi>` par ton nom d'utilisateur Hugging Face et `<space>` par le nom du Space
(par exemple `assistant-enicarthage`). L'adresse du Space sera `https://<toi>-<space>.hf.space`.

## À savoir avant de commencer

- **Le disque d'un Space gratuit est éphémère.** Tout ce que le conteneur écrit disparaît à chaque redémarrage
  ou reconstruction. En particulier `feedback.jsonl` (les « Signaler une réponse fausse ») est **perdu** : en
  ligne, les signalements ne sont pas conservés tant qu'un stockage persistant (payant) ou un dépôt de données
  n'est pas branché. Les données de l'assistant (`chunks.json`, `embeddings.npy`) ne sont pas concernées :
  elles font partie de l'image.
- **Un Space gratuit s'endort** quand personne ne l'utilise pendant un moment ; la première visite suivante le
  réveille (comptez une à quelques minutes).
- **Les réponses viennent de Gemini** avec ta clé : les limites gratuites de Gemini s'appliquent à tous les
  visiteurs ensemble.

## 1. Les données : quelle option ?

`chunks.json` et `embeddings.npy` sont tirés des documents de l'école : ils ne sont **pas** dans le dépôt GitHub
public et ne doivent pas l'être. Deux façons de les donner au Space :

| | A. Space privé avec les fichiers (**recommandé**) | B. Génération dans le conteneur |
|---|---|---|
| Ce qu'on envoie | `chunks.json` + `embeddings.npy` (1 Mo) | les **PDF** de `documents/` |
| Données exposées si le Space fuit | le texte découpé | les documents complets |
| Build | rapide | + découpage + calcul des embeddings à chaque build |
| Code | déjà prêt (`deploy/prepare_space.py`) | modifier `.dockerignore` (il exclut `documents/`) et le Dockerfile |
| Risque d'erreur | faible : liste blanche de fichiers | les PDF passent par un dépôt de plus |

**Recommandation : option A.** C'est la plus simple (rien à modifier) et la plus sûre (les PDF ne quittent
jamais ton ordinateur, et un script n'envoie que les fichiers d'une liste blanche).

**Attention à « privé » :** un Space privé n'est visible que par toi (et les membres d'une organisation que tu
choisis). C'est parfait pour tester et faire une démo. Pour l'ouvrir aux étudiants, le Space doit devenir
public, et alors **ses fichiers sont téléchargeables par tous**, `chunks.json` compris. Avant de le rendre
public : demander l'accord de l'école pour diffuser ce contenu, ou adapter le projet pour que le Space public
télécharge ces deux fichiers au démarrage depuis un dépôt de données privé (avec un jeton en secret). Ce n'est
pas encore fait.

## 2. Une fois : outils et connexion

1. Crée un compte sur https://huggingface.co si besoin.
2. Crée un jeton : *Settings → Access Tokens → Create new token*, type **Write**. Ne le colle nulle part ailleurs
   que dans la commande ci-dessous.
3. Dans le terminal du projet (PowerShell, `.venv` activé) :
   ```powershell
   hf auth login        # colle le jeton quand il est demandé
   hf auth whoami       # doit afficher ton nom
   ```

## 3. Créer le Space

Sur https://huggingface.co/new-space :

- **Space name** : `<space>`
- **SDK** : **Docker**, modèle **Blank**
- **Hardware** : *CPU basic* (gratuit)
- **Visibility** : **Private** (voir la partie 1)

Clique *Create Space*. Il est vide pour l'instant : c'est normal.

## 4. Les secrets

Dans le Space : *Settings → Variables and secrets → New secret* (des **secrets**, pas des variables : leur valeur
n'est jamais affichée).

| Nom | Valeur |
|---|---|
| `GEMINI_API_KEY` | ta clé Gemini (la même que dans `.env`) |
| `ALLOWED_ORIGINS` | `https://<toi>-<space>.hf.space` |

`ALLOWED_ORIGINS` sert seulement si une page d'un **autre** site appelle l'API : en ligne, la page et l'API sont
à la même adresse, donc aucune autorisation CORS n'est nécessaire. Le mettre à l'adresse du Space évite que la
valeur par défaut de développement (`http://localhost:5173`) soit utilisée en ligne.

Ne mets **jamais** la clé dans un fichier envoyé au Space : `.env` n'est pas dans la liste blanche, et
`.dockerignore` l'exclut aussi.

## 5. Préparer et envoyer les fichiers

```powershell
python chunk_documents.py            # seulement si les documents ont changé
python embed_chunks.py               # idem
python deploy/prepare_space.py       # crée space_build/ : uniquement les fichiers de la liste blanche
```

Le script vérifie que `chunks.json` et `embeddings.npy` existent et correspondent (même nombre de chunks), puis
affiche la liste des fichiers copiés : **relis-la**. Il ne doit y avoir ni `documents/`, ni `.env`, ni
`feedback.jsonl`. Ensuite :

```powershell
hf upload <toi>/<space> space_build . --repo-type space
```

`space_build/` est ignoré par git : il ne part jamais sur GitHub.

## 6. Premier démarrage

L'envoi déclenche la construction de l'image. Onglet **Logs** du Space :

1. *Building* : construction de la page (Node), installation de torch (version CPU) et des dépendances,
   téléchargement du modèle d'embedding. Plusieurs minutes la première fois.
2. *Running* : l'API démarre. Dans les logs, ces lignes doivent apparaître :
   - `Pipeline loaded: 503 chunks, embeddings (503, 384), 12 document titles`
   - `Serving the web interface from frontend/dist`
   - `Uvicorn running on http://0.0.0.0:7860`

Erreurs fréquentes :

| Message dans les logs | Cause | Solution |
|---|---|---|
| `GEMINI_API_KEY is not set` | secret absent ou mal nommé | partie 4, puis *Settings → Factory rebuild* |
| `"/chunks.json": not found` (pendant le build) | fichiers de données pas envoyés | refaire la partie 5 |
| `Quota Gemini atteint` dans la page | limite gratuite de Gemini | attendre ; voir la limite dans Google AI Studio |

## 7. Vérifications

1. `https://<toi>-<space>.hf.space/health` affiche `{"status":"ok","chunks":503,"model_loaded":true}`.
2. La page `https://<toi>-<space>.hf.space` s'ouvre, avec le logo, et les deux avertissements en bas
   (« Vérifiez l'information officielle… » et « Ne saisissez pas de données personnelles. »).
3. « Quand est le forum des entreprises ? » → le 17 novembre, avec une source « Calendrier universitaire
   2026-2027 » cliquable.
4. « quel est le menu de la cantine » → refus, avec « Essayez de reformuler votre question… ».
5. Onglet **Files** du Space : aucun PDF, pas de `.env`.
6. Depuis une fenêtre de navigation privée (non connectée) : le Space privé doit être **inaccessible**.

Tester la même image sur ton ordinateur avant l'envoi (si Docker Desktop est installé) :

```powershell
docker build -t assistant-enicarthage space_build
docker run --rm -p 7860:7860 --env-file .env assistant-enicarthage
# puis http://localhost:7860
```

## 8. Mettre à jour un document

Tout se fait sur ton ordinateur, puis on renvoie le dossier préparé.

**Ajouter un document** (par exemple le calendrier 2027-2028) :

1. Copie le PDF dans `documents/`.
2. Dans `documents_status.json`, ajoute une entrée (copie une entrée existante ; la clé est le nom exact du
   fichier) avec un `titre` lisible et `"status": "actuel"`.
3. Si un ancien document est remplacé, passe son `status` à `"archive"`.
4. `python chunk_documents.py` puis `python embed_chunks.py`.
5. Contrôle rapide : `python ask.py "une question sur le nouveau document"`, et `python evaluate.py` pour vérifier
   qu'il n'y a pas de régression.
6. `python deploy/prepare_space.py` puis `hf upload <toi>/<space> space_build . --repo-type space`.
7. Le Space se reconstruit tout seul ; refais les vérifications de la partie 7.

**Archiver un document** : change seulement son `status` en `"archive"`, puis étapes 4, 6 et 7.

**Changer un titre** : modifie `titre` dans `documents_status.json`, puis étapes 6 et 7 (pas besoin de recalculer
les embeddings).

Retirer un fichier qui n'est plus dans `space_build/` (rare) : *Files → le fichier → Delete* dans le Space.

## 9. Développement local (inchangé)

```powershell
uvicorn api:app --reload --port 8000                  # terminal 1
cd frontend; npm run dev                              # terminal 2 → http://localhost:5173
```

Vite renvoie `/ask`, `/feedback` et `/health` vers le port 8000 : la page et l'API ont la même origine, comme en
ligne. Pour viser une autre adresse d'API : `API_PROXY_TARGET` dans `frontend/.env.local`.

Sans Vite, `npm run build` puis `uvicorn api:app --port 8000` sert aussi la page sur http://localhost:8000.

## 10. Arrêter

*Settings → Pause this Space* l'arrête sans rien supprimer ; *Delete this Space* supprime tout (fichiers
compris). Les secrets peuvent être supprimés à tout moment dans *Variables and secrets*.
