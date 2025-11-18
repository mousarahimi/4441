import telebot
from telebot import types
from threading import Lock
import json, os, random
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

# ------------------ تنظیمات اولیه ------------------
BOT_TOKEN = '8549313349:AAFFuPlLNJTAHJI5B1Vl3PORCgI5d1wuUGw'  # جایگزین کن
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='html')

DATA_FILE = "players_data.json"
players_dict = {}
nazor_dict = {}
main_message_dict = {}
lock = Lock()
ADMIN_IDS = [5382898102]  # شناسه ادمین‌ها را قرار بده

# مقادیر پیش‌فرض (در load_data ممکنه بارگذاری شوند)
funny_add_messages = ["😎 اسم تو اضافه شد!", "😂 هیجان‌انگیز شد!", "🤣 چه بازیکن شجاعی!"]
funny_remove_messages = ["😅 خداحافظ!", "😂 اسم شما حذف شد!", "🤣 حذف شدی!"]
lobby_text = "لابی ساعت {time} — لطفاً آماده باشید!"

roles = ["شهروندساده", "شهروند ساده", "رییس مافیا", "شیاد", "ناتو", "رویین تن", "کاراگاه", "دکتر", "محقق", "بازپرس"]
illegal_names = ["مستانه", "مثتانه", "مصتانه"]

# برای ذخیره‌سازی وضعیت انتظار ادمین (وقتی ادمین خواست چیزی را ویرایش کند)
pending_actions = {}  # {admin_id: {"action":"edit_add_msgs"/"edit_remove_msgs"/"edit_lobby", "extra":{}}}

# ------------------ بارگذاری و ذخیره‌سازی ------------------
def load_data():
    global players_dict, nazor_dict, funny_add_messages, funny_remove_messages, lobby_text
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            players_dict = data.get("players", {})
            nazor_dict = data.get("nazor", {})
            settings = data.get("settings", {})
            funny_add_messages = settings.get("funny_add_messages", funny_add_messages)
            funny_remove_messages = settings.get("funny_remove_messages", funny_remove_messages)
            lobby_text = settings.get("lobby_text", lobby_text)
    else:
        players_dict.clear()
        nazor_dict.clear()

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "players": players_dict,
            "nazor": nazor_dict,
            "settings": {
                "funny_add_messages": funny_add_messages,
                "funny_remove_messages": funny_remove_messages,
                "lobby_text": lobby_text
            }
        }, f, ensure_ascii=False, indent=2)

# ------------------ تولید لیست و عملکردها ------------------
def generate_list(chat_id):
    players = players_dict.get(str(chat_id), [])
    nazor = nazor_dict.get(str(chat_id), ["___", "___"])
    styles = [{"prefix1":"▪️","prefix2":"▫️","header_icon":"🃏"},
              {"prefix1":"🎭","prefix2":"🎲","header_icon":"🔥"},
              {"prefix1":"🟢","prefix2":"🔴","header_icon":"✨"},
              {"prefix1":"🔹","prefix2":"🔸","header_icon":"🌟"},
              {"prefix1":"⚡","prefix2":"💥","header_icon":"🎴"}]
    style = random.choice(styles)
    header = f"{style['header_icon']} <b>ᴍᴀғɪᴀ ᴏғ ɴɪɢʜᴛ</b> {style['header_icon']}\n"
    header += f"👁‍🗨 ناظر ۱: {nazor[0]} | ناظر ۲: {nazor[1]}\n♣️ <b>لیست شرکت کنندگان</b>\n🕙 راس ساعت 22:00\n〰〰〰\n📃 اسامی:\n"
    body = ""
    for i in range(1, 17):
        prefix = style['prefix1'] if i % 2 == 1 else style['prefix2']
        name = players[i-1] if i-1 < len(players) else "___"
        body += f"{prefix} <b>{i}</b>- {name}\n"
    return header + body + "〰〰〰\n✨ فعال باشید!"

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

# ------------------ دکوراتور دسترسی ادمین ------------------
def admin_required(func):
    def wrapper(message, *args, **kwargs):
        if message.from_user.id not in ADMIN_IDS:
            bot.reply_to(message, "❌ فقط ادمین اجازه دارد")
            return
        return func(message, *args, **kwargs)
    return wrapper

