import telebot
from threading import Lock
import json, os, random
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz

# ------------------ تنظیمات اولیه ربات ------------------
bot = telebot.TeleBot('8549313349:AAFFuPlLNJTAHJI5B1Vl3PORCgI5d1wuUGw', parse_mode='html')

DATA_FILE = "players_data.json"
players_dict = {}
main_message_dict = {}
nazor_dict = {}
settings_dict = {}  # <--- متغیر جدید برای تنظیمات گروه
lock = Lock()

# متن‌های پیش‌فرض که قابل ویرایش خواهند بود
DEFAULT_SETTINGS = {
    "locked": False,
    "game_time": "22:00",
    "list_header_text": "♣️ <b>لیست شرکت کنندگان</b>\n🕙 راس ساعت {time}",
    "list_footer_text": "✨ فعال باشید!"
}

funny_add_messages = ["😎 اسم تو اضافه شد!", "😂 هیجان‌انگیز شد!", "🤣 چه بازیکن شجاعی!"]
funny_remove_messages = ["😅 خداحافظ!", "😂 اسم شما حذف شد!", "🤣 حذف شدی!"]

roles = ["شهروندساده", "شهروند ساده", "رییس مافیا", "شیاد", "ناتو", "رویین تن", "کاراگاه", "دکتر", "محقق", "بازپرس"]
illegal_names = ["مستانه", "مثتانه", "مصتانه"]

# ------------------ لیست آی‌دی اعضا برای تگ (بدون تغییر) ------------------
members_ids_list = [
    # ... لیست اعضای شما ...
    "davoodsaberii", "Mammaddasht", "Hadisnorozi", "AMIRABBAS6857", "Constantine2607",
    "Flower505", "Farjadparsa222", "Elinaz78", "Tbsoms8119", "shuhrukhind",
    "MRRrahimi", "Parsq", "Tthe_void", "ThanoS", "Zaki99841", "navidhmi",
    "M.A.B", "Feri00800", "NaziTala80", "mohammadkhz1380", "iDalef", "Frzam1234",
    "Matador7i", "Sevenfournine", "Xmsadeghhp77X", "arka12105", "MoonlightM8",
    "Zahra75a", "نـآزیـ🌼", "HosseinMO", "tf56vrji", "tanhavash_007", "Nima",
    "alik9066", "Miracle11", "Blackboy19980", "Azad_0017", "amirhtpr",
    "lonelyasfck", "Ninish8888", "𝐴𝑀𝐼𝑅𝐴𝐿𝐼᭄", "amnazm", "Shayadazavaleshtebah_bod",
    "Ravashzahra", "Sinabehroozian", "Rayansixpath"
]

# ------------------ داده‌ها (ذخیره و بارگذاری) ------------------
def load_data():
    global players_dict, nazor_dict, settings_dict
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            players_dict = data.get("players", {})
            nazor_dict = data.get("nazor", {})
            settings_dict = data.get("settings", {})
    else:
        players_dict = {}
        nazor_dict = {}
        settings_dict = {}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"players": players_dict, "nazor": nazor_dict, "settings": settings_dict}, f, ensure_ascii=False, indent=2)

# ------------------ توابع اصلی لیست (تولید، اضافه/حذف، ریست) ------------------
def get_chat_settings(chat_id):
    chat_id = str(chat_id)
    if chat_id not in settings_dict:
        settings_dict[chat_id] = DEFAULT_SETTINGS.copy()
        save_data()
    return settings_dict[chat_id]

