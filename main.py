import os
import sqlite3
import urllib.request
import urllib.parse
import json
import time
import re
from threading import Thread
from flask import Flask

BOT_TOKEN = "8882134412:AAHCFAVuRk6h0-oyafS0B_bgOWSln6VqkQs"
ADMIN_ID = 7699501193
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

app = Flask(__name__)

@app.route('/')
def home():
    return "Submit Pro Bot 100% Active & Fixed!"

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# Master Database Setup
def init_db():
    conn = sqlite3.connect("submit_pro.db")
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        balance REAL DEFAULT 0.0,
                        referrals INTEGER DEFAULT 0,
                        referred_by INTEGER,
                        has_worked INTEGER DEFAULT 0
                    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS review_comments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        comment_text TEXT UNIQUE
                    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS support_messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        message TEXT,
                        status TEXT DEFAULT 'OPEN'
                    )''')

    default_settings = {
        'channels': '@freeearningksteam,@freeearningsupport2',
        'ref_rate': '5.0',
        'gmail_pass': 'SetPass123',
        'gmail_price': '10.0',
        'gmail_status': 'ON',
        'min_withdraw': '50.0',
        'bkash_status': 'ON',
        'nagad_status': 'ON',
        'video_gmail': 'https://youtube.com',
        'video_review': 'https://youtube.com',
        'review_link': 'https://maps.google.com',
        'review_rate': '15.0',
        'review_limit': '10',
        'review_count': '0',
        'review_status': 'ON'
    }
    
    for key, val in default_settings.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, val))
        
    conn.commit()
    conn.close()

init_db()

def ensure_user(user_id):
    try:
        conn = sqlite3.connect("submit_pro.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error ensure_user: {e}")

def get_setting(key):
    try:
        conn = sqlite3.connect("submit_pro.db")
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
        res = cursor.fetchone()
        conn.close()
        return res[0] if res else ""
    except Exception:
        return ""

def set_setting(key, val):
    try:
        conn = sqlite3.connect("submit_pro.db")
        cursor = conn.cursor()
        cursor.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, val))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error set_setting: {e}")

def send_message(chat_id, text, reply_markup=None):
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup)
    try:
        req = urllib.request.Request(API_URL + "sendMessage", json.dumps(data).encode('utf-8'), {'Content-Type': 'application/json'})
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"Error sending msg: {e}")

def send_photo(chat_id, photo_file_id, caption, reply_markup=None):
    data = {'chat_id': chat_id, 'photo': photo_file_id, 'caption': caption, 'parse_mode': 'Markdown'}
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup)
    try:
        req = urllib.request.Request(API_URL + "sendPhoto", json.dumps(data).encode('utf-8'), {'Content-Type': 'application/json'})
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"Error sending photo: {e}")

def check_joined(user_id):
    channels = get_setting('channels').split(',')
    if not channels or channels == ['']:
        return True
    
    for ch in channels:
        ch = ch.strip()
        if not ch:
            continue
        try:
            url = f"{API_URL}getChatMember?chat_id={ch}&user_id={user_id}"
            req = urllib.request.urlopen(url)
            res = json.loads(req.read().decode('utf-8'))
            status = res.get("result", {}).get("status", "")
            if status not in ["member", "administrator", "creator"]:
                return False
        except Exception:
            return False
    return True

def force_join_markup():
    channels = get_setting('channels').split(',')
    keyboard = []
    for ch in channels:
        ch = ch.strip()
        if ch:
            clean_username = ch.replace("@", "")
            keyboard.append([{'text': f'📢 {ch}', 'url': f'https://t.me/{clean_username}'}])
    keyboard.append([{'text': '✅ Verify (ভেরিফাই)', 'callback_data': 'verify_membership'}])
    return {'inline_keyboard': keyboard}

def main_keyboard(user_id):
    kb = {
        'keyboard': [
            [{'text': '💼 Gmail Sell'}, {'text': '⭐ Google Review'}],
            [{'text': '👤 My Account'}, {'text': '💳 Withdraw'}],
            [{'text': '🎥 কাজের ভিডিও'}, {'text': '🎧 Support System'}]
        ],
        'resize_keyboard': True
    }
    if user_id == ADMIN_ID:
        kb['keyboard'].append([{'text': '⚙️ Admin Panel'}])
    return kb

user_states = {}

def process_referral(target_user):
    conn = sqlite3.connect("submit_pro.db")
    cursor = conn.cursor()
    cursor.execute("SELECT referred_by, has_worked FROM users WHERE user_id=?", (target_user,))
    row = cursor.fetchone()
    
    if row and row[0] and row[1] == 0:
        ref_by = row[0]
        ref_rate = float(get_setting('ref_rate'))
        cursor.execute("UPDATE users SET balance = balance + ?, referrals = referrals + 1 WHERE user_id=?", (ref_rate, ref_by))
        cursor.execute("UPDATE users SET has_worked = 1 WHERE user_id=?", (target_user,))
        send_message(ref_by, f"🎉 **রেফারেল বোনাস আপডেট!**\n\nআপনার রেফারকৃত সদস্য একটি কাজ সম্পন্ন করায় আপনার অ্যাকাউন্টে **{ref_rate} BDT** যোগ করা হয়েছে।")
    else:
        cursor.execute("UPDATE users SET has_worked = 1 WHERE user_id=?", (target_user,))
        
    conn.commit()
    conn.close()

def get_random_comment():
    conn = sqlite3.connect("submit_pro.db")
    cursor = conn.cursor()
    cursor.execute("SELECT comment_text FROM review_comments ORDER BY RANDOM() LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "Great service and smooth experience!"

def handle_update(update):
    try:
        # Callback Queries
        if "callback_query" in update:
            cb = update["callback_query"]
            cb_data = cb["data"]
            user_id = cb["from"]["id"]
            
            if cb_data == "verify_membership":
                if check_joined(user_id):
                    send_message(user_id, "✅ **ভেরিফিকেশন সফল হয়েছে!**\n\nকাজ শুরু করতে নিচের যেকোনো একটি অপশন নির্বাচন করুন।", main_keyboard(user_id))
                else:
                    send_message(user_id, "❌ **আপনি এখনো সবগুলো চ্যানেলে জয়েন করেননি!**")
                return

            # Admin Category Menus
            if user_id == ADMIN_ID:
                if cb_data == "adm_main_menu":
                    adm_kb = {'inline_keyboard': [
                        [{'text': '📥 Gmail Dashboard', 'callback_data': 'adm_gmail_menu'}],
                        [{'text': '⭐ Google Review Dashboard', 'callback_data': 'adm_review_menu'}],
                        [{'text': '💳 Withdraw Dashboard', 'callback_data': 'adm_withdraw_menu'}],
                        [{'text': '📢 Broadcast (নোটিশ পাঠান)', 'callback_data': 'adm_broadcast'}]
                    ]}
                    send_message(user_id, "⚙️ **উন্নত এডমিন কন্ট্রোল প্যানেল**", adm_kb)
                    return

                if cb_data == "adm_gmail_menu":
                    kb = {'inline_keyboard': [
                        [{'text': '🔄 Toggle Status (ON/OFF)', 'callback_data': 'toggle_gmail_status'}],
                        [{'text': '🔙 Back to Main Admin', 'callback_data': 'adm_main_menu'}]
                    ]}
                    st = get_setting('gmail_status')
                    send_message(user_id, f"📥 **Gmail Management Dashboard**\n\nবর্তমান স্ট্যাটাস: **{st}**\n\nপাসওয়ার্ড পরিবর্তন: `/set_pass newpass`\nরেট পরিবর্তন: `/set_gprice 10`", kb)
                    return

                if cb_data == "toggle_gmail_status":
                    cur = get_setting('gmail_status')
                    new_st = "OFF" if cur == "ON" else "ON"
                    set_setting('gmail_status', new_st)
                    send_message(user_id, f"✅ Gmail কাজ **{new_st}** করা হয়েছে।")
                    return

                if cb_data == "adm_review_menu":
                    kb = {'inline_keyboard': [
                        [{'text': '🔄 Toggle Review (ON/OFF)', 'callback_data': 'toggle_review_status'}],
                        [{'text': '➕ Add Comments Pool', 'callback_data': 'adm_add_comments'}],
                        [{'text': '🔙 Back to Main Admin', 'callback_data': 'adm_main_menu'}]
                    ]}
                    st = get_setting('review_status')
                    send_message(user_id, f"⭐ **Google Review Management**\n\nবর্তমান স্ট্যাটাস: **{st}**\n\nলিংক পরিবর্তন: `/set_rlink link`\nরেট পরিবর্তন: `/set_rprice 15`\nলিমিট সেট: `/set_rlimit 10`", kb)
                    return

                if cb_data == "toggle_review_status":
                    cur = get_setting('review_status')
                    new_st = "OFF" if cur == "ON" else "ON"
                    set_setting('review_status', new_st)
                    send_message(user_id, f"✅ গুগল রিভিউ **{new_st}** করা হয়েছে।")
                    return

                if cb_data == "adm_add_comments":
                    user_states[user_id] = "WAITING_COMMENT_POOL"
                    send_message(user_id, "📝 **কমেন্ট পুল যুক্ত করুন:**\n\nএকসাথে একাধিক কমেন্ট পাঠাতে পারেন (প্রতিটি লাইন দিয়ে আলাদা করুন):")
                    return

                if cb_data == "adm_withdraw_menu":
                    bkash = get_setting('bkash_status')
                    nagad = get_setting('nagad_status')
                    kb = {'inline_keyboard': [
                        [{'text': f'Bkash ({bkash})', 'callback_data': 'toggle_bkash'},
                         {'text': f'Nagad ({nagad})', 'callback_data': 'toggle_nagad'}],
                        [{'text': '🔙 Back to Main Admin', 'callback_data': 'adm_main_menu'}]
                    ]}
                    send_message(user_id, f"💳 **Withdraw Management**\n\nসর্বনিম্ন উইথড্র: `{get_setting('min_withdraw')}` BDT\nপরিবর্তন করতে টাইপ করুন: `/set_minwd 50`", kb)
                    return

                if cb_data == "toggle_bkash":
                    cur = get_setting('bkash_status')
                    set_setting('bkash_status', "OFF" if cur == "ON" else "ON")
                    send_message(user_id, "✅ বিকাশ পেমেন্ট স্ট্যাটাস আপডেট হয়েছে।")
                    return

                if cb_data == "toggle_nagad":
                    cur = get_setting('nagad_status')
                    set_setting('nagad_status', "OFF" if cur == "ON" else "ON")
                    send_message(user_id, "✅ নগদ পেমেন্ট স্ট্যাটাস আপডেট হয়েছে।")
                    return

                if cb_data == "adm_broadcast":
                    user_states[user_id] = "WAITING_BROADCAST_MSG"
                    send_message(user_id, "📢 **সব ইউজারের কাছে নোটিশ/মেসেজ পাঠান:**\n\nআপনার মেসেজটি নিচে লিখে পাঠান:")
                    return

            # User Withdraw Method Trigger
            if cb_data.startswith("wd_method_"):
                method = cb_data.split("_")[2]
                st = get_setting(f"{method}_status")
                if st == "OFF":
                    send_message(user_id, f"❌ দুঃখিত! বর্তমানে **{method.upper()}** উইথড্র বন্ধ আছে। অন্য মেথড চেষ্টা করুন।")
                    return
                user_states[user_id] = f"WAITING_WD_DETAILS_{method}"
                send_message(user_id, f"📲 **{method.upper()} উইথড্র**\n\nআপনার **{method.upper()} নম্বর** এবং **টাকার পরিমাণ** একসাথে লিখে পাঠান।\n\n📌 *উদাহরণ:* `01700000000 50`")
                return

            # Approvals Fix
            if cb_data.startswith("app_gmail_"):
                target_user = int(cb_data.split("_")[2])
                ensure_user(target_user)
                g_price = float(get_setting('gmail_price'))
                
                conn = sqlite3.connect("submit_pro.db")
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (g_price, target_user))
                conn.commit()
                conn.close()
                
                process_referral(target_user)
                send_message(target_user, f"✅ **অভিনন্দন!**\nআপনার Gmail একসেপ্ট করা হয়েছে। **{g_price} BDT** ব্যালেন্সে যোগ হয়েছে।")
                send_message(ADMIN_ID, f"✅ Gmail এপ্রুভ করা হয়েছে। (User: `{target_user}`)")

            elif cb_data.startswith("rej_gmail_"):
                target_user = int(cb_data.split("_")[2])
                send_message(target_user, "❌ **দুঃখিত!** আপনার জমা দেওয়া জিমেইলটি রিজেক্ট করা হয়েছে।")
                send_message(ADMIN_ID, f"❌ Gmail রিজেক্ট করা হয়েছে। (User: `{target_user}`)")

            elif cb_data.startswith("app_rev_"):
                target_user = int(cb_data.split("_")[2])
                ensure_user(target_user)
                r_price = float(get_setting('review_rate'))
                
                conn = sqlite3.connect("submit_pro.db")
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (r_price, target_user))
                conn.commit()
                conn.close()
                
                cur_cnt = int(get_setting('review_count'))
                set_setting('review_count', str(cur_cnt + 1))
                process_referral(target_user)
                send_message(target_user, f"🎉 **গুগল রিভিউ সফল!**\nআপনার রিভিউ এপ্রুভ করা হয়েছে এবং **{r_price} BDT** যোগ হয়েছে।")
                send_message(ADMIN_ID, f"✅ Google Review এপ্রুভ করা হয়েছে। (User: `{target_user}`)")

            elif cb_data.startswith("rej_rev_"):
                target_user = int(cb_data.split("_")[2])
                send_message(target_user, "❌ **দুঃখিত!** আপনার গুগল রিভিউটি রিজেক্ট করা হয়েছে।")
                send_message(ADMIN_ID, f"❌ Google Review রিজেক্ট করা হয়েছে। (User: `{target_user}`)")

            elif cb_data.startswith("reply_supp_"):
                target_user = int(cb_data.split("_")[2])
                user_states[ADMIN_ID] = f"WAITING_SUPP_REPLY_{target_user}"
                send_message(ADMIN_ID, f"💬 **User `{target_user}` কে রিপ্লাই দিন:**\nনিচে আপনার উত্তরটি লিখে পাঠান।")
            return

        # Message Handling
        if "message" in update:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            user_id = msg["from"]["id"]
            text = msg.get("text", "")

            ensure_user(user_id)

            if text.startswith("/start"):
                user_states[user_id] = None
                args = text.split()
                conn = sqlite3.connect("submit_pro.db")
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
                if not cursor.fetchone():
                    ref_by = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
                    cursor.execute("INSERT INTO users (user_id, referred_by) VALUES (?, ?)", (user_id, ref_by))
                    conn.commit()
                conn.close()
                
                if not check_joined(user_id):
                    send_message(chat_id, "⚠️ **বটটি ব্যবহার করতে আমাদের অফিশিয়াল চ্যানেলগুলোতে জয়েন থাকুন!**", force_join_markup())
                else:
                    send_message(chat_id, "👋 **Submit Pro** বটে আপনাকে স্বাগতম!", main_keyboard(user_id))
                return

            if not check_joined(user_id):
                send_message(chat_id, "⚠️ **কাজ শুরু করতে আগে চ্যানেলগুলোতে জয়েন হয়ে ভেরিফাই করুন!**", force_join_markup())
                return

            # Main Menu Reset
            if text in ["💼 Gmail Sell", "⭐ Google Review", "👤 My Account", "💳 Withdraw", "🎥 কাজের ভিডিও", "🎧 Support System", "⚙️ Admin Panel"]:
                user_states[user_id] = None

            if text == "👤 My Account":
                conn = sqlite3.connect("submit_pro.db")
                cursor = conn.cursor()
                cursor.execute("SELECT balance, referrals FROM users WHERE user_id=?", (user_id,))
                row = cursor.fetchone()
                conn.close()
                bal = row[0] if row else 0.0
                refs = row[1] if row else 0
                
                bot_info = json.loads(urllib.request.urlopen(API_URL + "getMe").read().decode('utf-8'))
                ref_link = f"https://t.me/{bot_info['result']['username']}?start={user_id}"
                
                send_message(chat_id, f"👤 **আপনার প্রোফাইল**\n\n💰 **ব্যালেন্স:** `{bal}` BDT\n👥 **সফল রেফার:** `{refs}` জন\n\n🔗 **রেফার লিংক:**\n`{ref_link}`\n\n📌 **নোটিশ:** রেফারকৃত সদস্য অন্তত ১টি কাজ জমা দিলে বোনাস কাউন্ট হবে।")
                return

            if text == "💼 Gmail Sell":
                if get_setting('gmail_status') == "OFF":
                    send_message(chat_id, "❌ বর্তমানে জিমেইল সেলের কাজ সাময়িকভাবে বন্ধ আছে।")
                    return
                g_pass = get_setting('gmail_pass')
                g_price = get_setting('gmail_price')
                user_states[user_id] = "WAITING_GMAIL"
                send_message(chat_id, f"📧 **Gmail Sell Work**\n\n🔑 **পাসওয়ার্ড:** `{g_pass}`\n💵 **রেট:** {g_price} BDT\n\nআপনার **Gmail** এবং **Password** একসাথে নিচে লিখে পাঠান:\n*উদাহরণ:* `example@gmail.com {g_pass}`")
                return

            if user_states.get(user_id) == "WAITING_GMAIL":
                has_gmail = re.search(r'[a-zA-Z0-9._%+-]+@gmail\.com', text, re.IGNORECASE)
                if not has_gmail:
                    send_message(chat_id, "❌ **ভুল ফরম্যাট!** সঠিকভাবে Gmail এবং Password দিন।")
                    return
                user_states[user_id] = None
                markup = {'inline_keyboard': [[
                    {'text': '✅ Approve', 'callback_data': f'app_gmail_{user_id}'},
                    {'text': '❌ Reject', 'callback_data': f'rej_gmail_{user_id}'}
                ]]}
                send_message(ADMIN_ID, f"📥 **নতুন Gmail জমা এসেছে!**\n\n👤 ID: `{user_id}`\n📝 **তথ্য:**\n{text}", markup)
                send_message(chat_id, "✅ **জিমেইল সফলভাবে জমা হয়েছে!** এডমিন রিভিউ করে বোনাস দেবে।", main_keyboard(user_id))
                return

            if text == "⭐ Google Review":
                if get_setting('review_status') == "OFF":
                    send_message(chat_id, "❌ বর্তমানে গুগল রিভিউর কাজ সাময়িকভাবে বন্ধ রয়েছে।")
                    return
                r_link = get_setting('review_link')
                r_rate = get_setting('review_rate')
                r_limit = int(get_setting('review_limit'))
                r_count = int(get_setting('review_count'))
                
                if r_count >= r_limit:
                    send_message(chat_id, "❌ গুগল রিভিউর দৈনিক লিমিট শেষ হয়ে গেছে!")
                else:
                    user_states[user_id] = "WAITING_REVIEW_NAME"
                    suggested_comment = get_random_comment()
                    send_message(chat_id, f"⭐ **Google Review Work**\n\n🔗 **লিংক:** {r_link}\n💵 **রেট:** {r_rate} BDT\n\n💬 **যে কমেন্টটি লিখবেন (কপি করুন):**\n`{suggested_comment}`\n\n📌 **নিয়ম:** ৫-স্টার দিয়ে মন্তব্য করার পর আপনার **Google Account Name** লিখে নিচে পাঠান:")
                return

            if user_states.get(user_id) == "WAITING_REVIEW_NAME":
                if text:
                    user_states[user_id] = f"WAITING_REVIEW_PHOTO_{text}"
                    send_message(chat_id, f"✅ নাম রেকর্ড করা হয়েছে: **{text}**\n\nএখন রিভিউর একটি **Screenshot** ফটো হিসাবে বানিয়ে পাঠিয়ে দিন।")
                return

            if "photo" in msg and user_states.get(user_id, "").startswith("WAITING_REVIEW_PHOTO_"):
                google_name = user_states[user_id].replace("WAITING_REVIEW_PHOTO_", "")
                photo_id = msg["photo"][-1]["file_id"]
                user_states[user_id] = None
                markup = {'inline_keyboard': [[
                    {'text': '✅ Approve', 'callback_data': f'app_rev_{user_id}'},
                    {'text': '❌ Reject', 'callback_data': f'rej_rev_{user_id}'}
                ]]}
                send_photo(ADMIN_ID, photo_id, f"⭐ **নতুন Google Review!**\n\n👤 ID: `{user_id}`\n📛 গুগল নাম: **{google_name}**", markup)
                send_message(chat_id, "✅ **আপনার গুগল রিভিউ জমা হয়েছে!**", main_keyboard(user_id))
                return

            if text == "💳 Withdraw":
                conn = sqlite3.connect("submit_pro.db")
                cursor = conn.cursor()
                cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
                bal = cursor.fetchone()[0]
                conn.close()
                wd_markup = {'inline_keyboard': [
                    [{'text': 'Bkash (বিকাশ)', 'callback_data': 'wd_method_bkash'},
                     {'text': 'Nagad (নগদ)', 'callback_data': 'wd_method_nagad'}]
                ]}
                send_message(chat_id, f"💰 **ব্যালেন্স:** `{bal}` BDT\nসর্বনিম্ন উইথড্র: `{get_setting('min_withdraw')}` BDT\n\nমেথড সিলেক্ট করুন:", wd_markup)
                return

            state = user_states.get(user_id, "")
            if state.startswith("WAITING_WD_DETAILS_"):
                method = state.replace("WAITING_WD_DETAILS_", "").upper()
                try:
                    parts = text.split()
                    num, amount = parts[0], float(parts[1])
                    min_wd = float(get_setting('min_withdraw'))
                    conn = sqlite3.connect("submit_pro.db")
                    cursor = conn.cursor()
                    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
                    bal = cursor.fetchone()[0]
                    if amount < min_wd:
                        send_message(chat_id, f"❌ সর্বনিম্ন উইথড্র `{min_wd}` BDT।")
                    elif amount > bal:
                        send_message(chat_id, "❌ পর্যাপ্ত ব্যালেন্স নেই।")
                    else:
                        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (amount, user_id))
                        conn.commit()
                        user_states[user_id] = None
                        send_message(ADMIN_ID, f"🚨 **Withdraw Request!**\n\n👤 ID: `{user_id}`\n💳 মেথড: **{method}**\n📱 নম্বর: `{num}`\n💵 পরিমাণ: **{amount} BDT**")
                        send_message(chat_id, f"✅ **{method} উইথড্র রিকোয়েস্ট জমা হয়েছে!**", main_keyboard(user_id))
                    conn.close()
                except Exception:
                    send_message(chat_id, "❌ **ফরম্যাট ভুল!** উদাহরণ: `01700000000 50`")
                return

            if text == "🎧 Support System":
                user_states[user_id] = "WAITING_SUPPORT_MSG"
                send_message(chat_id, "🎧 **Help & Support**\n\nআপনার প্রশ্ন বা সমস্যা বিস্তারিত লিখে পাঠান। এডমিন রিপ্লাই দেবে।")
                return

            if user_states.get(user_id) == "WAITING_SUPPORT_MSG":
                user_states[user_id] = None
                markup = {'inline_keyboard': [[{'text': '💬 Reply User', 'callback_data': f'reply_supp_{user_id}'}]]}
                send_message(ADMIN_ID, f"📩 **নতুন Support Ticket!**\n\n👤 ইউজার ID: `{user_id}`\n💬 **মেসেজ:**\n{text}", markup)
                send_message(chat_id, "✅ **আপনার সাপোর্ট মেসেজ পাঠানো হয়েছে!** এডমিন শীঘ্রই উত্তর দেবে।", main_keyboard(user_id))
                return

            if text == "🎥 কাজের ভিডিও":
                send_message(chat_id, f"🎥 **কাজের ভিডিও গাইড:**\n\n1. জিমেইল কাজ: {get_setting('video_gmail')}\n2. গুগল রিভিউ: {get_setting('video_review')}")
                return

            # Admin Operations
            if text == "⚙️ Admin Panel" and user_id == ADMIN_ID:
                adm_kb = {'inline_keyboard': [
                    [{'text': '📥 Gmail Dashboard', 'callback_data': 'adm_gmail_menu'}],
                    [{'text': '⭐ Google Review Dashboard', 'callback_data': 'adm_review_menu'}],
                    [{'text': '💳 Withdraw Dashboard', 'callback_data': 'adm_withdraw_menu'}],
                    [{'text': '📢 Broadcast (নোটিশ পাঠান)', 'callback_data': 'adm_broadcast'}]
                ]}
                send_message(chat_id, "⚙️ **উন্নত এডমিন কন্ট্রোল প্যানেল**\n\nনিচের ক্যাটাগরিগুলো থেকে বেছে নিন:", adm_kb)
                return

            if user_id == ADMIN_ID:
                if user_states.get(user_id) == "WAITING_COMMENT_POOL":
                    user_states[user_id] = None
                    comments = text.split('\n')
                    conn = sqlite3.connect("submit_pro.db")
                    cursor = conn.cursor()
                    for c in comments:
                        c = c.strip()
                        if c:
                            cursor.execute("INSERT OR IGNORE INTO review_comments (comment_text) VALUES (?)", (c,))
                    conn.commit()
                    conn.close()
                    send_message(ADMIN_ID, "✅ **কমেন্ট পুল সফলভাবে আপডেট করা হয়েছে!**")
                    return

                if user_states.get(user_id) == "WAITING_BROADCAST_MSG":
                    user_states[user_id] = None
                    conn = sqlite3.connect("submit_pro.db")
                    cursor = conn.cursor()
                    cursor.execute("SELECT user_id FROM users")
                    users = cursor.fetchall()
                    conn.close()
                    
                    count = 0
                    for u in users:
                        try:
                            send_message(u[0], f"📢 **অফিশিয়াল নোটিশ**\n\n{text}")
                            count += 1
                            time.sleep(0.05)
                        except Exception:
                            pass
                    send_message(ADMIN_ID, f"✅ **ব্রডকাস্ট সফল!** `{count}` জন ইউজারের কাছে মেসেজ পৌঁছেছে।")
                    return

                state = user_states.get(user_id, "")
                if state.startswith("WAITING_SUPP_REPLY_"):
                    target_u = int(state.replace("WAITING_SUPP_REPLY_", ""))
                    user_states[user_id] = None
                    send_message(target_u, f"🎧 **এডমিন রিপ্লাই:**\n\n{text}")
                    send_message(ADMIN_ID, f"✅ User `{target_u}`-কে উত্তর পাঠানো হয়েছে।")
                    return

                if text.startswith("/set_minwd"):
                    val = text.split(maxsplit=1)[1]
                    set_setting('min_withdraw', val)
                    send_message(chat_id, f"✅ সর্বনিম্ন উইথড্র সেট করা হয়েছে: `{val}` BDT")
                elif text.startswith("/set_pass"):
                    val = text.split(maxsplit=1)[1]
                    set_setting('gmail_pass', val)
                    send_message(chat_id, f"✅ জিমেইল পাসওয়ার্ড পরিবর্তন করা হয়েছে: `{val}`")
                elif text.startswith("/set_gprice"):
                    val = text.split(maxsplit=1)[1]
                    set_setting('gmail_price', val)
                    send_message(chat_id, f"✅ জিমেইল রেট সেট করা হয়েছে: `{val}` BDT")
                elif text.startswith("/set_rlink"):
                    val = text.split(maxsplit=1)[1]
                    set_setting('review_link', val)
                    send_message(chat_id, f"✅ গুগল রিভিউ লিংক সেট করা হয়েছে: `{val}`")
                elif text.startswith("/set_rprice"):
                    val = text.split(maxsplit=1)[1]
                    set_setting('review_rate', val)
                    send_message(chat_id, f"✅ রিভিউ রেট সেট করা হয়েছে: `{val}` BDT")
                elif text.startswith("/set_rlimit"):
                    val = text.split(maxsplit=1)[1]
                    set_setting('review_limit', val)
                    set_setting('review_count', '0')
                    send_message(chat_id, f"✅ রিভিউ লিমিট সেট করা হয়েছে: `{val}` টি।")

    except Exception as e:
        print(f"Error handling update: {e}")

def bot_loop():
    offset = 0
    while True:
        try:
            req = urllib.request.urlopen(f"{API_URL}getUpdates?offset={offset}&timeout=10")
            data = json.loads(req.read().decode('utf-8'))
            for result in data.get("result", []):
                offset = result["update_id"] + 1
                handle_update(result)
        except Exception as e:
            time.sleep(2)

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot_loop()