# ------------------ پنل مدیریتی ------------------
@bot.message_handler(commands=['panel'])
@admin_required
def open_panel(message):
    chat_id = str(message.chat.id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("📃 نمایش لیست", callback_data="show_list")
    btn2 = types.InlineKeyboardButton("➕ اضافه بازیکن", callback_data="add_player")
    btn3 = types.InlineKeyboardButton("➖ حذف بازیکن", callback_data="remove_player")
    btn4 = types.InlineKeyboardButton("♻️ ریست لیست", callback_data="reset_list")
    btn5 = types.InlineKeyboardButton("🎭 پیش‌بینی نقش", callback_data="role_prediction")
    btn6 = types.InlineKeyboardButton("👁‍🗨 مدیریت ناظر", callback_data="manage_nazor")
    btn7 = types.InlineKeyboardButton("📝 پیام‌های فان", callback_data="fun_messages")
    btn8 = types.InlineKeyboardButton("📢 متن لابی", callback_data="lobby_settings")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn8)
    bot.send_message(chat_id, "پنل مدیریتی پیشرفته:", reply_markup=markup)

# ------------------ هندلر دکمه‌های پنل ------------------
@bot.callback_query_handler(func=lambda call: True)
def handle_panel_buttons(call):
    chat_id = str(call.message.chat.id)
    data = call.data
    user_id = call.from_user.id

    if user_id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ فقط ادمین")
        return

    # نمایش لیست
    if data == "show_list":
        bot.edit_message_text(generate_list(chat_id), chat_id, call.message.message_id)
        return

    # ریست لیست
    if data == "reset_list":
        reset_list(chat_id)
        bot.answer_callback_query(call.id, "♻️ لیست ریست شد")
        try:
            bot.edit_message_text(generate_list(chat_id), chat_id, call.message.message_id)
        except: pass
        return

    # پیش‌بینی نقش
    if data == "role_prediction":
        bot.answer_callback_query(call.id, "🎭 پیش‌بینی نقش‌ها ارسال شد")
        bot.send_message(chat_id, generate_role_prediction(chat_id))
        return

    # اضافه بازیکن (نوتیفای و انتظار ورودی)
    if data == "add_player":
        pending_actions[user_id] = {"action": "add_player", "chat_id": chat_id}
        bot.answer_callback_query(call.id, "لطفا اسم بازیکن را با /اسم وارد کنید")
        return

    # حذف بازیکن
    if data == "remove_player":
        pending_actions[user_id] = {"action": "remove_player", "chat_id": chat_id}
        bot.answer_callback_query(call.id, "لطفا اسم بازیکن را با /حذف اسم وارد کنید")
        return

    # مدیریت ناظر
    if data == "manage_nazor":
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn1 = types.InlineKeyboardButton("ناظر 1 ✏️", callback_data="edit_nazor_1")
        btn2 = types.InlineKeyboardButton("ناظر 2 ✏️", callback_data="edit_nazor_2")
        btn3 = types.InlineKeyboardButton("ریست ناظرها 🔄", callback_data="reset_nazors")
        markup.add(btn1, btn2, btn3)
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "مدیریت ناظرها:", reply_markup=markup)
        return

    if data == "edit_nazor_1":
        pending_actions[user_id] = {"action": "edit_nazor_1", "chat_id": chat_id}
        bot.answer_callback_query(call.id, "لطفا نام ناظر 1 را ارسال کنید (بدون /)")
        return
    if data == "edit_nazor_2":
        pending_actions[user_id] = {"action": "edit_nazor_2", "chat_id": chat_id}
        bot.answer_callback_query(call.id, "لطفا نام ناظر 2 را ارسال کنید (بدون /)")
        return
    if data == "reset_nazors":
        nazor_dict[chat_id] = ["___", "___"]
        save_data()
        bot.answer_callback_query(call.id, "ناظرها ریست شدند")
        try:
            bot.edit_message_text(generate_list(chat_id), chat_id, call.message.message_id)
        except: pass
        return

    # پیام‌های فان (مدیریت)
    if data == "fun_messages":
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn1 = types.InlineKeyboardButton("نمایش پیام‌های اضافه", callback_data="show_fun_add")
        btn2 = types.InlineKeyboardButton("اضافه کردن پیام اضافه", callback_data="add_fun_add")
        btn3 = types.InlineKeyboardButton("نمایش پیام‌های حذف", callback_data="show_fun_remove")
        btn4 = types.InlineKeyboardButton("اضافه کردن پیام حذف", callback_data="add_fun_remove")
        markup.add(btn1, btn2, btn3, btn4)
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "مدیریت پیام‌های فان:", reply_markup=markup)
        return

    if data == "show_fun_add":
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "پیام‌های اضافه فعلی:\n" + "\n".join(funny_add_messages))
        return
    if data == "show_fun_remove":
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "پیام‌های حذف فعلی:\n" + "\n".join(funny_remove_messages))
        return
    if data == "add_fun_add":
        pending_actions[user_id] = {"action": "add_fun_add", "chat_id": chat_id}
        bot.answer_callback_query(call.id, "لطفا پیام جدید اضافه را ارسال کنید")
        return
    if data == "add_fun_remove":
        pending_actions[user_id] = {"action": "add_fun_remove", "chat_id": chat_id}
        bot.answer_callback_query(call.id, "لطفا پیام جدید حذف را ارسال کنید")
        return

    # تنظیمات لابی
    if data == "lobby_settings":
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn1 = types.InlineKeyboardButton("نمایش متن لابی", callback_data="show_lobby_text")
        btn2 = types.InlineKeyboardButton("ویرایش متن لابی", callback_data="edit_lobby_text")
        btn3 = types.InlineKeyboardButton("ارسال تست لابی", callback_data="send_test_lobby")
        markup.add(btn1, btn2, btn3)
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "تنظیمات لابی:", reply_markup=markup)
        return

    if data == "show_lobby_text":
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, f"متن لابی فعلی:\n{lobby_text}")
        return
    if data == "edit_lobby_text":
        pending_actions[user_id] = {"action": "edit_lobby_text", "chat_id": chat_id}
        bot.answer_callback_query(call.id, "لطفا متن جدید لابی را ارسال کنید (می‌توانید {time} را برای زمان قرار دهید)")
        return
    if data == "send_test_lobby":
        # ارسال لابی تست با تگ بازیکنان حاضر
        players = players_dict.get(chat_id, [])
        text = lobby_text.format(time="22:00")
        sent = bot.send_message(chat_id, text)
        mentions = " ".join([f"@{p}" for p in players])
        if mentions:
            bot.send_message(chat_id, mentions, reply_to_message_id=sent.message_id)
        bot.answer_callback_query(call.id, "لابی تست ارسال شد")
        return

