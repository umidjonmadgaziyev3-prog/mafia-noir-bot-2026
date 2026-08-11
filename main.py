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
            "allowed_updates": [
                "message",
                "callback_query"
            ]
        }
    )

    return result.get("result", [])


def welcome_menu():
    return {
        "inline_keyboard": [
            [
                {
                    "text": "🕯️ Mafia Noir nima?",
                    "callback_data": "welcome:about"
                }
            ],
            [
                {
                    "text": "📜 Qoidalar",
                    "callback_data": "welcome:rules"
                }
            ],
            [
                {
                    "text": "🎭 Rollar",
                    "callback_data": "welcome:roles"
                }
            ]
        ]
    }


def role_description(role):
    descriptions = {
        "Don": "👑 Mafia boshlig‘i. Mafia jamoasini boshqaradi.",
        "Mafia": "🔪 Mafia. Tun paytida nishon tanlaydi.",
        "Detective": "🕵️ Detective. Har tun bir o‘yinchini tekshiradi.",
        "Doctor": "🩺 Doctor. Har tun bir o‘yinchini himoya qiladi.",
        "Bodyguard": "🛡️ Bodyguard. Har tun bir o‘yinchini qo‘riqlaydi.",
        "Citizen": "👤 Oddiy fuqaro. Kunduzgi ovoz berishda qatnashadi."
    }

    return descriptions.get(role, "Noma’lum rol.")


def alive_players(game):
    return [
        (uid, data)
        for uid, data in game["players"].items()
        if data["alive"]
    ]


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


def player_name(game, user_id):
    return game["players"].get(
        user_id,
        {}
    ).get("name", "O‘yinchi")


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


def start_game(chat_id):
    game = games.get(chat_id)

    if not game:
        send_message(chat_id, "❌ Avval /newgame yuboring.")
        return

    if game["started"]:
        send_message(chat_id, "❌ O‘yin allaqachon boshlangan.")
        return

    players = list(game["players"].items())

    if len(players) < 4:
        send_message(
            chat_id,
            "❌ O‘yinni boshlash uchun kamida 4 ta o‘yinchi kerak."
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
            "🎭 MAFIA NOIR\n\n"
            f"SIZNING ROLINGIZ: {role}\n\n"
            f"{role_description(role)}\n\n"
            "🔐 Rolingiz maxfiy."
        )

    game["started"] = True
    game["finished"] = False
    game["phase"] = "night"
    game["night"] = 1

    send_message(
        chat_id,
        "🌑 ═══════════════\n"
        "       1-TUN\n"
        "════════════════\n\n"
        "🕯️ Shahar uxlamoqda...\n"
        "🌫️ Ko‘chalarda sukunat.\n"
        "👁️ Zulmat ichida kimdir uyg‘oq.\n\n"
        "🎭 Maxfiy rollar harakatga kelmoqda."
    )

    send_night_buttons(chat_id)


def send_night_buttons(chat_id):
    game = games.get(chat_id)

    if not game:
        return

    for user_id, data in alive_players(game):
        role = data["role"]

        targets = [
            (uid, pdata)
            for uid, pdata in alive_players(game)
            if uid != user_id
        ]

        buttons = []

        if role in ("Don", "Mafia"):
            for target_id, target in targets:
                buttons.append([
                    {
                        "text": f"🔪 {target['name']}",
                        "callback_data": f"kill:{chat_id}:{target_id}"
                    }
                ])

            if buttons:
                send_message(
                    user_id,
                    "🌑 TUN\n\n🔪 Nishonni tanlang:",
                    {"inline_keyboard": buttons}
                )

        elif role == "Detective":
            for target_id, target in targets:
                buttons.append([
                    {
                        "text": f"🕵️ {target['name']}",
                        "callback_data": f"check:{chat_id}:{target_id}"
                    }
                ])

            if buttons:
                send_message(
                    user_id,
                    "🕵️ Tekshirmoqchi bo‘lgan o‘yinchini tanlang:",
                    {"inline_keyboard": buttons}
                )

        elif role == "Doctor":
            for target_id, target in alive_players(game):
                buttons.append([
                    {
                        "text": f"🩺 {target['name']}",
                        "callback_data": f"heal:{chat_id}:{target_id}"
                    }
                ])

            send_message(
                user_id,
                "🩺 Kimni himoya qilasiz?",
                {"inline_keyboard": buttons}
            )

        elif role == "Bodyguard":
            for target_id, target in alive_players(game):
                buttons.append([
                    {
                        "text": f"🛡️ {target['name']}",
                        "callback_data": f"guard:{chat_id}:{target_id}"
                    }
                ])

            send_message(
                user_id,
                "🛡️ Kimni qo‘riqlaysiz?",
                {"inline_keyboard": buttons}
            )


