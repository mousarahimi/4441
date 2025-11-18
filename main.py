import telebot
from threading import Lock
import json, os, random
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

bot = telebot.TeleBot('8549313349:AAFFuPlLNJTAHJI5B1Vl3PORCgI5d1wuUGw', parse_mode='html')

DATA_FILE = "players_data.json"
players_dict = {}
nazor_dict = {}
main_message_dict = {}
lock = Lock()

funny_add_messages = ["😎 اسم تو اضافه شد!", "😂 هیجان‌انگیز شد!", "🤣 چه بازیکن شجاعی!"]
funny_remove_messages = ["😅 خداحافظ!", "😂 اسم شما حذف شد!", "🤣 حذف شدی!"]

roles = ["شهروندساده", "شهروند ساده", "رییس مافیا", "شیاد", "ناتو", "رویین تن", "کاراگاه", "دکتر", "محقق", "بازپرس"]
illegal_names = ["مستانه", "مثتانه", "مصتانه"]

# ------------------ داده‌ها ------------------
def load_data():
    global players_dict, nazor_dict
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            players_dict = data.get("players", {})
            nazor_dict = data.get("nazor", {})
    else:
        players_dict = {}
        nazor_dict = {}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"players": players_dict, "nazor": nazor_dict}, f, ensure_ascii=False, indent=2)

# ------------------ تولید لیست ------------------
def generate_list(chat_id):
    players = players_dict.get(str(chat_id), [])
    nazor = nazor_dict.get(str(chat_id), ["___", "___"])
    styles = [
        {"prefix1":"▪️","prefix2":"▫️","header_icon":"🃏"},
        {"prefix1":"🎭","prefix2":"🎲","header_icon":"🔥"},
        {"prefix1":"🟢","prefix2":"🔴","header_icon":"✨"},
        {"prefix1":"🔹","prefix2":"🔸","header_icon":"🌟"},
        {"prefix1":"⚡","prefix2":"💥","header_icon":"🎴"}
    ]
    style = random.choice(styles)
    header = f"{style['header_icon']} <b>ᴍᴀғɪᴀ ᴏғ ɴɪɢʜᴛ</b> {style['header_icon']}\n"
    header += f"👁‍🗨 ناظر ۱: {nazor[0]} | ناظر ۲: {nazor[1]}\n♣️ <b>لیست شرکت کنندگان</b>\n🕙 راس ساعت 22:00\n〰〰〰\n📃 اسامی:\n"
    body = ""
    for i in range(1, 17):
        prefix = style['prefix1'] if i % 2 == 1 else style['prefix2']
        name = players[i-1] if i-1 < len(players) else "___"
        body += f"{prefix} <b>{i}</b>- {name}\n"
    footer = "〰〰〰\n✨ فعال باشید!"
    return header + body + footer

# ------------------ اضافه و حذف اسم ------------------
def add_name(user_name, chat_id):
    with lock:
        if str(chat_id) not in players_dict:
            players_dict[str(chat_id)] = []
        if user_name in illegal_names:
            return "illegal"
        if len(players_dict[str(chat_id)]) >= 16:
            return False
        if user_name not in players_dict[str(chat_id)]:
            players_dict[str(chat_id)].append(user_name)
            save_data()
            return True
    return False

def remove_name(user_name, chat_id):
    with lock:
        if str(chat_id) in players_dict and user_name in players_dict[str(chat_id)]:
            players_dict[str(chat_id)].remove(user_name)
            save_data()
            return True
    return False

def reset_list(chat_id):
    with lock:
        players_dict[str(chat_id)] = []
        nazor_dict[str(chat_id)] = ["___", "___"]
        save_data()
        if str(chat_id) in main_message_dict:
            try:
                bot.edit_message_text(generate_list(chat_id), chat_id, main_message_dict[str(chat_id)])
            except: pass

# ------------------ پیش‌بینی نقش‌ها ------------------
def generate_role_prediction(chat_id):
    players = players_dict.get(str(chat_id), [])
    if not players:
        return "⚠️ لیست خالی است، پیش‌بینی ممکن نیست."
    role_list = roles.copy()
    random.shuffle(role_list)
    prediction = ""
    for idx, player in enumerate(players):
        role = role_list[idx % len(role_list)]
        prefix = "▪️" if idx % 2 == 0 else "▫️"
        prediction += f"{prefix} {idx+1}- {player} - نقش: {role}\n"
    return "<b>پیش‌بینی نقش‌ها:</b>\n" + prediction

# ------------------ ارسال لیست ------------------
@bot.message_handler(commands=['start', 'لیست'])
def send_list(message):
    chat_id = str(message.chat.id)
    with lock:
        if chat_id not in players_dict: players_dict[chat_id] = []
        if chat_id not in nazor_dict: nazor_dict[chat_id] = ["___", "___"]
        sent = bot.send_message(chat_id, generate_list(chat_id))
        main_message_dict[chat_id] = sent.message_id
        try:
            bot.pin_chat_message(chat_id, sent.message_id, disable_notification=True)
        except: pass
        save_data()

