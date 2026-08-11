import os
import random
import requests

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi")

API = f"https://api.telegram.org/bot{TOKEN}"

games = {}
offset = 0


# =========================
# TELEGRAM API
# =========================

def telegram(method, data=None):
    try:
        response = requests.post(
            f"{API}/{method}",
            json=data or {},
            timeout=35
        )
        return response.json()
    except Exception as e:
        print("Telegram xatosi:", e)
        return {}


def send_message(chat_id, text, reply_markup=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_markup:
        data["reply_markup"] = reply_markup

    return telegram("sendMessage", data)


def get_updates():
    global offset

    result = telegram(
        "getUpdates",
        {
            "offset": offset,
            "timeout": 25,
            "allowed_updates": [
                "message",
                "callback_query"
            ]
        }
    )

    return result.get("result", [])


# =========================
# YORDAMCHI
# =========================

def alive_players(game):
    return [
        (uid, data)
        for uid, data in game["players"].items()
        if data["alive"]
    ]


def player_name(game, user_id):
    return game["players"].get(
        user_id,
        {}
    ).get("name", "Noma'lum")


def mafia_players(game):
    return [
        (uid, data)
        for uid, data in alive_players(game)
        if data["role"] in ("Don", "Mafia")
    ]


def citizen_players(game):
    return [
        (uid, data)
        for uid, data in alive_players(game)
        if data["role"] not in ("Don", "Mafia")
    ]


def role_description(role):
    descriptions = {
        "Don": "👑 Mafia boshlig‘i. Mafia jamoasini boshqaradi.",
        "Mafia": "🔪 Mafia. Tun paytida nishon tanlaydi.",
        "Detective": "🕵️ Detective. Har tun bir o‘yinchini tekshiradi.",
        "Doctor": "🩺 Doctor. Har tun bir o‘yinchini himoya qiladi.",
        "Bodyguard": "🛡️ Bodyguard. Har tun bir o‘yinchini himoya qiladi.",
        "Citizen": "👤 Oddiy fuqaro. Kunduzgi ovoz berishda qatnashadi."
    }

    return descriptions.get(role, "Noma'lum rol.")


# =========================
# YANGI O‘YIN
# =========================

def new_game(chat_id):
    games[chat_id] = {
        "players": {},
        "started": False,
        "finished": False,
        "phase": "lobby",
        "night": 0,
        "mafia_target": None,
        "doctor_target": None,
        "bodyguard_target": None,
        "detective_target": None,
        "votes": {}
    }


# =========================
# ROLLAR
# =========================

def make_roles(count):
    roles = [
        "Don",
        "Mafia",
        "Detective",
        "Doctor"
    ]

    if count >= 6:
        roles.append("Bodyguard")

    while len(roles) < count:
        roles.append("Citizen")

    random.shuffle(roles)

    return roles


# =========================
# G‘ALABANI TEKSHIRISH
# =========================

def check_winner(chat_id):
    game = games.get(chat_id)

    if not game or not game["started"]:
        return False

    mafia_count = len(mafia_players(game))
    citizen_count = len(citizen_players(game))

    if mafia_count == 0:
        send_message(
            chat_id,
            "🏆 FUQAROLAR G‘ALABA QOZONDI!\n\n"
            "🕯️ Sirlar ochildi.\n"
            "🌅 Shahar yana tinchlandi."
        )

        game["started"] = False
        game["finished"] = True
        return True

    if mafia_count >= citizen_count:
        send_message(
            chat_id,
            "🩸 MAFIA G‘ALABA QOZONDI!\n\n"
            "🌑 Shahar zulmat bag‘rida qoldi."
        )

        game["started"] = False
        game["finished"] = True
        return True

    return False


# =========================
# O‘YINNI BOSHLASH
# =========================

def start_game(chat_id):
    game = games.get(chat_id)

    if not game:
        send_message(
            chat_id,
            "❌ Avval /newgame yuboring."
        )
        return

    if game["started"]:
        send_message(
            chat_id,
            "❌ O‘yin allaqachon boshlangan."
        )
        return

    players = list(game["players"].items())

    if len(players) < 4:
        send_message(
            chat_id,
            "❌ Kamida 4 ta o‘yinchi kerak."
        )
        return

    roles = make_roles(len(players))

    for index, item in enumerate(players):
        user_id, data = item
        role = roles[index]

        data["role"] = role
        data["alive"] = True

        send_message(
            user_id,
            "🕯️ MAFIA NOIR\n\n"
            f"🎭 SIZNING ROLINGIZ: {role}\n\n"
            f"{role_description(role)}\n\n"
            "🔐 ROLINGIZ MAXFIY.\n"
            "Uni boshqa o‘yinchilarga aytmang."
        )

    game["started"] = True
    game["finished"] = False
    game["phase"] = "night"
    game
