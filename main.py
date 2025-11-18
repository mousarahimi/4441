# -*- coding: utf-8 -*-
import telebot
from telebot import types
from threading import Lock
import json, os, random
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

# ------------------ تنظیمات ------------------
BOT_TOKEN = "8549313349:AAFFuPlLNJTAHJI5B1Vl3PORCgI5d1wuUGw"        # <-- اینو عوض کن
ADMIN_IDS = [5382898102]             # <-- شناسه(های) ادمین رو اینجا بگذار

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="html")
DATA_FILE = "players_data.json"

lock = Lock()
players_dict = {}       # structure: { chat_id_str: [ player_entry, ... ] }
                        # player_entry can be:
                        #  {"name": "Ali", "username": "ali_user", "user_id": 12345}
                        #  or legacy string "Ali" (we normalize on load)
nazor_dict = {}         # { chat_id_str: [nazor1, nazor2] }
main_message_dict = {}  # { chat_id_str: message_id_of_main_list }
pending_actions = {}    # { admin_user_id: {"action":..., "chat_id":... , ...} }

# تنظیمات قابل ویرایش
funny_add_messages = ["😎 اسم تو اضافه شد!", "😂 هیجان‌انگیز شد!", "🤣 چه بازیکن شجاعی!"]
funny_remove_messages = ["😅 خداحافظ!", "😂 اسم شما حذف شد!", "🤣 حذف شدی!"]
lobby_text = "لابی ساعت {time} — لطفاً آماده باشید!"

roles = ["شهروندساده", "شهروند ساده", "رییس مافیا", "شیاد", "ناتو", "رویین تن", "کاراگاه", "دکتر", "محقق", "بازپرس"]
illegal_names = ["مستانه", "مثتانه", "مصتانه"]

# ------------------ بارگذاری / ذخیره ------------------
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
        # normalize legacy entries (strings -> dicts where possible)
        for cid, lst in list(players_dict.items()):
            newlist = []
            for entry in lst:
                if isinstance(entry, str):
                    # legacy: just name string
                    newlist.append({"name": entry, "username": None, "user_id": None})
                elif isinstance(entry, dict):
                    # ensure keys exist
                    newlist.append({
                        "name": entry.get("name") or entry.get("display_name") or entry.get("username") or "___",
                        "username": entry.get("username"),
                        "user_id": entry.get("user_id")
                    })
                else:
                    # unknown -> skip
                    continue
            players_dict[cid] = newlist
    else:
        players_dict = {}
        nazor_dict = {}

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

# ------------------ یوتیلیتی‌ها ------------------
def update_main_message(chat_id_str):
    """ویرایش پیام اصلی لیست در صورت وجود"""
    if chat_id_str in main_message_dict:
        try:
            bot.edit_message_text(generate_list(chat_id_str), int(chat_id_str), main_message_dict[chat_id_str])
        except Exception:
            pass

def find_player_index_by_name_or_username_or_id(chat_id_str, target):
    """برمی‌گرداند index یا None؛ target می‌تواند user_id (int) یا username/name string"""
    players = players_dict.get(chat_id_str, [])
    if not players:
        return None
    # اگر عدد داده شده (user id)
    try:
        t_id = int(target)
        for i, p in enumerate(players):
            if p.get("user_id") == t_id:
                return i
    except Exception:
        pass
    # مقایسه با یوزرنیم یا نام (حساس به case-insensitive)
    tt = str(target).lstrip("@").strip().lower()
    for i, p in enumerate(players):
        # username
        if p.get("username"):
            if p["username"].lstrip("@").lower() == tt:
                return i
        # name
        if p.get("name") and p["name"].lower() == tt:
            return i
    return None

# ------------------ تولید لیست ------------------
def generate_list(chat_id_str):
    players = players_dict.get(str(chat_id_str), [])
    nazor = nazor_dict.get(str(chat_id_str), ["___", "___"])
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
        if i-1 < len(players):
            p = players[i-1]
            display = p.get("name") or (("@"+p.get("username")) if p.get("username") else "___")
        else:
            display = "___"
        body += f"{prefix} <b>{i}</b>- {display}\n"
    footer = "〰〰〰\n✨ فعال باشید!"
    return header + body + footer

