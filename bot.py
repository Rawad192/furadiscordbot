import discord
import os
import logging
from datetime import datetime, timedelta

# ============================================================
#  CONFIGURATION — remplace les IDs de tes amis uniquement
#  Le token et ton ID viennent des variables d'environnement
# ============================================================

AMIS_IDS = [
    1438260672587628564,  #Mathys Pseudo Ami 1 — remplace par le vrai ID
    1398380814596571308,  #Thildy Pseudo Ami 2
    1416787967661445274,  #ettienz Pseudo Ami 3
    1301568459703976039,  #dallil Pseudo Ami 4
    1063850610761404486,  #romain Pseudo Ami 5
    1376953372338290901,  #Jallel Pseudo Ami 6
    1345854728675786833,  #thuyai Pseudo Ami 7
    #888888888888888888,  # Pseudo Ami 8
]

# Délai minimum (en minutes) entre deux notifications pour le même ami
# Evite le spam si quelqu'un rejoint/quitte/rejoint rapidement
COOLDOWN_MINUTES = 5

# ============================================================

# Logs propres avec horodatage
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# Récupération des variables d'environnement
TOKEN = os.environ.get("DISCORD_TOKEN")
TON_USER_ID_STR = os.environ.get("TON_USER_ID")

# Validation au démarrage — erreurs claires plutôt qu'un crash bizarre
if not TOKEN:
    log.error("❌ DISCORD_TOKEN manquant ! Ajoute-le dans tes variables d'environnement.")
    exit(1)

if not TON_USER_ID_STR or not TON_USER_ID_STR.isdigit():
    log.error("❌ TON_USER_ID manquant ou invalide ! Ajoute-le dans tes variables d'environnement.")
    exit(1)

TON_USER_ID = int(TON_USER_ID_STR)

# Stocke l'heure de la dernière notification par ami (anti-spam)
derniere_notif: dict[int, datetime] = {}

# Intents nécessaires
intents = discord.Intents.default()
intents.voice_states = True
intents.members = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    log.info(f"✅ Bot connecté en tant que {client.user} (ID : {client.user.id})")
    log.info(f"👥 Surveillance de {len(AMIS_IDS)} ami(s)")


@client.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    # Ignore si ce n'est pas un ami surveillé
    if member.id not in AMIS_IDS:
        return

    # Ignore les changements de salon et les déconnexions — on veut uniquement les entrées
    if before.channel is not None or after.channel is None:
        return

    maintenant = datetime.now()

    # Anti-spam : vérifie le cooldown pour cet ami
    if member.id in derniere_notif:
        temps_ecoule = maintenant - derniere_notif[member.id]
        if temps_ecoule < timedelta(minutes=COOLDOWN_MINUTES):
            restant = COOLDOWN_MINUTES - int(temps_ecoule.total_seconds() / 60)
            log.info(f"⏳ Cooldown actif pour {member.display_name} (encore ~{restant} min)")
            return

    # Met à jour le timestamp de dernière notification
    derniere_notif[member.id] = maintenant

    salon_name = after.channel.name
    server_name = after.channel.guild.name
    heure = maintenant.strftime("%H:%M:%S")

    log.info(f"🎙️ {member.display_name} a rejoint #{salon_name} sur {server_name}")

    # Récupère l'utilisateur depuis le cache Discord d'abord (pas d'appel API inutile)
    # Si pas en cache, on fait l'appel API
    toi = client.get_user(TON_USER_ID)
    if toi is None:
        try:
            toi = await client.fetch_user(TON_USER_ID)
        except discord.NotFound:
            log.error(f"❌ Utilisateur introuvable avec l'ID {TON_USER_ID}. Vérifie TON_USER_ID.")
            return
        except discord.HTTPException as e:
            log.error(f"❌ Erreur lors de la récupération de ton compte : {e}")
            return

    # Envoi du DM avec gestion d'erreur
    try:
        await toi.send(
            f"🎙️ **{member.display_name}** vient de rejoindre le vocal **{salon_name}**\n"
            f"📡 Serveur : **{server_name}**\n"
            f"🕐 {heure}"
        )
        log.info("✅ Notification envoyée avec succès")
    except discord.Forbidden:
        log.error("❌ Impossible d'envoyer un DM — vérifie que tes DMs sont ouverts (Paramètres → Confidentialité)")
    except discord.HTTPException as e:
        log.error(f"❌ Erreur HTTP lors de l'envoi du DM : {e}")


client.run(TOKEN)