def generate_list(chat_id):
    players = players_dict.get(str(chat_id), [])
    nazor = nazor_dict.get(str(chat_id), ["___", "___"])
    settings = get_chat_settings(chat_id)
    
    styles = [
        {"prefix1":"▪️","prefix2":"▫️","header_icon":"🃏"},
        {"prefix1":"🎭","prefix2":"🎲","header_icon":"🔥"},
        {"prefix1":"🟢","prefix2":"🔴","header_icon":"✨"},
        {"prefix1":"🔹","prefix2":"🔸","header_icon":"🌟"},
        {"prefix1":"⚡","prefix2":"💥","header_icon":"🎴"}
    ]
    style = random.choice(styles)
    
    # استفاده از تنظیمات ذخیره شده
    header = f"{style['header_icon']} <b>ᴍᴀғɪᴀ ᴏғ ɴɪɢʜᴛ</b> {style['header_icon']}\n"
    header += f"👁‍🗨 ناظر ۱: {nazor[0]} | ناظر ۲: {nazor[1]}\n"
    header += settings["list_header_text"].format(time=settings["game_time"]) + "\n〰〰〰\n📃 اسامی:\n"
    
    body = ""
    for i in range(1, 17):
        prefix = style['prefix1'] if i%2==1 else style['prefix2']
        name = players[i-1] if i-1 < len(players) else "___"
        body += f"{prefix} <b>{i}</b>- {name}\n"
        
    footer = "〰〰〰\n" + settings["list_footer_text"]
    
    # اضافه کردن وضعیت قفل به هدر
    if settings["locked"]:
        header += "🔒 **قفل شده - فقط ادمین می‌تواند اضافه کند.**\n"
        
    return header + body + footer

# توابع add_names، remove_name، reset_list و generate_role_prediction بدون تغییر منطق اصلی اینجا قرار می‌گیرند.
# ... (کدهای add_names، remove_name، reset_list و generate_role_prediction از کد قبلی) ...
# نکته: در تابع add_names باید شرط قفل بودن را اضافه کنید.
def add_names(text, chat_id, is_admin_call=False):
    chat_id = str(chat_id)
    settings = get_chat_settings(chat_id)
    
    if settings["locked"] and not is_admin_call:
        return "LOCKED" # علامت‌گذاری برای قفل بودن

    names = text.split()
    added = []
    with lock:
        if chat_id not in players_dict: players_dict[chat_id] = []
        
        for name in names:
            name = name.strip()
            if name and name not in players_dict[chat_id] and len(players_dict[chat_id]) < 16:
                players_dict[chat_id].append(name)
                added.append(name)
        save_data()
    return added

def remove_name(name, chat_id):
    # این تابع می‌تواند بدون تغییر باقی بماند
    with lock:
        if name in players_dict.get(str(chat_id),[]):
            players_dict[str(chat_id)].remove(name)
            save_data()
            return True
    return False

def reset_list(chat_id):
    chat_id = str(chat_id)
    with lock:
        players_dict[chat_id] = []
        nazor_dict[chat_id] = ["___", "___"]
        save_data()
        if chat_id in main_message_dict:
            try:
                bot.edit_message_text(generate_list(chat_id), chat_id, main_message_dict[chat_id])
            except Exception: pass

def generate_role_prediction(chat_id):
    # این تابع بدون تغییر باقی می‌ماند
    players = players_dict.get(str(chat_id), [])
    if not players:
        return "⚠️ لیست خالی است، پیش‌بینی ممکن نیست."
    role_list = roles.copy()
    roles_available = role_list.copy()
    random.shuffle(roles_available)
    prediction = ""
    for idx, player in enumerate(players):
        if not roles_available:
            roles_available = role_list.copy()
            random.shuffle(roles_available)
        role = roles_available.pop(0)
        prefix = "▪️" if idx%2==0 else "▫️"
        prediction += f"{prefix} {idx+1}- {player} - نقش: {role}\n"
    return "<b>پیش‌بینی نقش‌ها:</b>\n" + prediction


# ------------------ توابع پنل مدیریت (Admin Panel) ------------------
ADMIN_COMMAND = "/admin"

def is_admin(chat_id, user_id):
    """بررسی می‌کند که آیا کاربر ادمین گروه است یا خیر."""
    try:
        admins = bot.get_chat_administrators(chat_id)
        return user_id in [a.user.id for a in admins]
    except Exception:
        return False