def night_action(chat_id, user_id, target_id, action):
    game = games.get(chat_id)

    if not game or game["phase"] != "night":
        return

    if user_id not in game["players"]:
        return

    if not game["players"][user_id]["alive"]:
        return

    if target_id not in game["players"]:
        return

    if not game["players"][target_id]["alive"]:
        return

    role = game["players"][user_id]["role"]

    if action == "kill":
        if role not in ("Don", "Mafia"):
            return

        game["mafia_target"] = target_id

        send_message(
            user_id,
            "🔪 Nishon tanlandi."
        )

    elif action == "check":
        if role != "Detective":
            return

        target_role = game["players"][target_id]["role"]

        if target_role in ("Don", "Mafia"):
            result = "🔴 MAFIA TOMONIDA"
        else:
            result = "🟢 FUQARO TOMONIDA"

        send_message(
            user_id,
            "🕵️ TEKSHIRUV NATIJASI\n\n"
            f"👤 {player_name(game, target_id)}\n"
            f"Natija: {result}"
        )

        game["detective_target"] = target_id

    elif action == "heal":
        if role != "Doctor":
            return

        game["doctor_target"] = target_id

        send_message(
            user_id,
            "🩺 Himoya tanlandi."
        )

    elif action == "guard":
        if role != "Bodyguard":
            return

        game["bodyguard_target"] = target_id

        send_message(
            user_id,
            "🛡️ Qo‘riqlash tanlandi."
        )

    check_night_complete(chat_id)


def check_night_complete(chat_id):
    game = games.get(chat_id)

    if not game or game["phase"] != "night":
        return

    if game["mafia_target"] is None:
        return

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
            "🌅 TONG OTDИ...\n\n"
            "🛡️ Kecha hujum bo‘ldi.\n"
            "Ammo himoya o‘z vaqtida yetib keldi.\n\n"
            "✅ Hech kim o‘yindan chiqmadi."
        )
    else:
        target = game["players"].get(target_id)

        if target and target["alive"]:
            target["alive"] = False

            send_message(
                chat_id,
                "🌅 TONG OTDИ...\n\n"
                f"💀 {target['name']} kechasi o‘yindan chiqdi.\n\n"
                f"🎭 Roli: {target['role']}"
            )

    if check_winner(chat_id):
        return

    start_day(chat_id)


def start_day(chat_id):
    game = games.get(chat_id)

    if not game:
        return

    game["phase"] = "day"
    game["votes"] = {}

    names = "\n".join(
        f"• {data['name']}"
        for _, data in alive_players(game)
    )

    send_message(
        chat_id,
        "☀️ ═══════════════\n"
        "       KUN\n"
        "════════════════\n\n"
        "🕯️ Shahar uyg‘ondi.\n"
        "👁️ Endi hamma bir-biridan shubhalanadi.\n\n"
        "👥 Tirik o‘yinchilar:\n"
        f"{names}"
    )

    send_vote_buttons(chat_id)


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

    if not game or game["phase"] != "day":
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
        return

    game["votes"][voter_id] = target_id

    send_message(
        voter_id,
        "🗳️ Ovoz qabul qilindi."
    )

    if len(game["votes"]) >= len(alive_players(game)):
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

    maximum = max(counts.values())

    winners = [
        target_id
        for target_id, count in counts.items()
        if count == maximum
    ]

    if len(winners) > 1:
        names = ", ".join(
            player_name(game, uid)
            for uid in winners
        )

        send_message(
            chat_id,
            "⚖️ OVOZLAR TENG KELDI\n\n"
            f"🤝 {names}\n\n"
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
            f"🎭 Roli: {eliminated['role']}"
        )

    if check_winner(chat_id):
        return

    start_night(chat_id)


def start_night(chat_id):
    game = games.get(chat_id)

    if not game:
        return

    game["phase"] = "night"
    game["night"] += 1

    game["mafia_target"] = None
    game["doctor_target"] = None
    game["bodyguard_target"] = None
    game["detective_target"] = None
    game["votes"] = {}

    send_message(
        chat_id,
        f"🌑 ═══════════════\n"
        f"       {game['night']}-TUN\n"
        "════════════════\n\n"
        "🕯️ Shahar yana sukutga cho‘mdi...\n\n"
        "🔪 Mafia harakatda.\n"
        "🕵️ Detective iz qidirmoqda.\n"
        "🩺 Doctor himoya qilmoqda.\n"
        "🛡️ Bodyguard navbatchilikda."
    )

    send_night_buttons(chat_id)


