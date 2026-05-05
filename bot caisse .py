import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime

# ─────────────────────────────────────────────
#  CONFIG — mets ton token ici ou dans .env
# ─────────────────────────────────────────────
TOKEN = os.getenv("DISCORD_TOKEN", "TON_TOKEN_ICI")
DATA_FILE = "caisse.json"

# ─────────────────────────────────────────────
#  DONNÉES (sauvegarde JSON locale)
# ─────────────────────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"solde": 0, "historique": [], "message_id": None, "channel_id": None}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ─────────────────────────────────────────────
#  BOT SETUP
# ─────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ─────────────────────────────────────────────
#  EMBED CAISSE (le panneau public)
# ─────────────────────────────────────────────
def build_caisse_embed(data):
    solde = data["solde"]
    historique = data["historique"]

    # Couleur selon solde
    if solde > 0:
        color = discord.Color.from_str("#2ecc71")
        icon = "🟢"
    elif solde < 0:
        color = discord.Color.from_str("#e74c3c")
        icon = "🔴"
    else:
        color = discord.Color.from_str("#95a5a6")
        icon = "⚪"

    embed = discord.Embed(
        title="🏦 Caisse du Groupe RP",
        color=color
    )

    embed.add_field(
        name="💰 Solde actuel",
        value=f"```\n{icon}  {solde:,.0f} €\n```",
        inline=False
    )

    # Historique — 10 derniers
    if historique:
        lignes = []
        for h in reversed(historique[-10:]):
            signe = "➕" if h["montant"] > 0 else "➖"
            montant = abs(h["montant"])
            lignes.append(
                f"{signe} **{montant:,.0f} €** — {h['raison']} *(par {h['auteur']})*"
            )
        embed.add_field(
            name="📋 Historique (10 derniers)",
            value="\n".join(lignes),
            inline=False
        )
    else:
        embed.add_field(
            name="📋 Historique",
            value="*Aucune transaction pour l'instant.*",
            inline=False
        )

    embed.set_footer(text=f"Mis à jour le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}")
    return embed

# ─────────────────────────────────────────────
#  VUE BOUTONS (panneau public permanent)
# ─────────────────────────────────────────────
class CaisseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Permanent !

    @discord.ui.button(label="➕ Ajouter", style=discord.ButtonStyle.success, custom_id="caisse_ajouter")
    async def ajouter(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TransactionModal(mode="ajouter"))

    @discord.ui.button(label="➖ Retirer", style=discord.ButtonStyle.danger, custom_id="caisse_retirer")
    async def retirer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TransactionModal(mode="retirer"))

    @discord.ui.button(label="📋 Historique complet", style=discord.ButtonStyle.secondary, custom_id="caisse_historique")
    async def historique(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        if not data["historique"]:
            await interaction.response.send_message(
                "📋 Aucune transaction enregistrée.", ephemeral=True
            )
            return

        lignes = []
        for h in reversed(data["historique"]):
            signe = "➕" if h["montant"] > 0 else "➖"
            montant = abs(h["montant"])
            lignes.append(
                f"{signe} **{montant:,.0f} €** — {h['raison']} *(par {h['auteur']}, le {h['date']})*"
            )

        # Découpage si trop long
        texte = "\n".join(lignes)
        if len(texte) > 4000:
            texte = texte[:3990] + "\n*…(tronqué)*"

        embed = discord.Embed(
            title="📋 Historique complet",
            description=texte,
            color=discord.Color.blurple()
        )
        embed.set_footer(text=f"Solde actuel : {data['solde']:,.0f} €")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🗑️ Réinitialiser", style=discord.ButtonStyle.secondary, custom_id="caisse_reset")
    async def reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "⚠️ Tu veux vraiment **remettre la caisse à zéro** et effacer l'historique ?",
            view=ConfirmResetView(),
            ephemeral=True
        )