# ------------------ اضافه کردن بازیکن ------------------
def add_name_from_user(name_str, chat_id_str, user_obj=None):
    """
    وقتی کاربر خودش /name میفرسته: user_obj را بده (message.from_user)
    اگر user_obj موجود باشه، ذخیره user_id و username انجام میشه تا بتوان تگ و چک حضور کرد.
    """
    name = name_str.strip()
    if not name:
        return False, "empty"
    if name in illegal_names:
        return False, "illegal"

    with lock:
        if chat_id_str not in players_dict:
            players_dict[chat_id_str] = []
        # بررسی پر بودن
        if len(players_dict[chat_id_str]) >= 16:
            return False, "full"
        # اگر user_obj داده شده سعی می‌کنیم entry یکتا بر اساس user_id بسازیم
        if user_obj:
            uid = getattr(user_obj, "id", None)
            uname = getattr(user_obj, "username", None)
            # اگر کاربر قبلاً بر اساس id وجود داره -> به‌روزرسانی نام نمایشی در صورت نیاز
            if uid:
                for p in players_dict[chat_id_str]:
                    if p.get("user_id") == uid:
                        # already present
                        p["name"] = name
                        p["username"] = uname
                        save_data()
                        return False, "exists"
            # اگر یوزرنیم تکراری بود ولی با id متفاوت (نادر) هم حذف می‌کنیم ورودی قدیمی
            if uname:
                for p in players_dict[chat_id_str]:
                    if p.get("username") and p["username"].lstrip("@").lower() == uname.lstrip("@").lower():
                        # update with real id
                        p["user_id"] = uid
                        p["name"] = name
                        save_data()
                        return False, "exists"
            # اضافه کردن جدید
            players_dict[chat_id_str].append({"name": name, "username": uname, "user_id": uid})
            save_data()
            return True, "added"
        else:
            # بدون user_obj: فقط اضافه بر اساس نام آزاد (ممکنه admin باشه که اسم رو اضافه میکنه)
            # ابتدا چک کنیم که اسم مشابه وجود نداشته باشه
            for p in players_dict[chat_id_str]:
                if p.get("name") and p["name"].lower() == name.lower():
                    return False, "exists"
            players_dict[chat_id_str].append({"name": name, "username": None, "user_id": None})
            save_data()
            return True, "added"

# ------------------ حذف بازیکن (محکم و منعطف) ------------------
def remove_player(chat_id_str, target, by_user_id=None):
    """
    target می‌تواند:
      - int user_id
      - "@username" یا "username"
      - "display name"
    اگر by_user_id داده شود یعنی کاربر خودش درخواست حذف رو داده -> مطابق آن حذف را دقیق‌تر انجام می‌دهیم
    """
    with lock:
        if chat_id_str not in players_dict:
            return False
        idx = None
        # تلاش برای تشخیص به عنوان عدد (user_id)
        try:
            t = int(target)
            idx = find_player_index_by_name_or_username_or_id(chat_id_str, t)
        except Exception:
            idx = find_player_index_by_name_or_username_or_id(chat_id_str, target)
        if idx is not None:
            players_dict[chat_id_str].pop(idx)
            save_data()
            return True
        # اگر by_user_id داده شده، سعی کن بر اساس آن حذف کنی
        if by_user_id:
            idx = find_player_index_by_name_or_username_or_id(chat_id_str, by_user_id)
            if idx is not None:
                players_dict[chat_id_str].pop(idx)
                save_data()
                return True
        return False

