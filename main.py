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

# =========================================================
# TELEGRAM
# =========================================================

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


# =========================================================
# YORDAMCHI FUNKSIYALAR
# =========================================================

def alive_players(game):
    return [
        (uid, data)
        for uid, data in game["players"].items()
        if data["alive"]
    ]


def player_name(game, user_id):
    if user_id in game["players"]:
        return game["players"][user_id]["name"]
    return "Noma'lum"


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


def check_winner(chat_id):
    game = games.get(chat_id)

    if not game or not game["started"]:
        return False

    mafia_count = len(mafia_players(game))
    civilian_count = len(civilian_players(game))

    if mafia_count == 0:
        send_message(
            chat_id,
            "🏆 FUQAROLAR G‘ALABA QOZONDI!\n\n"
            "🕯️ Mafia Noir ustidan yorug‘lik g‘alaba qozondi."
        )
        game["finished"] = True
        game["started"] = False
        return True

    if mafia_count >= civilian_count:
        send_message(
            chat_id,
            "🩸 MAFIA G‘ALABA QOZONDI!\n\n"
            "🌑 Shahar tun zulmatiga cho‘mdi."
        )
        game["finished"] = True
        game["started"] = False
        return True

    return False


def role_description(role):
    descriptions = {
        "Don": (
            "👑 Mafia boshlig‘i.\n"
            "Mafia jamoasini boshqaradi."
        ),
        "Mafia": (
            "🔪 Mafia jamoasi.\n"
            "Tun paytida nishon tanlashda qatnashadi."
        ),
        "Detective": (
            "🕵️ Detective.\n"
            "Har tun bir o‘yinchini tekshiradi."
        ),
        "Doctor": (
            "🩺 Doctor.\n"
            "Har tun bir o‘yinchini himoya qiladi."
        ),
        "Bodyguard": (
            "🛡️ Bodyguard.\n"
            "Har tun bir o‘yinchini himoya qiladi."
        ),
        "Citizen": (
            "👤 Oddiy fuqaro.\n"
            "Kunduzgi muhokama va ovoz berishda qatnashadi."
        )
    }

    return descriptions.get(role, "Noma'lum rol")


# =========================================================
# O‘YIN YARATISH
# =========================================================

def new_game(chat_id):
    games[chat_id] = {
        "players": {},
        "started": False,
        "finished": False,
        "phase": "lobby",

        "night_number": 0,

        "mafia_target": None,
        "doctor_target": None,
        "bodyguard_target": None,
        "detective_target": None,

        "votes": {},
        "night_actions": {}
    }


# =========================================================
# ROLLARNI TAQSIMLASH
# =========================================================

def create_roles(player_count):

    roles = []

    # Asosiy rollar
    roles.append("Don")
    roles.append("Mafia")
    roles.append("Detective")
    roles.append("Doctor")

    if player_count >= 6:
        roles.append("Bodyguard")

    while len(roles) < player_count:
        roles.append("Citizen")

    random.shuffle(roles)

    return roles


# =========================================================
# O‘YINNI BOSHLASH
# =========================================================

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

    roles = create_roles(len(players))

    for index, (user_id, data) in enumerate(players):

        role = roles[index]

        data["role"] = role
        data["alive"] = True

        message = (
            "🕯️ MAFIA NOIR\n\n"
            f"🎭 Sizning rolingiz: {role}\n\n"
            f"{role_description(role)}\n\n"
            "🔐 Bu rol maxfiy.\n"
            "Boshqa o‘yinchilarga aytmang."
        )

        send_message(user_id, message)

    game["started"] = True
    game["finished"] = False
    game["phase"] = "night"
    game["night_number"] = 1

    send_message(
        chat_id,
        "🌑 ━━━ 1-TUN ━━━ 🌑\n\n"
        "🕯️ Shahar uxlamoqda...\n"
        "Ko‘chalarda sukunat.\n"
        "Ammo zulmat ichida kimdir harakat qilmoqda.\n\n"
        "🎭 Maxfiy rollar o‘z vazifalarini bajaradi.\n"
        "📩 Kerakli harakatlar shaxsiy chat orqali amalga oshiriladi."
    )

    send_night_instructions(chat_id)


# =========================================================
# TUN BUYRUQLARI
# =========================================================

