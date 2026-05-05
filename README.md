# 🏦 Caisse RP — Bot Discord

Bot de caisse commune pour serveur Discord RP.  
Panneau interactif avec boutons, messages éphémères, historique en temps réel.

---

## ⚙️ Installation

### 1. Prérequis
- Python 3.10+ installé → https://www.python.org/downloads/

### 2. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 3. Créer le bot sur Discord
1. Va sur https://discord.com/developers/applications
2. Clique **"New Application"** → donne un nom
3. Va dans **"Bot"** → clique **"Add Bot"**
4. Clique **"Reset Token"** → copie le token
5. Active ces **Privileged Gateway Intents** :
   - ✅ MESSAGE CONTENT INTENT
6. Va dans **"OAuth2" → "URL Generator"** :
   - Coche `bot` + `applications.commands`
   - Dans Bot Permissions : `Send Messages`, `Embed Links`, `Manage Messages` (pour épingler)
   - Copie le lien généré et invite le bot sur ton serveur

### 4. Configurer le token
Ouvre `bot.py` et remplace `TON_TOKEN_ICI` par ton token :
```python
TOKEN = "ton_vrai_token_ici"
```

Ou mieux, crée un fichier `.env` :
```
DISCORD_TOKEN=ton_vrai_token_ici
```
Et installe python-dotenv :
```bash
pip install python-dotenv
```
Puis ajoute en haut de bot.py :
```python
from dotenv import load_dotenv
load_dotenv()
```

### 5. Lancer le bot
```bash
python bot.py
```

---

## 🎮 Utilisation

### Première fois
Tape `/caisse` dans le channel de ton choix → le panneau s'affiche et se retrouve épinglé.

### Les boutons
| Bouton | Action |
|--------|--------|
| ➕ **Ajouter** | Ouvre un formulaire (visible que par toi) → entre le montant + la raison → le solde se met à jour |
| ➖ **Retirer** | Même chose, soustrait du solde |
| 📋 **Historique complet** | Affiche toutes les transactions (visible que par toi) |
| 🗑️ **Réinitialiser** | Remet la caisse à 0 (demande confirmation) |

### Comment ça fonctionne
- Le **formulaire** de saisie est **éphémère** (seul toi le vois → le channel reste propre)
- Le **panneau principal** est **public et mis à jour en temps réel** pour tout le monde
- Les données sont **sauvegardées** dans `caisse.json` (survit aux redémarrages)
- Les boutons **fonctionnent après redémarrage** (vue persistante)

---

## 🖥️ Hébergement gratuit (24h/24)

### Option 1 — Railway.app (recommandé)
1. Crée un compte sur https://railway.app
2. "New Project" → "Deploy from GitHub"
3. Upload tes fichiers ou connecte GitHub
4. Ajoute la variable d'environnement `DISCORD_TOKEN`
5. Le bot tourne en continu !

### Option 2 — Ton PC (simple)
Lance `python bot.py` dans un terminal et laisse-le ouvert.  
Le bot s'arrête quand tu fermes le terminal.

---

## 📁 Fichiers
```
caisse-bot/
├── bot.py          ← Le bot principal
├── requirements.txt
├── README.md
└── caisse.json     ← Créé automatiquement au premier lancement
```