# --- کیبوردهای شیشه‌ای ---
def get_admin_main_keyboard(chat_id):
    """کیبورد اصلی پنل ادمین."""
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton("➕/➖ مدیریت لیست بازیکنان", callback_data="admin_manage_players")
    )
    keyboard.row(
        telebot.types.InlineKeyboardButton("👁‍🗨 تنظیم ناظران", callback_data="admin_manage_nazor")
    )
    # اضافه شدن منوی تنظیمات
    keyboard.row(
        telebot.types.InlineKeyboardButton("🛠️ تنظیمات کلی ربات", callback_data="admin_settings_menu")
    )
    keyboard.row(
        telebot.types.InlineKeyboardButton("♻️ ریست کامل لیست", callback_data="admin_reset_list")
    )
    return keyboard

def get_settings_keyboard(chat_id):
    """کیبورد منوی تنظیمات."""
    settings = get_chat_settings(chat_id)
    lock_status = "باز" if not settings["locked"] else "قفل"
    keyboard = telebot.types.InlineKeyboardMarkup()
    
    keyboard.row(
        telebot.types.InlineKeyboardButton(f"🔒 وضعیت گروه: {lock_status} (تغییر)", callback_data="admin_toggle_lock")
    )
    keyboard.row(
        telebot.types.InlineKeyboardButton(f"⏰ ساعت بازی: {settings['game_time']} (تغییر)", callback_data="admin_prompt_time")
    )
    keyboard.row(
        telebot.types.InlineKeyboardButton("📝 ویرایش متن هدر لیست", callback_data="admin_prompt_header")
    )
    keyboard.row(
        telebot.types.InlineKeyboardButton("📝 ویرایش متن فوتر لیست", callback_data="admin_prompt_footer")
    )
    keyboard.row(
        telebot.types.InlineKeyboardButton("🔙 بازگشت به منو اصلی", callback_data="admin_main_menu")
    )
    return keyboard

def get_player_list_keyboard(chat_id):
    """کیبورد مدیریت لیست بازیکنان با دکمه‌های حذف."""
    # (بدون تغییر)
    keyboard = telebot.types.InlineKeyboardMarkup()
    players = players_dict.get(str(chat_id), [])
    
    for i, player in enumerate(players):
        callback_data = f"admin_remove_player_{i}"
        keyboard.add(telebot.types.InlineKeyboardButton(f"❌ {player}", callback_data=callback_data))

    keyboard.row(
        telebot.types.InlineKeyboardButton("➕ افزودن نام جدید", callback_data="admin_prompt_add"),
        telebot.types.InlineKeyboardButton("🔙 بازگشت به منو اصلی", callback_data="admin_main_menu")
    )
    return keyboard

def get_nazor_keyboard(chat_id):
    """کیبورد تنظیم ناظران."""
    # (بدون تغییر)
    keyboard = telebot.types.InlineKeyboardMarkup()
    nazor = nazor_dict.get(str(chat_id), ["___", "___"])
    
    keyboard.row(
        telebot.types.InlineKeyboardButton(f"👁‍🗨 ناظر ۱: {nazor[0]} (تغییر)", callback_data="admin_prompt_nazor_1")
    )
    keyboard.row(
        telebot.types.InlineKeyboardButton(f"👁‍🗨 ناظر ۲: {nazor[1]} (تغییر)", callback_data="admin_prompt_nazor_2")
    )
    keyboard.row(
        telebot.types.InlineKeyboardButton("🔙 بازگشت به منو اصلی", callback_data="admin_main_menu")
    )
    return keyboard

def get_player_list_text(chat_id):
    """متن لیست بازیکنان برای پنل ادمین."""
    # (بدون تغییر)
    players = players_dict.get(str(chat_id), [])
    text = "👥 **لیست فعلی شرکت کنندگان:**\n"
    if players:
        for i, player in enumerate(players):
            text += f"**{i+1}**- {player}\n"
    else:
        text += "⚠️ لیست خالی است."
    text += "\n\n روی نام هر بازیکن کلیک کنید تا **حذف** شود، یا از دکمه **افزودن** استفاده کنید."
    return text