# ------------------ ارسال پیام لابی با تگ اعضای حاضر ------------------
@bot.message_handler(func=lambda m: "لابی ساعت" in m.text)
def lobby_message(message):
    chat_id = str(message.chat.id)
    try:
        # ارسال پیام لابی
        sent_msg = bot.send_message(chat_id, message.text)
        bot.pin_chat_message(chat_id, sent_msg.message_id, disable_notification=True)

        # تگ کردن بازیکنان حاضر در گروه
        mentions_text = ""
        current_players = players_dict.get(chat_id, [])
        for player in current_players:
            mentions_text += f"@{player} "
        
        if mentions_text:
            bot.send_message(chat_id, mentions_text, reply_to_message_id=sent_msg.message_id)

        bot.reply_to(message, "📌 پیام لابی ارسال و اعضای حاضر تگ شدند!")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا در ارسال لابی: {e}")

# ------------------ هندلر پیام‌ها ------------------
@bot.message_handler(func=lambda m: True)
def handle_messages(message):
    chat_id = str(message.chat.id)
    text = message.text.strip()
    user_name = message.from_user.username or message.from_user.first_name

    if not text.startswith("/"):
        bot.reply_to(message, "🚨 فرمان نامعتبره! لطفا قبل از ارسال / بگذارید")
        return

    cmd = text[1:].strip()  # حذف اسلش

    if not cmd:
        bot.reply_to(message, "🚨 فرمان نامعتبره! لطفا بعد از / اسم یا دستور وارد کنید")
        return

    # ---------- ثبت ناظر ----------
    if cmd.startswith("ناظر"):
        parts = cmd.split()
        if len(parts) >= 3:
            nazor_type = parts[1]
            nazor_name = " ".join(parts[2:]).strip()
            if chat_id not in nazor_dict:
                nazor_dict[chat_id] = ["___", "___"]
            if nazor_type in ["1","یک","۱"]:
                nazor_dict[chat_id][0] = nazor_name
            elif nazor_type in ["2","دو","۲"]:
                nazor_dict[chat_id][1] = nazor_name
            save_data()
            bot.reply_to(message, f"👁‍🗨 ناظر ثبت شد: {nazor_name}")
            if chat_id in main_message_dict:
                bot.edit_message_text(generate_list(chat_id), chat_id, main_message_dict[chat_id])
        return

    # ---------- پیش‌بینی نقش‌ها ----------
    if cmd.lower() in ["پیشبینی", "پیشبینی نقش"]:
        bot.reply_to(message, generate_role_prediction(chat_id))
        return

    # ---------- ریست ----------
    if cmd.lower() == "ریست":
        try:
            admins = bot.get_chat_administrators(message.chat.id)
            if message.from_user.id in [a.user.id for a in admins]:
                reset_list(chat_id)
                bot.reply_to(message, "♻️ لیست ریست شد.")
            else:
                bot.reply_to(message, "❌ فقط ادمین می‌تواند ریست کند.")
        except: pass
        return

    # ---------- حذف خود ----------
    if cmd.lower() in ["حذف", "remove"]:
        if remove_name(user_name, chat_id):
            bot.reply_to(message, random.choice(funny_remove_messages))
        else:
            bot.reply_to(message, "⚠️ شما در لیست نبودید!")
        if chat_id in main_message_dict:
            bot.edit_message_text(generate_list(chat_id), chat_id, main_message_dict[chat_id])
        return

    # ---------- اضافه کردن بازیکن ----------
    result = add_name(cmd, chat_id)
    if result == "illegal":
        bot.reply_to(message,"🚨 نام غیرمجاز!")
    elif result is True:
        bot.reply_to(message,f"✔ {cmd} اضافه شد!")
        bot.reply_to(message, random.choice(funny_add_messages))
    else:
        bot.reply_to(message,"⚠️ اضافه نشد! یا قبلا هست یا لیست پر است.")
    if chat_id in main_message_dict:
        bot.edit_message_text(generate_list(chat_id), chat_id, main_message_dict[chat_id])

# ------------------ زمان‌بندی ------------------
def schedule_jobs():
    tz = pytz.timezone("Asia/Tehran")
    scheduler = BackgroundScheduler(timezone=tz)
    scheduler.add_job(lambda: [reset_list(cid) for cid in players_dict.keys()], 'cron', hour=22, minute=0)
    def send_reminder():
        for cid in players_dict.keys():
            try: bot.send_message(cid, "⏰ بازی امشب ساعت 22 شروع می‌شود!")
            except: pass
    scheduler.add_job(send_reminder, 'cron', hour=20, minute=30)
    scheduler.start()

# ------------------ شروع ------------------
load_data()
schedule_jobs()
bot.polling(none_stop=True)