# ------------------ تولید پیش‌بینی نقش ------------------
def generate_role_prediction_str(chat_id_str):
    players = players_dict.get(str(chat_id_str), [])
    if not players:
        return "⚠️ لیست خالی است، پیش‌بینی ممکن نیست."
    pool = roles.copy()
    random.shuffle(pool)
    pred = "<b>پیش‌بینی نقش‌ها:</b>\n"
    for i, p in enumerate(players):
        role = pool[i % len(pool)]
        display = p.get("name") or (("@"+p.get("username")) if p.get("username") else "___")
        prefix = "▪️" if i%2==0 else "▫️"
        pred += f"{prefix} {i+1}- {display} - نقش: {role}\n"
    return pred

# ------------------ دکوراتور ادمین ------------------
def admin_required(func):
    def wrapper(message, *args, **kwargs):
        if message.from_user.id not in ADMIN_IDS:
            bot.reply_to(message, "❌ فقط ادمین اجازه دارد")
            return
        return func(message, *args, **kwargs)
    return wrapper

# ------------------ هندلر ارسال لیست (/لیست و /start) ------------------
@bot.message_handler(commands=['start', 'لیست'])
def cmd_list(message):
    chat_id_str = str(message.chat.id)
    with lock:
        if chat_id_str not in players_dict:
            players_dict[chat_id_str] = []
        if chat_id_str not in nazor_dict:
            nazor_dict[chat_id_str] = ["___", "___"]
        sent = bot.send_message(message.chat.id, generate_list(chat_id_str))
        main_message_dict[chat_id_str] = sent.message_id
        try:
            bot.pin_chat_message(message.chat.id, sent.message_id, disable_notification=True)
        except Exception:
            pass
        save_data()

# ------------------ لابی: تگ بازیکنان حاضر (فقط کسانی که user_id دارند و هنوز در گروه هستند) ------------------
@bot.message_handler(func=lambda m: m.text and "لابی ساعت" in m.text)
def lobby_message_handler(message):
    chat_id = message.chat.id
    chat_id_str = str(chat_id)
    try:
        sent = bot.send_message(chat_id, message.text)
        try:
            bot.pin_chat_message(chat_id, sent.message_id, disable_notification=True)
        except: pass

        # ساخت mentions با user_id ها و چک حضور
        mentions = []
        for p in players_dict.get(chat_id_str, []):
            uid = p.get("user_id")
            if uid:
                try:
                    member = bot.get_chat_member(chat_id, uid)
                    # اگر عضو باشند، mention با لینک
                    if member and not member.user.is_bot:
                        name = p.get("name") or member.user.first_name or "کاربر"
                        mentions.append(f"<a href='tg://user?id={uid}'>{name}</a>")
                except Exception:
                    # کاربر لفت داده یا دسترسی نیست -> ردش کن
                    continue
        if mentions:
            # پیام تگ‌ها رو ارسال کن
            bot.send_message(chat_id, " ".join(mentions), reply_to_message_id=sent.message_id)
        bot.reply_to(message, "📌 پیام لابی ارسال و اعضای حاضر تگ شدند!")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا در ارسال لابی: {e}")