def welcome_callback(callback):
    callback_id = callback.get("id")
    data = callback.get("data", "")
    user_id = callback.get("from", {}).get("id")

    telegram(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_id
        }
    )

    if data == "welcome:about":
        send_message(
            user_id,
            "🕯️ MAFIA NOIR NIMA?\n\n"
            "Mafia Noir — yashirin rollar, "
            "sirlar va shubhalarga asoslangan "
            "ijtimoiy o‘yin.\n\n"
            "👥 O‘yin guruhda davom etadi.\n"
            "🔐 Shaxsiy chat esa faqat sizga "
            "tegishli maxfiy o‘yin harakatlari "
            "uchun ishlatiladi."
        )

    elif data == "welcome:rules":
        send_message(
            user_id,
            "📜 ASOSIY QOIDALAR\n\n"
            "🔪 Mafia yashirincha harakat qiladi.\n"
            "🕵️ Detective tekshiradi.\n"
            "🩺 Doctor himoya qiladi.\n"
            "🛡️ Bodyguard qo‘riqlaydi.\n"
            "👤 Fuqarolar Mafia kimligini topishga "
            "harakat qiladi.\n\n"
            "☀️ Kunduzi ovoz beriladi.\n"
            "🌑 Tunda maxfiy rollar harakat qiladi."
        )

    elif data == "welcome:roles":
        send_message(
            user_id,
            "🎭 ROLLAR\n\n"
            "👑 Don — Mafia boshlig‘i.\n"
            "🔪 Mafia — Mafia jamoasi.\n"
            "🕵️ Detective — tekshiruvchi.\n"
            "🩺 Doctor — himoyachi.\n"
            "🛡️ Bodyguard — qo‘riqchi.\n"
            "👤 Citizen — oddiy fuqaro."
        )


def handle_callback(callback):
    data = callback.get("data", "")

    if data.startswith("welcome:"):
        welcome_callback(callback)
        return

    callback_id = callback.get("id")
    user_id = callback.get("from", {}).get("id")

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
    except (ValueError, TypeError):
        return

    if action in ("kill", "check", "heal", "guard"):
        night_action(
            chat_id,
            user_id,
            target_id,
            action
        )

    elif action == "vote":
        vote_player(
            chat_id,
            user_id,
            target_id
        )


def handle_message(message):
    chat = message.get("chat", {})
    chat_id = chat.get("id")

    user = message.get("from", {})
    user_id = user.get("id")

    text = message.get("text", "").strip()

    if not chat_id or not user_id:
        return

    chat_type = chat.get("type")

    # SHAXSIY CHAT
    if chat_type == "private":
        if text == "/start":
            send_message(
                chat_id,
                "🕯️ MAFIA NOIR\n\n"
                "Sirlar, shubhalar va yashirin "
                "rollar olamiga xush kelibsiz.\n\n"
                "🎭 Bu bot orqali Mafia Noir "
                "o‘yinida sizning maxfiy rolingiz "
                "va o‘yindagi shaxsiy harakatlaringiz "
                "boshqariladi.\n\n"
                "👥 O‘yin guruhda davom etadi.\n"
                "🔐 Maxfiy harakatlar esa shu yerda "
                "amalga oshiriladi.",
                welcome_menu()
            )

        return

    # GURUH
    if text == "/newgame":
        new_game(chat_id)

        send_message(
            chat_id,
            "🕯️ MAFIA NOIR\n\n"
            "🎭 Yangi o‘yin yaratildi!\n\n"
            "O‘yinga qo‘shilish uchun /join yuboring."
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

        if user_id in game["players"]:
            return

        name = user.get(
            "first_name",
            "O‘yinchi"
        )

        game["players"][user_id] = {
            "name": name,
            "role": None,
            "alive": True
        }

        send_message(
            chat_id,
            f"✅ {name} o‘yinga qo‘shildi!\n"
            f"👥 Jami o‘yinchilar: "
            f"{len(game['players'])}"
        )

    elif text == "/startgame":
        start_game(chat_id)


def main():
    global offset

    print("🕯️ Mafia Noir Bot ishga tushdi...")

    while True:
        updates = get_updates()

        for update in updates:
            offset = update.get(
                "update_id",
                offset
            ) + 1

            message = update.get("message")

            if message:
                handle_message(message)

            callback = update.get("callback_query")

            if callback:
                handle_callback(callback)


if __name__ == "__main__":
    main()