# ─────────────────────────────────────────────
#  MODAL SAISIE MONTANT + RAISON
# ─────────────────────────────────────────────
class TransactionModal(discord.ui.Modal):
    def __init__(self, mode: str):
        titre = "➕ Ajouter de l'argent" if mode == "ajouter" else "➖ Retirer de l'argent"
        super().__init__(title=titre)
        self.mode = mode

        self.montant_input = discord.ui.TextInput(
            label="Montant (€)",
            placeholder="Ex: 1500",
            required=True,
            max_length=12
        )
        self.raison_input = discord.ui.TextInput(
            label="Raison / Description",
            placeholder="Ex: Vente d'armes, Paiement loyer...",
            required=True,
            max_length=100
        )
        self.add_item(self.montant_input)
        self.add_item(self.raison_input)

    async def on_submit(self, interaction: discord.Interaction):
        # Validation montant
        try:
            montant_str = self.montant_input.value.replace(",", ".").replace(" ", "")
            montant = float(montant_str)
            if montant <= 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                "❌ Montant invalide. Entre un nombre positif (ex: `1500` ou `250.50`)",
                ephemeral=True
            )
            return

        raison = self.raison_input.value.strip()
        data = load_data()

        # Calcul
        if self.mode == "ajouter":
            data["solde"] += montant
            signe = "➕"
        else:
            data["solde"] -= montant
            signe = "➖"

        # Ajout historique
        data["historique"].append({
            "montant": montant if self.mode == "ajouter" else -montant,
            "raison": raison,
            "auteur": interaction.user.display_name,
            "date": datetime.now().strftime("%d/%m/%Y %H:%M")
        })

        save_data(data)

        # Confirmation éphémère (visible uniquement par l'utilisateur)
        nouveau_solde = data["solde"]
        couleur = "🟢" if nouveau_solde >= 0 else "🔴"
        await interaction.response.send_message(
            f"✅ **Transaction enregistrée !**\n"
            f"{signe} `{montant:,.0f} €` — *{raison}*\n"
            f"{couleur} Nouveau solde : **{nouveau_solde:,.0f} €**",
            ephemeral=True
        )

        # Mise à jour du panneau public
        await update_caisse_message(interaction, data)