# ------------------ هندلرهای ربات ------------------

@bot.message_handler(commands=['start'])
def start(message):
    chat_id=str(message.chat.id)
    with lock:
        if chat_id not in players_dict: players_dict[chat_id]=[]
        if chat_id not in nazor_dict: nazor_dict[chat_id]=["___","___"]
        if chat_id not in settings_dict: settings_dict[chat_id]=DEFAULT_SETTINGS.copy() # تضمین وجود تنظیمات
        
        sent=bot.send_message(chat_id, generate_list(chat_id))
        main_message_dict[chat_id]=sent.message_id
        try: bot.pin_chat_message(chat_id,sent.message_id,disable_notification=True)
        except Exception: pass
        bot.send_message(chat_id,"✔ لیست ارسال و پین شد.")
        save_data()

# ------------------ پنل مدیریت ادمین ------------------
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not is_admin(chat_id, user_id):
        bot.reply_to(message, "❌ **شما اجازه دسترسی به پنل ادمین را ندارید.**")
        return

    # تضمین وجود داده‌ها برای چت
    with lock:
        if str(chat_id) not in players_dict: players_dict[str(chat_id)]=[]
        if str(chat_id) not in nazor_dict: nazor_dict[str(chat_id)]=["___","___"]
        if str(chat_id) not in settings_dict: settings_dict[str(chat_id)]=DEFAULT_SETTINGS.copy()
        save_data()

    text = "👑 **پنل مدیریت ربات مافیا**\nلطفاً گزینه مورد نظر خود را انتخاب کنید:"
    bot.send_message(chat_id, text, reply_markup=get_admin_main_keyboard(chat_id), parse_mode='Markdown')

# ... (هندلر send_current_list بدون تغییر) ...

@bot.message_handler(func=lambda m: any(kw in m.text.lower() for kw in ["لیست", "لیست بفرست"]))
def send_current_list(message):
    chat_id = str(message.chat.id)
    if chat_id not in players_dict: players_dict[chat_id] = []
    if chat_id not in nazor_dict: nazor_dict[chat_id] = ["___","___"]
    sent = bot.send_message(chat_id, generate_list(chat_id))
    main_message_dict[chat_id] = sent.message_id
    try:
        bot.pin_chat_message(chat_id, sent.message_id, disable_notification=True)
    except Exception:
        pass

