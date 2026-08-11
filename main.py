import os
import random
import requests

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi")

API = f"https://api.telegram.org/bot{TOKEN}"

games = {}
offset = 0


def telegram(method, data=None):
    try:
        r = requests.post(
            f"{API}/{method}",
            json=data or {},
            timeout=35
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
            "timeout": 25,
            "allowed_updates": ["message", "callback_query"]
        }
    )

    return result.get("result", [])


def alive_players(game):
    return [
        (uid, data)
        for uid, data in game["players"].items()
        if data["alive"]
    ]


def player_name(game, user_id):
    return game["players"].get(user_id, {}).get("name", "Noma'lum")


def mafia_players(game):
    return [
        (uid, data)
        for uid, data in alive_players(game)
        if data["role"] in ("Mafia", "Don")
    ]


def civilian_players(game):
    return [
        (uid, data)
        for uid, data in alive_players(game)
        if data["role"] not in ("Mafia", "Don")
    ]


def role_description(role):
    descriptions = {
        "Don": "👑 Mafia boshlig‘i. Mafia jamoasini bosh