# ─────────────────────────────────────────────
#  CONFIRMATION RESET
# ─────────────────────────────────────────────
class ConfirmResetView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)

    @discord.ui.button(label="✅ Oui, remettre à zéro", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        data["solde"] = 0
        data["historique"] = []
        save_data(data)
        await interaction.response.send_message("✅ Caisse remise à zéro !", ephemeral=True)
        await update_caisse_message(interaction, data)
        self.stop()

    @discord.ui.button(label="❌ Annuler", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("❌ Annulé.", ephemeral=True)
        self.stop()

# ─────────────────────────────────────────────
#  MISE À JOUR DU MESSAGE PUBLIC
# ─────────────────────────────────────────────
async def update_caisse_message(interaction: discord.Interaction, data: dict):
    """Met à jour le message épinglé de la caisse."""
    channel = interaction.channel
    embed = build_caisse_embed(data)

    if data.get("message_id") and data.get("channel_id") == channel.id:
        try:
            msg = await channel.fetch_message(data["message_id"])
            await msg.edit(embed=embed, view=CaisseView())
            return
        except discord.NotFound:
            pass  # Message supprimé, on en recrée un

    # Créer un nouveau message
    msg = await channel.send(embed=embed, view=CaisseView())
    try:
        await msg.pin()
    except Exception:
        pass  # Pas de perms pour épingler, pas grave

    data["message_id"] = msg.id
    data["channel_id"] = channel.id
    save_data(data)

# ─────────────────────────────────────────────
#  COMMANDE /caisse — Initialise le panneau
# ─────────────────────────────────────────────
@bot.tree.command(name="caisse", description="Affiche ou crée le panneau de la caisse commune")
async def caisse_cmd(interaction: discord.Interaction):
    data = load_data()
    embed = build_caisse_embed(data)

    # Si un ancien message existe, le supprimer
    if data.get("message_id") and data.get("channel_id") == interaction.channel_id:
        try:
            old = await interaction.channel.fetch_message(data["message_id"])
            await old.delete()
        except Exception:
            pass

    # Répondre (éphémère) pour confirmer
    await interaction.response.send_message("✅ Panneau créé !", ephemeral=True)

    # Envoyer le vrai panneau public
    msg = await interaction.channel.send(embed=embed, view=CaisseView())
    try:
        await msg.pin()
    except Exception:
        pass

    data["message_id"] = msg.id
    data["channel_id"] = interaction.channel_id
    save_data(data)

# ─────────────────────────────────────────────
#  STATUTS COMMANDE
# ─────────────────────────────────────────────
STATUTS = ["⏳ En attente", "🚚 En cours", "✅ Livrée", "❌ Annulée"]

# ─────────────────────────────────────────────
#  BUILD EMBED COMMANDE
# ─────────────────────────────────────────────
def build_commande_embed(data: dict, type_cmd: str):
    if type_cmd == "envoyee":
        titre = "📋 COMMANDE ENVOYÉE"
        couleur = discord.Color.from_str("#3498db")
        emoji_type = "📤"
    else:
        titre = "📋 COMMANDE REÇUE"
        couleur = discord.Color.from_str("#9b59b6")
        emoji_type = "📥"

    statut = data["statut"]
    if "✅" in statut:
        couleur = discord.Color.from_str("#2ecc71")
    elif "❌" in statut:
        couleur = discord.Color.from_str("#e74c3c")
    elif "🚚" in statut:
        couleur = discord.Color.from_str("#f39c12")

    embed = discord.Embed(title=f"{emoji_type} {titre}", color=couleur)
    embed.add_field(name="🏘️ Communauté", value=data["communaute"], inline=True)
    embed.add_field(name="📦 Matière", value=data["matiere"], inline=True)
    embed.add_field(name="🔢 Quantité", value=data["quantite"], inline=True)
    embed.add_field(name="💲 Prix", value=data["prix"], inline=True)
    embed.add_field(name="✅ Statut", value=statut, inline=True)
    embed.set_footer(text=f"Par {data['auteur']} — {data['date']}")
    return embed

# ─────────────────────────────────────────────
#  VUE BOUTONS COMMANDE (modifier statut)
# ─────────────────────────────────────────────
class CommandeView(discord.ui.View):
    def __init__(self, type_cmd: str, commande_data: dict):
        super().__init__(timeout=None)
        self.type_cmd = type_cmd
        self.commande_data = commande_data
        custom_id = f"statut_{type_cmd}_{commande_data['id']}"
        btn = discord.ui.Button(
            label="🔄 Changer le statut",
            style=discord.ButtonStyle.secondary,
            custom_id=custom_id
        )
        btn.callback = self.changer_statut
        self.add_item(btn)

    async def changer_statut(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Choisis le nouveau statut :",
            view=StatutSelectView(self.type_cmd, self.commande_data, interaction.message),
            ephemeral=True
        )

class StatutSelectView(discord.ui.View):
    def __init__(self, type_cmd: str, commande_data: dict, message: discord.Message):
        super().__init__(timeout=60)
        self.type_cmd = type_cmd
        self.commande_data = commande_data
        self.message = message

        for statut in STATUTS:
            btn = discord.ui.Button(label=statut, style=discord.ButtonStyle.secondary)
            btn.callback = self.make_callback(statut)
            self.add_item(btn)

    def make_callback(self, statut: str):
        async def callback(interaction: discord.Interaction):
            self.commande_data["statut"] = statut
            embed = build_commande_embed(self.commande_data, self.type_cmd)
            await self.message.edit(embed=embed)
            await interaction.response.send_message(
                f"✅ Statut mis à jour : **{statut}**", ephemeral=True
            )
            self.stop()
        return callback

# ─────────────────────────────────────────────
#  MODAL COMMANDE ENVOYÉE
# ─────────────────────────────────────────────
class CommandeModal(discord.ui.Modal):
    def __init__(self, type_cmd: str):
        titre = "📤 Nouvelle commande envoyée" if type_cmd == "envoyee" else "📥 Nouvelle commande reçue"
        super().__init__(title=titre)
        self.type_cmd = type_cmd

        self.communaute = discord.ui.TextInput(
            label="🏘️ Communauté",
            placeholder="Ex: Les Loups du Nord",
            required=True, max_length=50
        )
        self.matiere = discord.ui.TextInput(
            label="📦 Matière / Produit",
            placeholder="Ex: Acier, Munitions, Bois...",
            required=True, max_length=50
        )
        self.quantite = discord.ui.TextInput(
            label="🔢 Quantité",
            placeholder="Ex: 500 unités",
            required=True, max_length=30
        )
        self.prix = discord.ui.TextInput(
            label="💲 Prix",
            placeholder="Ex: 15 000 $",
            required=True, max_length=30
        )
        self.add_item(self.communaute)
        self.add_item(self.matiere)
        self.add_item(self.quantite)
        self.add_item(self.prix)

    async def on_submit(self, interaction: discord.Interaction):
        import time
        commande_data = {
            "id": str(int(time.time())),
            "communaute": self.communaute.value,
            "matiere": self.matiere.value,
            "quantite": self.quantite.value,
            "prix": self.prix.value,
            "statut": "⏳ En attente",
            "auteur": interaction.user.display_name,
            "date": datetime.now().strftime("%d/%m/%Y %H:%M")
        }

        embed = build_commande_embed(commande_data, self.type_cmd)
        view = CommandeView(self.type_cmd, commande_data)

        await interaction.response.send_message("✅ Commande enregistrée !", ephemeral=True)
        await interaction.channel.send(embed=embed, view=view)

# ─────────────────────────────────────────────
#  COMMANDES /commande-envoyee et /commande-recue
# ─────────────────────────────────────────────
@bot.tree.command(name="commande-envoyee", description="Enregistrer une commande passée à une autre communauté")
async def commande_envoyee(interaction: discord.Interaction):
    await interaction.response.send_modal(CommandeModal(type_cmd="envoyee"))

@bot.tree.command(name="commande-recue", description="Enregistrer une commande reçue d'une autre communauté")
async def commande_recue(interaction: discord.Interaction):
    await interaction.response.send_modal(CommandeModal(type_cmd="recue"))

# ─────────────────────────────────────────────
#  EVENTS
# ─────────────────────────────────────────────
@bot.event
async def on_ready():
    # Réenregistrer la vue persistante au redémarrage
    bot.add_view(CaisseView())
    await bot.tree.sync()
    print(f"✅ Bot connecté en tant que {bot.user}")
    print(f"   Utilise /caisse dans ton channel pour démarrer !")

# ─────────────────────────────────────────────
#  LANCEMENT
# ─────────────────────────────────────────────
bot.run(TOKEN)