@bot.message_handler(func=lambda m: True)
def reply_handler(message):
    chat_id=str(message.chat.id)
    if chat_id not in main_message_dict: return
    text=message.text.strip()
    user_name=message.from_user.username or message.from_user.first_name
    
    # ... (بقیه کدهای لابی ساعت و ریپلای روی لیست بدون تغییر منطق اصلی) ...
    # ... (بجز بخش اضافه کردن اسامی) ...

    # ---------- پیام لابی ساعت ----------
    if "لابی ساعت" in text:
        try:
            sent_msg = bot.send_message(chat_id, text)
            bot.pin_chat_message(chat_id, sent_msg.message_id, disable_notification=True)

            # ارسال ریپلای با تگ همه اعضا
            mentions_text = ""
            for username in members_ids_list:
                mentions_text += f"@{username} "
            bot.send_message(chat_id, mentions_text, reply_to_message_id=sent_msg.message_id)

            bot.reply_to(message, "📌 پیام لابی کپی شد، پین شد و اعضا تگ شدند!")
        except Exception as e:
            bot.reply_to(message, f"❌ خطا: {e}")
        return

    # ---------- پیام ریپلای روی لیست ----------
    if not message.reply_to_message: return
    if message.reply_to_message.message_id != main_message_dict[chat_id]: return

    if text in illegal_names:
        bot.reply_to(message,"🚨 <b>هشدار!</b>\nنام خطرناک!")
        return

    # ناظر (روش قدیمی برای کاربر عادی)
    if text.startswith("ناظر"):
        parts=text.split()
        if len(parts)>=3:
            nazor_type = parts[1]
            nazor_name = " ".join(parts[2:]).strip()
            if nazor_type in ["1","یک","۱"]: nazor_dict[chat_id][0]=nazor_name
            elif nazor_type in ["2","دو","۲"]: nazor_dict[chat_id][1]=nazor_name
            bot.reply_to(message,f"👁‍🗨 ناظر ثبت شد: {nazor_name}")
            save_data()
            bot.edit_message_text(generate_list(chat_id),chat_id,main_message_dict[chat_id])
            return

    # اضافه کردن الی
    if text=="الی":
        added_result=add_names(text,chat_id)
        if added_result == "LOCKED":
             bot.reply_to(message,"🔒 گروه قفل است! فقط ادمین می‌تواند اسم اضافه کند.")
        elif added_result: 
            bot.reply_to(message,"😂 الی نمک نشناس است!")
        bot.edit_message_text(generate_list(chat_id),chat_id,main_message_dict[chat_id])
        return

    # پیش‌بینی نقش‌ها
    if text.lower() in ["پیشبینی","پیشبینی نقش"]:
        bot.reply_to(message, generate_role_prediction(chat_id))
        return

    # ریست (روش قدیمی برای ادمین)
    if text=="ریست":
        try:
            if is_admin(message.chat.id, message.from_user.id):
                reset_list(chat_id)
                bot.reply_to(message,"♻️ لیست ریست شد.")
            else: bot.reply_to(message,"❌ فقط ادمین")
        except Exception: pass
        return

    # حذف خود
    if text.lower() in ["حذف","delete","remove","حذف نام"]:
        removed=remove_name(user_name,chat_id)
        if removed: 
            bot.reply_to(message,"❌ حذف شد.")
            bot.reply_to(message, random.choice(funny_remove_messages))
        else: 
            bot.reply_to(message,"⚠️ نام نبود")
        bot.edit_message_text(generate_list(chat_id),chat_id,main_message_dict[chat_id])
        return

    # حذف دیگران
    if text.startswith("حذف "):
        target=text.replace("حذف ","").strip()
        removed=remove_name(target,chat_id)
        if removed: 
            bot.reply_to(message,f"❌ {target} حذف شد")
            bot.reply_to(message, random.choice(funny_remove_messages))
        else: 
            bot.reply_to(message,f"⚠️ {target} داخل لیست نبود")
        bot.edit_message_text(generate_list(chat_id),chat_id,main_message_dict[chat_id])
        return

    # اضافه کردن اسامی (در صورت قفل نبودن)
    added_result=add_names(text,chat_id)
    if added_result == "LOCKED":
        bot.reply_to(message,"🔒 گروه قفل است! فقط ادمین می‌تواند اسم اضافه کند.")
    elif added_result:
        bot.reply_to(message,f"✔ اضافه شدند: {', '.join(added_result)}")
        bot.reply_to(message, random.choice(funny_add_messages))
    else:
        bot.reply_to(message,"⚠️ اسمی اضافه نشد")
    bot.edit_message_text(generate_list(chat_id),chat_id,main_message_dict[chat_id])


