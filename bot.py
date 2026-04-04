import discord
import os
import logging
from datetime import datetime

# ============================================================
#  CONFIGURATION — remplace les IDs de tes amis uniquement
#  Le token et ton ID viennent des variables d'environnement
# ============================================================

AMIS_IDS = [
    1438260672587628564,  # Mathys  — Ami 1
    1398380814596571308,  # Thildy  — Ami 2
    1416787967661445274,  # ettienz — Ami 3
    1301568459703976039,  # dallil  — Ami 4
    1063850610761404486,  # romain  — Ami 5
    1376953372338290901,  # Jallel  — Ami 6
    1345854728675786833,  # thuyai  — Ami 7
    #888888888888888888, # Ami 8
]

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

# Stocke les données du message envoyé pour chaque ami :
#   member_id → {"message": discord.Message, "content": str}
# Permet d'éditer le message pour signaler la déconnexion avec 🔴
# NOTE : dict[int, dict] compatible Python 3.8+
messages_notif = {}  # type: dict

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
async def on_voice_state_update(member, before, after):
    # Ignore si ce n'est pas un ami surveillé
    if member.id not in AMIS_IDS:
        return

    # ── CAS 1 : Déconnexion totale du vocal ──────────────────────────────────
    # before.channel = salon quitté, after.channel = None (complètement déco)
    if before.channel is not None and after.channel is None:
        if member.id in messages_notif:
            stored = messages_notif[member.id]
            msg = stored["message"]
            original_content = stored["content"]
            heure_depart = datetime.now().strftime("%H:%M:%S")

            # ⚠️ Les bots ne peuvent PAS ajouter de réactions dans les DMs (API Discord).
            # On édite le message d'origine pour y ajouter une ligne de départ avec 🔴.
            new_content = f"{original_content}\n🔴 **A quitté le vocal** à **{heure_depart}**"
            try:
                await msg.edit(content=new_content)
                log.info(f"🔴 {member.display_name} a quitté le vocal — message mis à jour")
            except discord.NotFound:
                log.warning(f"⚠️ Message introuvable pour {member.display_name} (supprimé ?)")
            except discord.Forbidden:
                log.error("❌ Impossible de modifier le message — permissions insuffisantes")
            except discord.HTTPException as e:
                log.error(f"❌ Erreur HTTP lors de la modification du message : {e}")
            finally:
                # Nettoyage dans tous les cas pour éviter une référence obsolète
                del messages_notif[member.id]
        else:
            log.info(f"ℹ️ {member.display_name} a quitté le vocal (aucun message stocké — bot redémarré ?)")
        return

    # ── CAS 2 : Changement de salon (avant → après, sans déco) → ignoré ─────
    # before.channel is not None ET after.channel is not None
    if before.channel is not None:
        return

    # ── CAS 3 : Entrée dans un salon vocal (depuis aucun salon) ──────────────
    # before.channel = None, after.channel = salon rejoint
    if after.channel is None:
        return  # sécurité (ne devrait pas arriver)

    maintenant = datetime.now()
    salon_name = after.channel.name

    # Sécurité : guild peut être None dans certains edge cases
    guild = getattr(after.channel, "guild", None)
    server_name = guild.name if guild else "Serveur inconnu"

    heure = maintenant.strftime("%H:%M:%S")

    log.info(f"🎙️ {member.display_name} a rejoint #{salon_name} sur {server_name}")

    # Récupère l'utilisateur depuis le cache Discord d'abord (pas d'appel API inutile)
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

    # Construction du contenu du message (stocké pour pouvoir l'éditer plus tard)
    contenu = (
        f"🎙️ **{member.display_name}** vient de rejoindre le vocal **{salon_name}**\n"
        f"📡 Serveur : **{server_name}**\n"
        f"🕐 {heure}"
    )

    # Envoi du DM avec gestion d'erreur — on stocke le message pour l'édition future
    try:
        message = await toi.send(contenu)
        # Stocke le message ET son contenu original pour reconstruire le texte édité
        messages_notif[member.id] = {
            "message": message,
            "content": contenu,
        }
        log.info("✅ Notification envoyée et message stocké pour la mise à jour future")
    except discord.Forbidden:
        log.error("❌ Impossible d'envoyer un DM — vérifie que tes DMs sont ouverts (Paramètres → Confidentialité)")
    except discord.HTTPException as e:
        log.error(f"❌ Erreur HTTP lors de l'envoi du DM : {e}")


client.run(TOKEN)