def send_night_instructions(chat_id):

    game = games.get(chat_id)

    if not game:
        return

    for user_id, data in alive_players(game):

        role = data["role"]

        buttons = []

        targets = [
            (uid, pdata)
            for uid, pdata in alive_players(game)
            if uid != user_id
        ]

        if role in ("Mafia", "Don"):

            for uid, pdata in targets:
                buttons.append([
                    {
                        "text": f"🔪 {pdata['name']}",
                        "callback_data": f"night_kill:{chat_id}:{uid}"
                    }
                ])

            if buttons:
                send_message(
                    user_id,
                    "🌑 Tun boshlandi.\n\n"
                    "🔪 Mafia uchun nishon tanlang:",
                    {"inline_keyboard": buttons}
                )

        elif role == "Detective":

            for uid, pdata in targets:
                buttons.append([
                    {
                        "text": f"🕵️ {pdata['name']}",
                        "callback_data": f"detective:{chat_id}:{uid}"
                    }
                ])

            if buttons:
                send_message(
                    user_id,
                    "🕵️ Kimni tekshirmoqchisiz?",
                    {"inline_keyboard": buttons}
                )

        elif role == "Doctor":

            for uid, pdata in alive_players(game):
                buttons.append([
                    {
                        "text": f"🩺 {pdata['name']}",
                        "callback_data": f"doctor:{chat_id}:{uid}"
                    }
                ])

            send_message(
                user_id,
                "🩺 Kimni himoya qilasiz?",
                {"inline_keyboard": buttons}
            )

        elif role == "Bodyguard":

            for uid, pdata in alive_players(game):
                buttons.append([
                    {
                        "text": f"🛡️ {pdata['name']}",
                        "callback_data": f"bodyguard:{chat_id}:{uid}"
                    }
                ])

            send_message(
                user_id,
                "🛡️ Kimni himoya qilasiz?",
                {"inline_keyboard": buttons}
            )


# =========================================================
# TUN HARAKATLARI
# =========================================================

def night_kill(chat_id, user_id, target_id):

    game = games.get(chat_id)

    if not game:
        return

    if game["phase"] != "night":
        return

    if user_id not in game["players"]:
        return

    role = game["players"][user_id]["role"]

    if role not in ("Mafia", "Don"):
        return

    if target_id not in game["players"]:
        return

    if not game["players"][target_id]["alive"]:
        return

    game["mafia_target"] = target_id

    send_message(
        user_id,
        "🔪 Nishon belgilandi.\n\n"
        "🌑 Tun davom etmoqda..."
    )

    check_night_complete(chat_id)


def detective_check(chat_id, user_id, target_id):

    game = games.get(chat_id)

    if not game:
        return

    if game["phase"] != "night":
        return

    if game["players"].get(user_id, {}).get("role") != "Detective":
        return

    target = game["players"].get(target_id)

    if not target:
        return

    if not target["alive"]:
        return

    role = target["role"]

    if role in ("Mafia", "Don"):
        result = (
            f"🕵️ Tekshiruv natijasi:\n\n"
            f"🔴 {target['name']} — MAFIA TOMONIDA."
        )
    else:
        result = (
            f"🕵️ Tekshiruv natijasi:\n\n"
            f"🟢 {target['name']} — FUQARO TOMONIDA."
        )

    send_message(user_id, result)

    game["detective_target"] = target_id

    check_night_complete(chat_id)


def doctor_save(chat_id, user_id, target_id):

    game = games.get(chat_id)

    if not game:
        return

    if game["phase"] != "night":
        return

    if game["players"].get(user_id, {}).get("role") != "Doctor":
        return

    if target_id not in game["players"]:
        return

    if not game["players"][target_id]["alive"]:
        return

    game["doctor_target"] = target_id

    send_message(
        user_id,
        "🩺 Himoya tanlandi."
    )

    check_night_complete(chat_id)


def bodyguard_save(chat_id, user_id, target_id):

    game = games.get(chat_id)

    if not game:
        return

    if game["phase"] != "night":
        return

    if game["players"].get(user_id, {}).get("role") != "Bodyguard":
        return

    if target_id not in game["players"]:
        return

    if not game["players"][target_id]["alive"]:
        return

    game["bodyguard_target"] = target_id

    send_message(
        user_id,
        "🛡️ Himoya pozitsiyasi tanlandi."
    )

    check_night_complete(chat_id)


# =========================================================
# TUNNI YAKUNLASH
# =========================================================

def check_night_complete(chat_id):

    game = games.get(chat_id)

    if not game or game["phase"] != "night":
        return

    mafia_ready = game["mafia_target"] is not None

    if not mafia_ready:
        return

    # Detective, Doctor yoki Bodyguard mavjud bo‘lmasa kutmaymiz.
    roles = [
        data["role"]
        for _, data in alive_players(game)
    ]

    if "Detective" in roles and game["detective_target"] is None:
        return

    if "Doctor" in roles and game["doctor_target"] is None:
        return

    if "Bodyguard" in roles and game["bodyguard_target"] is None:
        return

    resolve_night(chat_id)


# =========================================================
# TUN NATIJASI
# =========================================================

def resolve_night(chat_id):

    game = games.get(chat_id)

    if not game:
        return

    target_id = game["mafia_target"]

    protected = []

    if game["doctor_target"] is not None:
        protected.append(game["doctor_target"])

    if game["bodyguard_target"] is not None:
        protected.append(game["bodyguard_target"])

    if target_id in protected:

        send_message(
            chat_id,
            "🌅 Tong otdi...\n\n"
            "🕯️ Kecha kimdir nishonga olingan edi.\n"
            "Ammo hujum muvaffaqiyatsiz tugadi.\n\n"
            "🛡️ Hech kim o‘yindan chiqmadi."
        )

    else:

        target = game["players"].get(target_id)

        if target and target["alive"]:

            target["alive"] = False

            send_message(
                chat_id,
                "🌅 Tong otdi...\n\n"
                f"💀 {target['name']} kechasi o‘yindan chiqdi.\n\n"
                "🕯️ Uning roli endi oshkor qilinadi:\n"
                f"🎭 {target['role']}"
            )

    if check_winner(chat_id):
        return

    start_day(chat_id)