# ------------------ هندلر کلیک روی دکمه‌های شیشه‌ای (پنل ادمین) ------------------
@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def admin_callback_query(call):
    chat_id = str(call.message.chat.id)
    message_id = call.message.message_id
    user_id = call.from_user.id
    data = call.data

    if not is_admin(chat_id, user_id):
        bot.answer_callback_query(call.id, "❌ شما مدیر نیستید!", show_alert=True)
        return
        
    # --- مدیریت منوها ---
    if data == "admin_main_menu":
        text = "👑 **پنل مدیریت ربات مافیا**\nلطفاً گزینه مورد نظر خود را انتخاب کنید:"
        bot.edit_message_text(text, chat_id, message_id, reply_markup=get_admin_main_keyboard(chat_id), parse_mode='Markdown')
        bot.answer_callback_query(call.id, "بازگشت به منوی اصلی")

    elif data == "admin_manage_players":
        text = get_player_list_text(chat_id)
        keyboard = get_player_list_keyboard(chat_id)
        bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard, parse_mode='Markdown')
        bot.answer_callback_query(call.id, "مدیریت لیست فعال شد")

    elif data == "admin_manage_nazor":
        text = "👁‍🗨 **تنظیم ناظران**\nبرای تغییر نام ناظر، روی دکمه مربوطه کلیک کنید."
        keyboard = get_nazor_keyboard(chat_id)
        bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard, parse_mode='Markdown')
        bot.answer_callback_query(call.id, "مدیریت ناظران فعال شد")

    elif data == "admin_settings_menu":
        settings = get_chat_settings(chat_id)
        lock_status = "قفل" if settings["locked"] else "باز"
        text = f"🛠️ **تنظیمات کلی ربات**\n"
        text += f"وضعیت قفل: **{lock_status}**\n"
        text += f"ساعت بازی: **{settings['game_time']}**\n"
        text += "\nگزینه مورد نظر برای تغییر را انتخاب کنید:"
        keyboard = get_settings_keyboard(chat_id)
        bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard, parse_mode='Markdown')
        bot.answer_callback_query(call.id, "پنل تنظیمات فعال شد")

    # --- مدیریت بازیکنان و ناظران (همانند قبل) ---
    elif data.startswith("admin_remove_player_"):
        index = int(data.split('_')[-1])
        with lock:
            players = players_dict.get(chat_id, [])
            if 0 <= index < len(players):
                player_to_remove = players.pop(index)
                save_data()
                bot.answer_callback_query(call.id, f"❌ {player_to_remove} حذف شد!", show_alert=False)
            
        text = get_player_list_text(chat_id)
        keyboard = get_player_list_keyboard(chat_id)
        bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard, parse_mode='Markdown')
        if chat_id in main_message_dict:
            try: bot.edit_message_text(generate_list(chat_id), chat_id, main_message_dict[chat_id])
            except Exception: pass

    elif data == "admin_prompt_add":
        bot.answer_callback_query(call.id, "لطفاً نام یا اسامی (با فاصله) را ارسال کنید.")
        bot.send_message(chat_id, "✍️ **لطفاً نام یا اسامی بازیکنان جدید را در یک پیام برای من ارسال کنید.** (مثال: `علی رضا مریم`)\n\nبا ارسال `/cancel` لغو کنید.", parse_mode='Markdown')
        bot.register_next_step_handler(call.message, add_player_by_admin, call.message)

    elif data.startswith("admin_prompt_nazor_"):
        nazor_index = 0 if data.endswith("_1") else 1
        bot.answer_callback_query(call.id, f"لطفاً نام ناظر {nazor_index+1} را ارسال کنید.")
        bot.send_message(chat_id, f"✍️ **لطفاً نام ناظر {nazor_index+1} را در یک پیام برای من ارسال کنید.**\n\nبا ارسال `/cancel` لغو کنید.", parse_mode='Markdown')
        bot.register_next_step_handler(call.message, set_nazor_by_admin, nazor_index, call.message)

    elif data == "admin_reset_list":
        reset_list(chat_id)
        bot.answer_callback_query(call.id, "✅ لیست ریست شد!", show_alert=True)
        text = "👑 **پنل مدیریت ربات مافیا**\n♻️ لیست با موفقیت ریست شد."
        bot.edit_message_text(text, chat_id, message_id, reply_markup=get_admin_main_keyboard(chat_id), parse_mode='Markdown')


    # --- تنظیمات جدید (ساعت، قفل، متن) ---
    elif data == "admin_toggle_lock":
        settings = get_chat_settings(chat_id)
        settings["locked"] = not settings["locked"]
        save_data()
        
        status_msg = "قفل شد. فقط ادمین می‌تواند اسم اضافه کند." if settings["locked"] else "باز شد. همه می‌توانند اسم اضافه کنند."
        bot.answer_callback_query(call.id, f"✅ گروه {status_msg}", show_alert=True)
        
        # به‌روزرسانی پنل و لیست پین شده
        admin_callback_query(telebot.types.CallbackQuery(id=call.id, from_user=call.from_user, message=call.message, data="admin_settings_menu"))
        if chat_id in main_message_dict:
            try: bot.edit_message_text(generate_list(chat_id), chat_id, main_message_dict[chat_id])
            except Exception: pass
            
    elif data == "admin_prompt_time":
        bot.answer_callback_query(call.id, "لطفاً ساعت بازی را وارد کنید (مثال: 22:30).")
        bot.send_message(chat_id, "⏰ **لطفاً ساعت جدید بازی (فقط ساعت و دقیقه) را در فرمت `HH:MM` ارسال کنید.**\n\nبا ارسال `/cancel` لغو کنید.", parse_mode='Markdown')
        bot.register_next_step_handler(call.message, set_game_time_by_admin, call.message)
        
    elif data == "admin_prompt_header":
        settings = get_chat_settings(chat_id)
        bot.answer_callback_query(call.id, "لطفاً متن جدید هدر را وارد کنید.")
        bot.send_message(chat_id, f"📝 **لطفاً متن جدید هدر لیست را ارسال کنید.**\n*توجه: از `{}` برای نمایش زمان استفاده کنید.* (متن فعلی: `{settings['list_header_text']}`)\n\nبا ارسال `/cancel` لغو کنید.", parse_mode='Markdown')
        bot.register_next_step_handler(call.message, set_list_text_by_admin, "list_header_text", call.message)
        
    elif data == "admin_prompt_footer":
        settings = get_chat_settings(chat_id)
        bot.answer_callback_query(call.id, "لطفاً متن جدید فوتر را وارد کنید.")
        bot.send_message(chat_id, f"📝 **لطفاً متن جدید فوتر لیست را ارسال کنید.** (متن فعلی: `{settings['list_footer_text']}`)\n\nبا ارسال `/cancel` لغو کنید.", parse_mode='Markdown')
        bot.register_next_step_handler(call.message, set_list_text_by_admin, "list_footer_text", call.message)


