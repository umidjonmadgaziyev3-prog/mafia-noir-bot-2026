import os
import time
import random
import requests

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi")

API = f"https://api.telegram.org/bot{TOKEN}"

games = {}
offset = 0

ROLES = [
    ("Mafia", "Mafia jamoasi"),
    ("Don", "Mafia boshlig‘i"),
    ("Detective", "Bir o‘yinchini tekshiradi"),
    ("Doctor", "Bir o‘yinchini himoya qiladi"),
    ("Bodyguard", "Bir o‘yinchini himoya qiladi"),
    ("Citizen", "Oddiy fuqaro"),
]


def telegram(method, data=None):
    try:
        r = requests.post(
            f"{API}/{method}",
            json=data or {},
            timeout=30
        )
        return r.json()
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
            "timeout": 25
        }
    )

    return result.get("result", [])


def new_game(chat_id):
    games[chat_id] = {
        "players": {},
        "started": False
    }


def start_game(chat_id):
    game = games.get(chat_id)

    if not game:
        return

    players = list(game["players"].items())

    if len(players) < 4:
        send_message(
            chat_id,
            "❌ O‘yinni boshlash uchun kamida 4 ta o‘yinchi kerak."
        )
        return

    random.shuffle(players)

    roles = []

    roles.append(("Don", "Mafia boshlig‘i"))
    roles.append(("Mafia", "Mafia jamoasi"))
    roles.append(("Detective", "Bir o‘yinchini tekshiradi"))
    roles.append(("Doctor", "Bir o‘yinchini himoya qiladi"))

    while len(roles) < len(players):
        roles.append(("Citizen", "Oddiy fuqaro"))

    random.shuffle(roles)

    for i, (user_id, user) in enumerate(players):
        role, description = roles[i]

        game["players"][user_id]["role"] = role
        game["players"][user_id]["alive"] = True

        try:
            send_message(
                user_id,
                f"🎭 MAFIA NOIR\n\n"
                f"Sizning rolingiz: {role}\n"
                f"{description}\n\n"
                f"Rolingizni boshqa o‘yinchilarga aytmang."
            )
        except Exception:
            pass

    game["started"] = True

    text = (
        "🌙 MAFIA NOIR BOSHLANDI!\n\n"
        f"👥 O‘yinchilar: {len(players)}\n\n"
        "🌑 Tun tushdi...\n"
        "Har bir rol o‘z vazifasini bajaradi."
    )

    send_message(chat_id, text)


def handle_message(message):
    chat = message.get("chat", {})
    chat_id = chat.get("id")

    user = message.get("from", {})
    user_id = user.get("id")

    text = message.get("text", "")

    if not chat_id or not user_id:
        return

    if text == "/start":
        send_message(
            chat_id,
            "🕯️ MAFIA NOIR\n\n"
            "Sirlar, shubhalar va yashirin rollar o‘yini.\n\n"
            "Buyruqlar:\n"
            "/newgame — yangi o‘yin\n"
            "/join — o‘yinga qo‘shilish\n"
            "/startgame — o‘yinni boshlash"
        )

    elif text == "/newgame":
        new_game(chat_id)

        send_message(
            chat_id,
            "🎭 Yangi Mafia Noir o‘yini yaratildi!\n\n"
            "O‘yinga qo‘shilish uchun /join bosing."
        )

    elif text == "/join":
        if chat_id not in games:
            new_game(chat_id)

        game = games[chat_id]

        if game["started"]:
            send_message(
                chat_id,
                "❌ O‘yin allaqachon boshlangan."
            )
            return

        name = user.get("first_name", "O‘yinchi")

        game["players"][user_id] = {
            "name": name,
            "role": None,
            "alive": True
        }

        send_message(
            chat_id,
            f"✅ {name} o‘yinga qo‘shildi!\n"
            f"👥 Jami o‘yinchilar: {len(game['players'])}"
        )

    elif text == "/startgame":
        start_game(chat_id)

    else:
        send_message(
            chat_id,
            "🕯️ Noma’lum buyruq.\n\n"
            "/newgame\n"
            "/join\n"
            "/startgame"
        )


def main():
    global offset

    print("🤖 Mafia Noir Bot ishga tushdi...")

    while True:
        updates = get_updates()

        for update in updates:
            offset = update["update_id"] + 1

            message = update.get("message")

            if message:
                handle_message(message)


if __name__ == "__main__":
    main()
