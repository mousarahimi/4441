import telebot
from threading import Lock
import json, os, random
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz

bot = telebot.TeleBot('7998730211:AAFIyWka_cwKfVW_w0xtqrZmrKk3NicxQCk',parse_mode='html')


DATA_FILE = "players_data.json"
players_dict = {}
main_message_dict = {}
nazor_dict = {}
lock = Lock()

funny_add_messages = ["😎 اسم تو اضافه شد!", "😂 هیجان‌انگیز شد!", "🤣 چه بازیکن شجاعی!"]
funny_remove_messages = ["😅 خداحافظ!", "😂 اسم شما حذف شد!", "🤣 حذف شدی!"]

roles = ["شهروندساده", "شهروند ساده", "رییس مافیا", "شیاد", "ناتو", "رویین تن", "کاراگاه", "دکتر", "محقق", "بازپرس"]
illegal_names = ["مستانه", "مثتانه", "مصتانه"]

# ------------------ لیست آی‌دی اعضا برای تگ ------------------
members_ids_list = [
    "davoodsaberii","Mammaddasht","Hadisnorozi","AMIRABBAS6857","Constantine2607",
    "Flower505","Farjadparsa222","Elinaz78","Tbsoms8119","shuhrukhind",
    "MRRrahimi","Parsq","Tthe_void","ThanoS","Zaki99841","navidhmi",
    "M.A.B","Feri00800","NaziTala80","mohammadkhz1380","iDalef","Frzam1234",
    "Matador7i","Sevenfournine","Xmsadeghhp77X","arka12105","MoonlightM8",
    "Zahra75a","نـآزیـ🌼","HosseinMO","tf56vrji","tanhavash_007","Nima",
    "alik9066","Miracle11","Blackboy19980","Azad_0017","amirhtpr",
    "lonelyasfck","Ninish8888","𝐴𝑀𝐼𝑅𝐴𝐿𝐼᭄","amnazm","Shayadazavaleshtebah_bod",
    "Ravashzahra","Sinabehroozian","Rayansixpath"
]

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

# ------------------ تولید لیست پویا ------------------
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
        prefix = style['prefix1'] if i%2==1 else style['prefix2']
        name = players[i-1] if i-1 < len(players) else "___"
        body += f"{prefix} <b>{i}</b>- {name}\n"
    footer = "〰〰〰\n✨ فعال باشید!"
    return header + body + footer

# ------------------ اضافه/حذف ------------------
def add_names(text, chat_id):
    names = text.split()
    added = []
    with lock:
        for name in names:
            if name not in players_dict.get(chat_id,[]) and len(players_dict.get(chat_id,[]))<16:
                players_dict[chat_id].append(name)
                added.append(name)
        save_data()
    return added

def remove_name(name, chat_id):
    with lock:
        if name in players_dict.get(chat_id,[]):
            players_dict[chat_id].remove(name)
            save_data()
            return True
    return False

def reset_list(chat_id):
    with lock:
        players_dict[chat_id]=[]
        nazor_dict[chat_id]=["___","___"]
        save_data()
        if chat_id in main_message_dict:
            try:
                bot.edit_message_text(generate_list(chat_id), chat_id, main_message_dict[chat_id])
            except: pass

# ------------------ پیش‌بینی نقش‌ها ------------------
def generate_role_prediction(chat_id):
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

# ------------------ ارسال لیست ------------------
@bot.message_handler(commands=['start'])
def start(message):
    chat_id=str(message.chat.id)
    with lock:
        if chat_id not in players_dict: players_dict[chat_id]=[]
        if chat_id not in nazor_dict: nazor_dict[chat_id]=["___","___"]
        sent=bot.send_message(chat_id, generate_list(chat_id))
        main_message_dict[chat_id]=sent.message_id
        try: bot.pin_chat_message(chat_id,sent.message_id,disable_notification=True)
        except: pass
        bot.send_message(chat_id,"✔ لیست ارسال و پین شد.")
        save_data()

# ------------------ ارسال خودکار لیست با کلیدواژه ------------------
@bot.message_handler(func=lambda m: any(kw in m.text.lower() for kw in ["لیست", "لیست بفرست"]))
def send_current_list(message):
    chat_id = str(message.chat.id)
    if chat_id not in players_dict: players_dict[chat_id] = []
    if chat_id not in nazor_dict: nazor_dict[chat_id] = ["___","___"]
    sent = bot.send_message(chat_id, generate_list(chat_id))
    main_message_dict[chat_id] = sent.message_id
    try:
        bot.pin_chat_message(chat_id, sent.message_id, disable_notification=True)
    except:
        pass

# ------------------ هندلر واحد ریپلای‌ها و لابی ساعت ------------------
@bot.message_handler(func=lambda m: True)
def reply_handler(message):
    chat_id=str(message.chat.id)
    if chat_id not in main_message_dict: return
    text=message.text.strip()
    user_name=message.from_user.username or message.from_user.first_name

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

    # ناظر
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
        added=add_names(text,chat_id)
        if added: bot.reply_to(message,"😂 الی نمک نشناس است!")
        bot.edit_message_text(generate_list(chat_id),chat_id,main_message_dict[chat_id])
        return

    # پیش‌بینی نقش‌ها
    if text.lower() in ["پیشبینی","پیشبینی نقش"]:
        bot.reply_to(message, generate_role_prediction(chat_id))
        return

    # ریست
    if text=="ریست":
        try:
            admins = bot.get_chat_administrators(message.chat.id)
            if message.from_user.id in [a.user.id for a in admins]:
                reset_list(chat_id)
                bot.reply_to(message,"♻️ لیست ریست شد.")
            else: bot.reply_to(message,"❌ فقط ادمین")
        except: pass
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

    # اضافه کردن اسامی
    added=add_names(text,chat_id)
    if added:
        bot.reply_to(message,f"✔ اضافه شدند: {', '.join(added)}")
        bot.reply_to(message, random.choice(funny_add_messages))
    else:
        bot.reply_to(message,"⚠️ اسمی اضافه نشد")
    bot.edit_message_text(generate_list(chat_id),chat_id,main_message_dict[chat_id])

# ------------------ زمان‌بندی ------------------
def schedule_jobs():
    tz=pytz.timezone("Asia/Tehran")
    scheduler = BackgroundScheduler(timezone=tz)
    scheduler.add_job(lambda:[reset_list(cid) for cid in players_dict.keys()], 'cron', hour=22, minute=0)
    def send_reminder():
        for cid in players_dict.keys():
            try: bot.send_message(cid,"⏰ بازی امشب ساعت 22 شروع می‌شود!")
            except: pass
    scheduler.add_job(send_reminder,'cron',hour=20,minute=30)
    scheduler.start()

# ------------------ شروع ربات ------------------
load_data()
schedule_jobs()
bot.polling(none_stop=True)