# ------------------ توابع پردازش ورودی‌های بعدی (Next Step Handlers) ------------------

def add_player_by_admin(message, original_message):
    chat_id = str(message.chat.id)
    if message.text and message.text.lower() == "/cancel":
        bot.send_message(chat_id, "عملیات افزودن لغو شد.")
        return

    # استفاده از is_admin_call=True برای دور زدن قفل در پنل ادمین
    added = add_names(message.text, chat_id, is_admin_call=True)

    if added:
        bot.send_message(chat_id, f"✅ **اسامی جدید با موفقیت اضافه شدند:** {', '.join(added)}", parse_mode='Markdown')
        if chat_id in main_message_dict:
            try: bot.edit_message_text(generate_list(chat_id), chat_id, main_message_dict[chat_id])
            except Exception: pass
    else:
        bot.send_message(chat_id, "⚠️ هیچ نامی اضافه نشد. (شاید لیست پر یا نام‌ها تکراری بودند)")
    
    text = get_player_list_text(chat_id)
    keyboard = get_player_list_keyboard(chat_id)
    bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode='Markdown')


def set_nazor_by_admin(message, nazor_index, original_message):
    # (بدون تغییر)
    chat_id = str(message.chat.id)
    if message.text and message.text.lower() == "/cancel":
        bot.send_message(chat_id, "عملیات تنظیم ناظر لغو شد.")
        return

    nazor_name = message.text.strip()
    
    with lock:
        if chat_id not in nazor_dict: nazor_dict[chat_id] = ["___", "___"]
        nazor_dict[chat_id][nazor_index] = nazor_name
        save_data()

    bot.send_message(chat_id, f"✅ **ناظر {nazor_index+1} با موفقیت به** `{nazor_name}` **تغییر یافت.**", parse_mode='Markdown')
    
    if chat_id in main_message_dict:
        try: bot.edit_message_text(generate_list(chat_id), chat_id, main_message_dict[chat_id])
        except Exception: pass
    
    text = "👁‍🗨 **تنظیم ناظران**\nبرای تغییر نام ناظر، روی دکمه مربوطه کلیک کنید."
    keyboard = get_nazor_keyboard(chat_id)
    bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode='Markdown')