# ------------------ پنل مدیریتی پیشرفته (/panel) ------------------
@bot.message_handler(commands=['panel'])
def open_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ فقط ادمین اجازه دارد")
        return
    chat_id_str = str(message.chat.id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton("📃 نمایش لیست", callback_data="show_list"),
        types.InlineKeyboardButton("➕ اضافه بازیکن", callback_data="add_player"),
        types.InlineKeyboardButton("➖ حذف بازیکن", callback_data="remove_player"),
        types.InlineKeyboardButton("✏️ ویرایش بازیکن", callback_data="edit_player"),
        types.InlineKeyboardButton("👁‍🗨 مدیریت ناظر", callback_data="manage_nazor"),
        types.InlineKeyboardButton("♻️ ریست لیست", callback_data="reset_list"),
        types.InlineKeyboardButton("🎭 پیش‌بینی نقش", callback_data="role_prediction"),
        types.InlineKeyboardButton("📝 پیام‌های فان", callback_data="fun_messages"),
        types.InlineKeyboardButton("📢 تنظیمات لابی", callback_data="lobby_settings"),
        types.InlineKeyboardButton("📊 آمار", callback_data="show_stats")
    ]
    for b in buttons:
        markup.add(b)
    bot.send_message(message.chat.id, "پنل مدیریتی پیشرفته:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    chat_id_str = str(call.message.chat.id)
    data = call.data

    if user_id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ فقط ادمین")
        return

    # نمایش لیست
    if data == "show_list":
        try:
            bot.edit_message_text(generate_list(chat_id_str), call.message.chat.id, call.message.message_id)
        except:
            bot.send_message(call.message.chat.id, generate_list(chat_id_str))
        bot.answer_callback_query(call.id)
        return

    # اضافه بازیکن (در انتظار input)
    if data == "add_player":
        pending_actions[user_id] = {"action": "add_player", "chat_id": chat_id_str}
        bot.answer_callback_query(call.id, "لطفا اسم بازیکن را با /قبل ارسال کنید (مثال: /Ali)")
        return

    # حذف بازیکن (در انتظار input)
    if data == "remove_player":
        pending_actions[user_id] = {"action": "remove_player", "chat_id": chat_id_str}
        bot.answer_callback_query(call.id, "لطفا اسم یا یوزرنیم را با / قبل ارسال کنید (مثال: /Ali یا /@ali)\nیا روی پیام ریپلای کنید و /حذف را بزنید.")
        return

    # ویرایش بازیکن
    if data == "edit_player":
        pending_actions[user_id] = {"action": "edit_player_select", "chat_id": chat_id_str}
        bot.answer_callback_query(call.id, "لطفا نام یا یوزرنیم بازیکن مورد نظر را با / ارسال کنید تا ویرایش شود.")
        return

    # مدیریت ناظر
    if data == "manage_nazor":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("ناظر 1 ✏️", callback_data="edit_nazor_1"),
            types.InlineKeyboardButton("ناظر 2 ✏️", callback_data="edit_nazor_2"),
            types.InlineKeyboardButton("ریست ناظرها 🔄", callback_data="reset_nazors")
        )
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "مدیریت ناظرها:", reply_markup=markup)
        return

    if data == "edit_nazor_1":
        pending_actions[user_id] = {"action": "edit_nazor_1", "chat_id": chat_id_str}
        bot.answer_callback_query(call.id, "لطفا نام جدید ناظر 1 را ارسال کنید (بدون /).")
        return
    if data == "edit_nazor_2":
        pending_actions[user_id] = {"action": "edit_nazor_2", "chat_id": chat_id_str}
        bot.answer_callback_query(call.id, "لطفا نام جدید ناظر 2 را ارسال کنید (بدون /).")
        return
    if data == "reset_nazors":
        nazor_dict[chat_id_str] = ["___", "___"]
        save_data()
        update_main_message(chat_id_str)
        bot.answer_callback_query(call.id, "ناظرها ریست شدند")
        return

    # ریست لیست
    if data == "reset_list":
        reset_list(chat_id_str)
        bot.answer_callback_query(call.id, "♻️ لیست ریست شد")
        try:
            bot.edit_message_text(generate_list(chat_id_str), call.message.chat.id, call.message.message_id)
        except:
            pass
        return

    # پیش‌بینی نقش
    if data == "role_prediction" or data == "role_prediction":
        bot.answer_callback_query(call.id, "🎭 پیش‌بینی نقش‌ها ارسال شد")
        bot.send_message(call.message.chat.id, generate_role_prediction_str(chat_id_str))
        return

    # مدیریت پیام‌های فان
    if data == "fun_messages":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("نمایش پیام‌های اضافه", callback_data="show_fun_add"),
            types.InlineKeyboardButton("افزودن پیام اضافه", callback_data="add_fun_add"),
            types.InlineKeyboardButton("نمایش پیام‌های حذف", callback_data="show_fun_remove"),
            types.InlineKeyboardButton("افزودن پیام حذف", callback_data="add_fun_remove")
        )
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "مدیریت پیام‌های فان:", reply_markup=markup)
        return

    if data == "show_fun_add":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "پیام‌های اضافه:\n" + "\n".join(funny_add_messages))
        return
    if data == "show_fun_remove":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "پیام‌های حذف:\n" + "\n".join(funny_remove_messages))
        return
    if data == "add_fun_add":
        pending_actions[user_id] = {"action": "add_fun_add", "chat_id": chat_id_str}
        bot.answer_callback_query(call.id, "لطفا پیام جدید اضافه را ارسال کنید (بدون /).")
        return
    if data == "add_fun_remove":
        pending_actions[user_id] = {"action": "add_fun_remove", "chat_id": chat_id_str}
        bot.answer_callback_query(call.id, "لطفا پیام جدید حذف را ارسال کنید (بدون /).")
        return

    # لابی
    if data == "lobby_settings":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("نمایش متن لابی", callback_data="show_lobby_text"),
            types.InlineKeyboardButton("ویرایش متن لابی", callback_data="edit_lobby_text"),
            types.InlineKeyboardButton("ارسال تست لابی", callback_data="send_test_lobby")
        )
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "تنظیمات لابی:", reply_markup=markup)
        return
    if data == "show_lobby_text":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"متن لابی فعلی:\n{lobby_text}")
        return
    if data == "edit_lobby_text":
        pending_actions[user_id] = {"action": "edit_lobby_text", "chat_id": chat_id_str}
        bot.answer_callback_query(call.id, "لطفا متن جدید لابی را ارسال کنید (می‌توانید {time} را قرار دهید).")
        return
    if data == "send_test_lobby":
        # send test
        ch_id = int(chat_id_str)
        sent = bot.send_message(ch_id, lobby_text.format(time="22:00"))
        mentions = []
        for p in players_dict.get(chat_id_str, []):
            if p.get("user_id"):
                mentions.append(f"<a href='tg://user?id={p.get('user_id')}'>{p.get('name') or p.get('username') or 'کاربر'}</a>")
        if mentions:
            bot.send_message(ch_id, " ".join(mentions), reply_to_message_id=sent.message_id)
        bot.answer_callback_query(call.id, "لابی تست ارسال شد")
        return

    # آمار
    if data == "show_stats":
        total_players = sum(len(v) for v in players_dict.values())
        cur_players = len(players_dict.get(chat_id_str, []))
        nazors = nazor_dict.get(chat_id_str, ["___","___"])
        text = f"آمار:\nتعداد کل چت‌ها: {len(players_dict.keys())}\nتعداد بازیکنان این چت: {cur_players}\nناظرها: {nazors[0]} ، {nazors[1]}\nپیام فان اضافه: {len(funny_add_messages)}\nپیام فان حذف: {len(funny_remove_messages)}"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text)
        return