# ------------------ هندلر پیام‌هایی که ادمین برای ویرایش می‌فرستد ------------------
@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    chat_id = str(message.chat.id)
    text = (message.text or "").strip()

    # اگر ادمین منتظر یک اکسیون باشه
    if user_id in pending_actions:
        action = pending_actions[user_id]["action"]
        target_chat = pending_actions[user_id].get("chat_id", chat_id)

        # اضافه کردن بازیکن از پنل (ادمین می‌تونه هر اسمی اضافه کنه)
        if action == "add_player":
            if not text.startswith("/"):
                bot.reply_to(message, "🚨 لطفا اسم را با / قبل ارسال کنید، مثال: /Ali")
                return
            name = text[1:].strip()
            res = add_name(name, target_chat)
            if res == "illegal":
                bot.reply_to(message, "🚨 نام غیرمجاز!")
            elif res is True:
                bot.reply_to(message, f"✔ {name} اضافه شد!")
                bot.reply_to(message, random.choice(funny_add_messages))
            else:
                bot.reply_to(message, "⚠️ اضافه نشد! یا لیست پر است یا قبلاً وجود داشت.")
            try:
                if target_chat in main_message_dict:
                    bot.edit_message_text(generate_list(target_chat), target_chat, main_message_dict[target_chat])
            except: pass
            pending_actions.pop(user_id, None)
            return

        # حذف بازیکن از پنل
        if action == "remove_player":
            if not text.startswith("/"):
                bot.reply_to(message, "🚨 لطفا اسم را با / قبل ارسال کنید، مثال: /Ali")
                return
            name = text[1:].strip()
            if remove_name(name, target_chat):
                bot.reply_to(message, f"❌ {name} حذف شد")
                bot.reply_to(message, random.choice(funny_remove_messages))
            else:
                bot.reply_to(message, "⚠️ آن نام در لیست نبود.")
            try:
                if target_chat in main_message_dict:
                    bot.edit_message_text(generate_list(target_chat), target_chat, main_message_dict[target_chat])
            except: pass
            pending_actions.pop(user_id, None)
            return

        # ویرایش ناظر 1/2
        if action in ("edit_nazor_1", "edit_nazor_2"):
            name = text.strip()
            if target_chat not in nazor_dict:
                nazor_dict[target_chat] = ["___", "___"]
            if action == "edit_nazor_1":
                nazor_dict[target_chat][0] = name
            else:
                nazor_dict[target_chat][1] = name
            save_data()
            bot.reply_to(message, f"👁‍🗨 ناظر ثبت شد: {name}")
            try:
                if target_chat in main_message_dict:
                    bot.edit_message_text(generate_list(target_chat), target_chat, main_message_dict[target_chat])
            except: pass
            pending_actions.pop(user_id, None)
            return

        # اضافه پیام فان اضافه
        if action == "add_fun_add":
            line = text.strip()
            if line:
                funny_add_messages.append(line)
                save_data()
                bot.reply_to(message, "✅ پیام اضافه جدید ذخیره شد.")
            else:
                bot.reply_to(message, "⚠️ متن خالی است.")
            pending_actions.pop(user_id, None)
            return

        # اضافه پیام فان حذف
        if action == "add_fun_remove":
            line = text.strip()
            if line:
                funny_remove_messages.append(line)
                save_data()
                bot.reply_to(message, "✅ پیام حذف جدید ذخیره شد.")
            else:
                bot.reply_to(message, "⚠️ متن خالی است.")
            pending_actions.pop(user_id, None)
            return

        # ویرایش متن لابی
        if action == "edit_lobby_text":
            new_text = text.strip()
            if new_text:
                global lobby_text
                lobby_text = new_text
                save_data()
                bot.reply_to(message, "✅ متن لابی ذخیره شد.")
            else:
                bot.reply_to(message, "⚠️ متن خالی است.")
            pending_actions.pop(user_id, None)
            return

    # اگر پیام عادی از کاربر عادی است (غیر از عملیات pending)، به هندلر اصلی واگذار می‌کنیم
    # هندلر فرمان‌های اصلی (/اسم، /ناظر، /لیست، /حذف و ...) را فراخوانی می‌کنیم
    # این بخش برای سازگاری با بقیه دستورات نوشته شده
    if not text.startswith("/"):
        bot.reply_to(message, "🚨 فرمان نامعتبره! لطفا قبل از ارسال / بگذارید")
        return

    cmd = text[1:].strip()
    if not cmd:
        bot.reply_to(message, "🚨 فرمان نامعتبره! لطفا بعد از / اسم یا دستور وارد کنید")
        return

    # ثبت ناظر با /ناظر 1 نام یا /ناظر 2 نام
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
                try:
                    bot.edit_message_text(generate_list(chat_id), chat_id, main_message_dict[chat_id])
                except: pass
        return

    # پیش‌بینی نقش‌ها
    if cmd.lower() in ["پیشبینی", "پیشبینی نقش"]:
        bot.reply_to(message, generate_role_prediction(chat_id))
        return

    # ریست (فقط ادمین یا ادمین‌های گروه)
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

    # حذف خود
    if cmd.lower() in ["حذف", "remove"]:
        user_name = message.from_user.username or message.from_user.first_name
        if remove_name(user_name, chat_id):
            bot.reply_to(message, random.choice(funny_remove_messages))
        else:
            bot.reply_to(message, "⚠️ شما در لیست نبودید!")
        if chat_id in main_message_dict:
            try:
                bot.edit_message_text(generate_list(chat_id), chat_id, main_message_dict[chat_id])
            except: pass
        return

    # ارسال لیست با /لیست
    if cmd.lower() == "لیست":
        if chat_id not in players_dict: players_dict[chat_id] = []
        if chat_id not in nazor_dict: nazor_dict[chat_id] = ["___","___"]
        sent = bot.send_message(chat_id, generate_list(chat_id))
        main_message_dict[chat_id] = sent.message_id
        try:
            bot.pin_chat_message(chat_id, sent.message_id, disable_notification=True)
        except: pass
        save_data()
        return

    # اضافه کردن بازیکن با /نام
    res = add_name(cmd, chat_id)
    if res == "illegal":
        bot.reply_to(message,"🚨 نام غیرمجاز!")
    elif res is True:
        bot.reply_to(message,f"✔ {cmd} اضافه شد!")
        bot.reply_to(message, random.choice(funny_add_messages))
    else:
        bot.reply_to(message,"⚠️ اضافه نشد! یا قبلا هست یا لیست پر است.")
    if chat_id in main_message_dict:
        try:
            bot.edit_message_text(generate_list(chat_id), chat_id, main_message_dict[chat_id])
        except: pass

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