# =========================================================
# KUN
# =========================================================

def start_day(chat_id):

    game = games.get(chat_id)

    if not game:
        return

    game["phase"] = "day"
    game["votes"] = {}

    alive = alive_players(game)

    names = "\n".join(
        f"• {data['name']}"
        for _, data in alive
    )

    send_message(
        chat_id,
        "☀️ ━━━ KUN ━━━ ☀️\n\n"
        "🕯️ Shahar uyg‘ondi.\n"
        "Endi gumonlar boshlanadi.\n\n"
        "👥 Tirik o‘yinchilar:\n"
        f"{names}\n\n"
        "🗳️ Ovoz berish:\n"
        "Shaxsiy chatda /vote buyrug‘i orqali nishon tanlang."
    )

    send_vote_buttons(chat_id)


# =========================================================
# OVOZ BERISH
# =========================================================

def send_vote_buttons(chat_id):

    game = games.get(chat_id)

    if not game:
        return

    for user_id, data in alive_players(game):

        buttons = []

        for target_id, target in alive_players(game):

            if target_id == user_id:
                continue

            buttons.append([
                {
                    "text": f"🗳️ {target['name']}",
                    "callback_data": f"vote:{chat_id}:{target_id}"
                }
            ])

        if buttons:
            send_message(
                user_id,
                "🗳️ Kimni shubhali deb hisoblaysiz?",
                {"inline_keyboard": buttons}
            )


def vote_player(chat_id, voter_id, target_id):

    game = games.get(chat_id)

    if not game:
        return

    if game["phase"] != "day":
        return

    if voter_id not in game["players"]:
        return

    if not game["players"][voter_id]["alive"]:
        return

    if target_id not in game["players"]:
        return

    if not game["players"][target_id]["alive"]:
        return

    if voter_id == target_id:
        send_message(
            voter_id,
            "❌ O‘zingizga ovoz bera olmaysiz."
        )
        return

    game["votes"][voter_id] = target_id

    send_message(
        voter_id,
        f"🗳️ Ovoz qabul qilindi: "
        f"{game['players'][target_id]['name']}"
    )

    alive_count = len(alive_players(game))

    if len(game["votes"]) >= alive_count:
        resolve_votes(chat_id)


def resolve_votes(chat_id):

    game = games.get(chat_id)

    if not game:
        return

    counts = {}

    for target_id in game["votes"].values():
        counts[target_id] = counts.get(target_id, 0) + 1

    if not counts:
        start_night(chat_id)
        return

    max_votes = max(counts.values())

    winners = [
        target_id
        for target_id, count in counts.items()
        if count == max_votes
    ]

    if len(winners) > 1:

        names = ", ".join(
            game["players"][uid]["name"]
            for uid in winners
        )

        send_message(
            chat_id,
            "⚖️ Ovozlar teng keldi.\n\n"
            f"🤝 Teng ovoz: {names}\n\n"
            "🕯️ Hech kim chiqarilmadi."
        )

    else:

        eliminated_id = winners[0]
        eliminated = game["players"][eliminated_id]

        eliminated["alive"] = False

        send_message(
            chat_id,
            "🗳️ OVOZ BERISH YAKUNI\n\n"
            f"💀 {eliminated['name']} o‘yindan chiqarildi.\n\n"
            "🎭 Uning roli:\n"
            f"{eliminated['role']}"
        )

    if check_winner(chat_id):
        return

    start_night(chat_id)


# =========================================================
# YANGI TUN
# =========================================================

def start_night(chat_id):

    game = games.get(chat_id)

    if not game:
        return

    game["phase"] = "night"
    game["night_number"] += 1

    game["mafia_target"] = None
    game["doctor_target"] = None
    game["bodyguard_target"] = None
    game["detective_target"] = None
    game["votes"] = {}

    send_message(
        chat_id,
        f"🌑 ━━━ {game['night_number']}-TUN ━━━ 🌑\n\n"
        "🕯️ Shahar yana sukutga cho‘mdi...\n\n"
        "🌑 Mafia harakatda.\n"
        "🕵️ Detective iz qidirmoqda.\n"
        "🩺 Doctor himoya qilmoqda.\n"
        "🛡️ Bodyguard navbatchilikda."
    )

    send_night_instructions(chat_id)


# =========================================================
# CALLBACK
# =========================================================

def handle_callback(callback):

    data = callback.get("data", "")
    callback_id = callback.get("id")
    from_user = callback.get("from", {})
    user_id = from_user.get("id")

    telegram(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_id,
            "text": "Qabul qilindi."
        }
    )

    parts = data.split(":")

    if len(parts) != 3:
        return

    action = parts[0]

    try:
        chat_id = int(parts[1])
        target_id = int(parts[2])