def set_game_time_by_admin(message, original_message):
    chat_id = str(message.chat.id)
    if message.text and message.text.lower() == "/cancel":
        bot.send_message(chat_id, "عملیات تنظیم ساعت لغو شد.")
        return
        
    new_time = message.text.strip()
    # اعتبارسنجی ساده برای فرمت ساعت HH:MM
    try:
        datetime.strptime(new_time, '%H:%M')
        valid_time = True
    except ValueError:
        valid_time = False

    if valid_time:
        settings = get_chat_settings(chat_id)
        settings["game_time"] = new_time
        save_data()
        
        bot.send_message(chat_id, f"✅ **ساعت بازی با موفقیت به** `{new_time}` **تغییر یافت.**", parse_mode='Markdown')
        if chat_id in main_message_dict:
            try: bot.edit_message_text(generate_list(chat_id), chat_id, main_message_dict[chat_id])
            except Exception: pass
    else:
        bot.send_message(chat_id, "❌ **فرمت ساعت نامعتبر است.** لطفاً از فرمت `HH:MM` (مثلاً 21:00) استفاده کنید.")

    # نمایش مجدد منوی تنظیمات
    admin_callback_query(telebot.types.CallbackQuery(id=message.message_id, from_user=message.from_user, message=message, data="admin_settings_menu"))

def set_list_text_by_admin(message, setting_key, original_message):
    chat_id = str(message.chat.id)
    if message.text and message.text.lower() == "/cancel":
        bot.send_message(chat_id, "عملیات تنظیم متن لغو شد.")
        return
        
    new_text = message.text.strip()
    settings = get_chat_settings(chat_id)
    
    # اطمینان از وجود placeholder در هدر
    if setting_key == "list_header_text" and "{time}" not in new_text:
        bot.send_message(chat_id, "⚠️ **متن هدر باید شامل `{time}` باشد** تا ساعت بازی نمایش داده شود.")
    else:
        settings[setting_key] = new_text
        save_data()
        
        bot.send_message(chat_id, "✅ **متن با موفقیت به‌روزرسانی شد.**", parse_mode='Markdown')
        if chat_id in main_message_dict:
            try: bot.edit_message_text(generate_list(chat_id), chat_id, main_message_dict[chat_id])
            except Exception: pass

    # نمایش مجدد منوی تنظیمات
    admin_callback_query(telebot.types.CallbackQuery(id=message.message_id, from_user=message.from_user, message=message, data="admin_settings_menu"))

# ------------------ زمان‌بندی و اجرا ------------------
def schedule_jobs():
    # ... (بدون تغییر منطق اصلی زمان‌بندی) ...
    tz=pytz.timezone("Asia/Tehran")
    scheduler = BackgroundScheduler(timezone=tz)
    
    # ریست لیست در ساعت 22:00
    scheduler.add_job(lambda:[reset_list(cid) for cid in players_dict.keys()], 'cron', hour=22, minute=0)
    
    # ارسال یادآوری در ساعت 20:30
    def send_reminder():
        for cid in players_dict.keys():
            try: bot.send_message(cid,"⏰ بازی امشب ساعت 22 شروع می‌شود!")
            except Exception: pass
    scheduler.add_job(send_reminder,'cron',hour=20,minute=30)
    scheduler.start()

# ------------------ شروع ربات ------------------
load_data()
schedule_jobs()
print("Bot started...")
bot.polling(none_stop=True)
