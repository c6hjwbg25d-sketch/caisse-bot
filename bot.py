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