# ------------------ هندلر پیام‌ها (شامل pending actions و دستورات عمومی) ------------------
@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_all_messages(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    chat_id_str = str(chat_id)
    text = (message.text or "").strip()

    # اگر ادمین عملیات pending دارد، آن را پردازش کن
    if user_id in pending_actions:
        action_info = pending_actions[user_id]
        action = action_info.get("action")
        target_chat = action_info.get("chat_id", chat_id_str)

        # اضافه بازیکن از پنل
        if action == "add_player":
            if not text.startswith("/"):
                bot.reply_to(message, "🚨 لطفا اسم را با / قبل ارسال کنید، مثال: /Ali")
                return
            name = text[1:].strip()
            # اگر admin خودش کاربر مد نظر است، ممکنه بخواهیم user_id را هم ذخیره کنیم:
            # اگر پیام ریپلای به یک کاربر باشد، از آن user_id استفاده کن
            user_obj = None
            if message.reply_to_message:
                user_obj = message.reply_to_message.from_user
            res, code = add_name_from_user(name, target_chat, user_obj)
            if code == "illegal":
                bot.reply_to(message, "🚨 نام غیرمجاز!")
            elif res:
                bot.reply_to(message, f"✔ {name} اضافه شد!")
                bot.reply_to(message, random.choice(funny_add_messages))
            else:
                if code == "exists":
                    bot.reply_to(message, "⚠️ این نام قبلاً وجود دارد (آپدیت شد).")
                elif code == "full":
                    bot.reply_to(message, "⚠️ ظرفیت لیست پر است.")
                else:
                    bot.reply_to(message, "⚠️ اضافه نشد.")
            update_main_message(target_chat)
            pending_actions.pop(user_id, None)
            return

        # حذف بازیکن از پنل
        if action == "remove_player":
            if not text.startswith("/"):
                bot.reply_to(message, "🚨 لطفا اسم یا یوزرنیم را با / قبل ارسال کنید، مثال: /Ali یا /@ali")
                return
            name = text[1:].strip()
            ok = remove_player(target_chat, name)
            if ok:
                bot.reply_to(message, f"❌ {name} حذف شد.")
                bot.reply_to(message, random.choice(funny_remove_messages))
            else:
                bot.reply_to(message, "⚠️ آن نام در لیست نبود.")
            update_main_message(target_chat)
            pending_actions.pop(user_id, None)
            return

        # ویرایش انتخابی بازیکن: ابتدا مشخص کن کدام بازیکن
        if action == "edit_player_select":
            if not text.startswith("/"):
                bot.reply_to(message, "🚨 لطفا نام یا یوزرنیم را با / قبل ارسال کنید، مثال: /Ali")
                return
            name = text[1:].strip()
            idx = find_player_index_by_name_or_username_or_id(target_chat, name)
            if idx is None:
                bot.reply_to(message, "⚠️ بازیکن یافت نشد.")
                pending_actions.pop(user_id, None)
                return
            # درخواست نام جدید
            pending_actions[user_id] = {"action": "edit_player_input", "chat_id": target_chat, "player_index": idx}
            bot.reply_to(message, "لطفا نام جدید را ارسال کنید (بدون /).")
            return

        if action == "edit_player_input":
            idx = action_info.get("player_index")
            new_name = text.strip()
            if not new_name:
                bot.reply_to(message, "⚠️ نام خالی است.")
                pending_actions.pop(user_id, None)
                return
            with lock:
                players_dict[target_chat][idx]["name"] = new_name
                save_data()
            bot.reply_to(message, "✅ نام بازیکن ویرایش شد.")
            update_main_message(target_chat)
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

        # ویرایش ناظرها
        if action in ("edit_nazor_1", "edit_nazor_2"):
            nm = text.strip()
            if not nm:
                bot.reply_to(message, "⚠️ نام خالی است.")
                pending_actions.pop(user_id, None)
                return
            if target_chat not in nazor_dict:
                nazor_dict[target_chat] = ["___", "___"]
            if action == "edit_nazor_1":
                nazor_dict[target_chat][0] = nm
            else:
                nazor_dict[target_chat][1] = nm
            save_data()
            bot.reply_to(message, f"👁‍🗨 ناظر ثبت شد: {nm}")
            update_main_message(target_chat)
            pending_actions.pop(user_id, None)
            return

        # ویرایش متن لابی
        if action == "edit_lobby_text":
            new_text = text.strip()
            if not new_text:
                bot.reply_to(message, "⚠️ متن خالی است.")
                pending_actions.pop(user_id, None)
                return
            global lobby_text
            lobby_text = new_text
            save_data()
            bot.reply_to(message, "✅ متن لابی ذخیره شد.")
            pending_actions.pop(user_id, None)
            return

    # اگر پیام ریپلای روی پیام لیست بود و کاربر خواست خودش رو اضافه یا حذف کنه یا ناظر بزنه
    # فرمان‌های عمومی: /ناظر 1 name , /نام , /حذف , /پیشبینی
    if not text.startswith("/"):
        bot.reply_to(message, "🚨 فرمان نامعتبره! لطفا قبل از ارسال / بگذارید")
        return

    cmd = text[1:].strip()
    if not cmd:
        bot.reply_to(message, "🚨 فرمان نامعتبره! لطفا بعد از / اسم یا دستور وارد کنید")
        return

    # ثبت ناظر
    if cmd.startswith("ناظر"):
        parts = cmd.split()
        if len(parts) >= 3:
            nazor_type = parts[1]
            nazor_name = " ".join(parts[2:]).strip()
            if chat_id_str not in nazor_dict:
                nazor_dict[chat_id_str] = ["___", "___"]
            if nazor_type in ["1","یک","۱"]:
                nazor_dict[chat_id_str][0] = nazor_name
            elif nazor_type in ["2","دو","۲"]:
                nazor_dict[chat_id_str][1] = nazor_name
            save_data()
            bot.reply_to(message, f"👁‍🗨 ناظر ثبت شد: {nazor_name}")
            update_main_message(chat_id_str)
        else:
            bot.reply_to(message, "⚠️ فرمت درست: /ناظر 1 Ali")
        return

    # پیش‌بینی نقش
    if cmd.lower() in ["پیشبینی", "پیشبینی نقش"]:
        bot.reply_to(message, generate_role_prediction_str(chat_id_str))
        return

    # ریست (فقط ادمین یا ادمین گروه)
    if cmd.lower() == "ریست":
        try:
            admins = bot.get_chat_administrators(chat_id)
            if message.from_user.id in [a.user.id for a in admins] or message.from_user.id in ADMIN_IDS:
                reset_list(chat_id_str)
                bot.reply_to(message, "♻️ لیست ریست شد.")
            else:
                bot.reply_to(message, "❌ فقط ادمین می‌تواند ریست کند.")
        except Exception:
            bot.reply_to(message, "❌ خطا در بررسی ادمین‌ها.")
        return

    # حذف: /حذف یا /حذف Ali  یا ریپلای روی پیام کاربر و ارسال /حذف
    if cmd.lower().startswith("حذف"):
        parts = cmd.split(maxsplit=1)
        # حالت ریپلای: حذف کاربر ریپلای‌شده
        if message.reply_to_message:
            target_user = message.reply_to_message.from_user
            if target_user:
                ok = remove_player(chat_id_str, target_user.id, by_user_id=target_user.id)
                if ok:
                    bot.reply_to(message, f"❌ بازیکن حذف شد: {target_user.username or target_user.first_name}")
                    bot.reply_to(message, random.choice(funny_remove_messages))
                else:
                    bot.reply_to(message, "⚠️ آن کاربر در لیست نبود.")
                update_main_message(chat_id_str)
                return
        # حالت /حذف Ali
        if len(parts) == 2:
            target = parts[1].strip()
            ok = remove_player(chat_id_str, target)
            if ok:
                bot.reply_to(message, f"❌ {target} حذف شد.")
                bot.reply_to(message, random.choice(funny_remove_messages))
            else:
                bot.reply_to(message, "⚠️ آن نام در لیست نبود.")
            update_main_message(chat_id_str)
            return
        # حالت /حذف بدون آرگومان -> حذف خود کاربر
        # حذف بر اساس user_id یا username یا name
        requester_uname = message.from_user.username
        requester_id = message.from_user.id
        ok = remove_player(chat_id_str, requester_id, by_user_id=requester_id)
        if ok:
            bot.reply_to(message, "❌ شما از لیست حذف شدید.")
            bot.reply_to(message, random.choice(funny_remove_messages))
        else:
            # تلاش بر اساس یوزرنیم
            if requester_uname:
                ok2 = remove_player(chat_id_str, requester_uname)
                if ok2:
                    bot.reply_to(message, "❌ شما از لیست حذف شدید.")
                    bot.reply_to(message, random.choice(funny_remove_messages))
                    update_main_message(chat_id_str)
                    return
            bot.reply_to(message, "⚠️ شما در لیست نبودید.")
        update_main_message(chat_id_str)
        return
