import os
import sqlite3
import urllib.request
import urllib.parse
import json
import time
import re
from threading import Thread
from flask import Flask

# Bot Config
BOT_TOKEN = "8882134412:AAHCFAVuRk6h0-oyafS0B_bgOWSln6VqkQs"
ADMIN_ID = 7699501193
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

app = Flask(__name__)

@app.route('/')
def home():
    return "Submit Pro Bot is Running 24/7 Smoothly!"

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# ১. বট আটকে যাওয়া বন্ধ করতে অটো-ওয়েবহুক রিমুভার
def clear_webhook():
    try:
        url = API_URL + "deleteWebhook?drop_pending_updates=True"
        urllib.request.urlopen(url)
        print("Webhook cleared and old message backlog removed!")
    except Exception as e:
        print(f"Error clearing webhook: {e}")

# ২. ডাটাবেজ ফ্রিজিং বন্ধ করতে বিশেষ সেটিংস
def get_db():
    conn = sqlite3.connect("submit_pro.db", timeout=60.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = get_db()
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

    cursor.execute('''CREATE TABLE IF NOT EXISTS logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        type TEXT,
                        details TEXT,
                        status TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )''')

    default_settings = {
        'channels': '@freeearningksteam,@freeearningsupport2',
        'ref_rate': '5.0',
        'gmail_pass': 'SetPass123',
        'gmail_price': '10.0',
        'gmail_status': 'ON',
        'gmail_notice': '📌 প্রতি জিমেইল এর পেমেন্ট ১২-২৪ ঘণ্টার মধ্যে দেওয়া হয়। নিচের পাসওয়ার্ড ব্যবহার করে জিমেইল খুলুন।',
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

def ensure_user(user_id, ref_by=None):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO users (user_id, referred_by) VALUES (?, ?)", (user_id, ref_by))
            if ref_by:
                cursor.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id=?", (ref_by,))
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error ensure_user: {e}")

def get_setting(key):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
        res = cursor.fetchone()
        conn.close()
        return res[0] if res else ""
    except Exception:
        return ""

def set_setting(key, val):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, val))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error set_setting: {e}")

def add_log(user_id, log_type, details, status="PENDING"):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO logs (user_id, type, details, status) VALUES (?, ?, ?, ?)", 
                       (user_id, log_type, details, status))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error add_log: {e}")

def get_user_stats():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM users WHERE has_worked = 1")
    active_workers = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM logs WHERE type='GMAIL'")
    total_gmail_logs = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM logs WHERE type='REVIEW'")
    total_review_logs = cursor.fetchone()[0]
    conn.close()
    
    return (
        f"📊 **বট ব্যবহারকারী ও কাজের পরিসংখ্যান:**\n\n"
        f"👥 **মোট বট স্টার্ট করেছে:** `{total_users}` জন\n"
        f"💼 **মোট কাজ সম্পন্নকারী ইউজার:** `{active_workers}` জন\n\n"
        f"📥 **মোট জিমেইল সাবমিশন:** `{total_gmail_logs}` টি\n"
        f"⭐ **মোট গুগল রিভিউ সাবমিশন:** `{total_review_logs}` টি\n"
    )

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
user_gmail_drafts = {}

# ৩. রেফারেল বোনাসের সঠিক সমাধান (প্রথম কাজ এপ্রুভ হলে বোনাস যাবে)
def process_referral(target_user):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT referred_by, has_worked FROM users WHERE user_id=?", (target_user,))
        row = cursor.fetchone()
        
        if row and row[0] and row[1] == 0:
            ref_by = row[0]
            ref_rate = float(get_setting('ref_rate'))
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (ref_rate, ref_by))
            cursor.execute("UPDATE users SET has_worked = 1 WHERE user_id=?", (target_user,))
            send_message(ref_by, f"🎉 **রেফারেল বোনাস অর্জিত!**\n\nআপনার রেফারকৃত ইউজার কাজ সম্পন্ন করায় আপনার ব্যালেন্সে **{ref_rate} BDT** যোগ হয়েছে।")
        else:
            cursor.execute("UPDATE users SET has_worked = 1 WHERE user_id=?", (target_user,))
            
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error referral: {e}")

def get_random_comment():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT comment_text FROM review_comments ORDER BY RANDOM() LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "Great service and smooth experience!"

def get_history(log_type):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, details, status, timestamp FROM logs WHERE type=? ORDER BY id DESC LIMIT 10", (log_type,))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return f"📂 **{log_type}** এর কোনো রেকর্ড পাওয়া যায়নি।"
    
    text = f"📜 **সর্বশেষ {log_type} হিস্টোরি (Top 10):**\n\n"
    for r in rows:
        text += f"👤 User: `{r[0]}` | Status: **{r[2]}**\n📝 তথ্য:\n{r[1]}\n⏰ সময়: {r[3]}\n-------------------\n"
    return text

def get_admin_menu_markup():
    return {'inline_keyboard': [
        [{'text': '📊 User Statistics', 'callback_data': 'adm_user_stats'}],
        [{'text': '📥 Gmail Store Dashboard', 'callback_data': 'adm_gmail_menu'},
         {'text': '⭐ Review Store Dashboard', 'callback_data': 'adm_review_menu'}],
        [{'text': '💳 Withdraw Dashboard', 'callback_data': 'adm_withdraw_menu'},
         {'text': '📢 Broadcast', 'callback_data': 'adm_broadcast'}]
    ]}

def handle_update(update):
    try:
        if "callback_query" in update:
            cb = update["callback_query"]
            cb_data = cb["data"]
            user_id = cb["from"]["id"]
            
            if cb_data == "verify_membership":
                if check_joined(user_id):
                    send_message(user_id, "✅ **ভেরিফিকেশন সফল হয়েছে!**\n\nকাজ শুরু করতে নিচের অপশন বেছে নিন।", main_keyboard(user_id))
                else:
                    send_message(user_id, "❌ **আপনি এখনো সব চ্যানেলে জয়েন করেননি!**")
                return

            if cb_data == "submit_bulk_gmail":
                draft = user_gmail_drafts.get(user_id, "").strip()
                if not draft:
                    send_message(user_id, "❌ আপনি কোনো জিমেইল লিখেননি! জিমেইল এবং পাসওয়ার্ড লিখে মেসেজ দিন।")
                    return
                
                lines = [l.strip() for l in draft.split('\n') if l.strip()]
                valid_entries = []
                
                for idx, line in enumerate(lines, 1):
                    has_gmail = re.search(r'[a-zA-Z0-9._%+-]+@gmail\.com', line, re.IGNORECASE)
                    if not has_gmail:
                        send_message(user_id, f"❌ **{idx} নম্বর লাইনের ফরম্যাট ভুল!**\n\nঅবশ্যই `@gmail.com` সহ ইমেল ও পাসওয়ার্ড লিখুন।")
                        return
                    valid_entries.append(line)

                user_states[user_id] = None
                user_gmail_drafts[user_id] = ""
                full_submission = "\n".join(valid_entries)
                add_log(user_id, "GMAIL", f"Total: {len(valid_entries)} Pcs\n{full_submission}", "PENDING")
                
                markup = {'inline_keyboard': [[
                    {'text': f'✅ Approve All ({len(valid_entries)} Pcs)', 'callback_data': f'app_gmail_{user_id}_{len(valid_entries)}'},
                    {'text': '❌ Reject All', 'callback_data': f'rej_gmail_{user_id}'}
                ]]}
                
                send_message(ADMIN_ID, f"📥 **নতুন জিমেইল সাবমিশন! ({len(valid_entries)} টি)**\n\n👤 ID: `{user_id}`\n\n📝 **তালিকা:**\n{full_submission}", markup)
                send_message(user_id, f"✅ **মোট {len(valid_entries)} টি জিমেইল সফলভাবে জমা নেওয়া হয়েছে!**", main_keyboard(user_id))
                return

            if user_id == ADMIN_ID:
                if cb_data == "adm_main_menu":
                    send_message(user_id, "⚙️ **এডমিন প্যানেল**", get_admin_menu_markup())
                    return
                if cb_data == "adm_user_stats":
                    send_message(user_id, get_user_stats(), {'inline_keyboard': [[{'text': '🔙 Back', 'callback_data': 'adm_main_menu'}]]})
                    return
                if cb_data == "adm_gmail_menu":
                    kb = {'inline_keyboard': [
                        [{'text': '🔄 Status (ON/OFF)', 'callback_data': 'toggle_gmail_status'}],
                        [{'text': '📜 Gmail History', 'callback_data': 'hist_GMAIL'}],
                        [{'text': '🔙 Back', 'callback_data': 'adm_main_menu'}]
                    ]}
                    send_message(user_id, f"📥 **Gmail Store Management**\n\nস্ট্যাটাস: **{get_setting('gmail_status')}**", kb)
                    return
                if cb_data == "adm_review_menu":
                    kb = {'inline_keyboard': [
                        [{'text': '🔄 Status (ON/OFF)', 'callback_data': 'toggle_review_status'}],
                        [{'text': '➕ Add Comments', 'callback_data': 'adm_add_comments'}],
                        [{'text': '📜 Review History', 'callback_data': 'hist_REVIEW'}],
                        [{'text': '🔙 Back', 'callback_data': 'adm_main_menu'}]
                    ]}
                    send_message(user_id, f"⭐ **Google Review Management**\n\nস্ট্যাটাস: **{get_setting('review_status')}**", kb)
                    return
                if cb_data == "adm_withdraw_menu":
                    kb = {'inline_keyboard': [
                        [{'text': f"Bkash ({get_setting('bkash_status')})", 'callback_data': 'toggle_bkash'},
                         {'text': f"Nagad ({get_setting('nagad_status')})", 'callback_data': 'toggle_nagad'}],
                        [{'text': '📜 Withdraw History', 'callback_data': 'hist_WITHDRAW'}],
                        [{'text': '🔙 Back', 'callback_data': 'adm_main_menu'}]
                    ]}
                    send_message(user_id, f"💳 **Withdraw Store Management**\n\nসর্বনিম্ন উইথড্র: `{get_setting('min_withdraw')}` BDT", kb)
                    return
                if cb_data.startswith("hist_"):
                    send_message(user_id, get_history(cb_data.replace("hist_", "")))
                    return
                if cb_data == "toggle_gmail_status":
                    set_setting('gmail_status', "OFF" if get_setting('gmail_status') == "ON" else "ON")
                    send_message(user_id, "✅ জিমেইল কাজের স্ট্যাটাস আপডেট হয়েছে।")
                    return
                if cb_data == "toggle_review_status":
                    set_setting('review_status', "OFF" if get_setting('review_status') == "ON" else "ON")
                    send_message(user_id, "✅ রিভিউ কাজের স্ট্যাটাস আপডেট হয়েছে।")
                    return
                if cb_data == "toggle_bkash":
                    set_setting('bkash_status', "OFF" if get_setting('bkash_status') == "ON" else "ON")
                    send_message(user_id, "✅ বিকাশ স্ট্যাটাস আপডেট হয়েছে।")
                    return
                if cb_data == "toggle_nagad":
                    set_setting('nagad_status', "OFF" if get_setting('nagad_status') == "ON" else "ON")
                    send_message(user_id, "✅ নগদ স্ট্যাটাস আপডেট হয়েছে।")
                    return
                if cb_data == "adm_add_comments":
                    user_states[user_id] = "WAITING_COMMENT_POOL"
                    send_message(user_id, "📝 **কমেন্ট পুল যুক্ত করুন (প্রতিটি লাইন আলাদা):**")
                    return
                if cb_data == "adm_broadcast":
                    user_states[user_id] = "WAITING_BROADCAST_MSG"
                    send_message(user_id, "📢 **সব ইউজারের জন্য নোটিশ লিখুন:**")
                    return

            if cb_data.startswith("wd_method_"):
                method = cb_data.split("_")[2]
                if get_setting(f"{method}_status") == "OFF":
                    send_message(user_id, f"❌ বর্তমানে **{method.upper()}** উইথড্র বন্ধ আছে।")
                    return
                user_states[user_id] = f"WAITING_WD_DETAILS_{method}"
                send_message(user_id, f"📲 **{method.upper()} উইথড্র**\n\nআপনার **{method.upper()} নম্বর** এবং **টাকার পরিমাণ** স্পেস দিয়ে লিখুন।\n\n📌 *উদাহরণ:* `01700000000 50` ")
                return

            if cb_data.startswith("app_gmail_"):
                parts = cb_data.split("_")
                target_user = int(parts[2])
                qty = int(parts[3]) if len(parts) > 3 else 1
                ensure_user(target_user)
                
                total_reward = float(get_setting('gmail_price')) * qty
                
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (total_reward, target_user))
                conn.commit()
                conn.close()
                
                process_referral(target_user)
                add_log(target_user, "GMAIL", f"+{total_reward} BDT ({qty} Pcs)", "APPROVED")
                send_message(target_user, f"🎉 **{qty} টি জিমেইল এপ্রুভ হয়েছে!** +{total_reward} BDT ব্যালেন্স যোগ করা হয়েছে।")
                send_message(ADMIN_ID, f"✅ User `{target_user}` এর {qty} টি জিমেইল এপ্রুভড।")

            elif cb_data.startswith("rej_gmail_"):
                target_user = int(cb_data.split("_")[2])
                add_log(target_user, "GMAIL", "0 BDT", "REJECTED")
                send_message(target_user, "❌ আপনার জমা দেওয়া জিমেইলগুলো রিজেক্ট করা হয়েছে।")
                send_message(ADMIN_ID, f"❌ Gmail রিজেক্ট করা হয়েছে (User: `{target_user}`)")

            elif cb_data.startswith("app_rev_"):
                target_user = int(cb_data.split("_")[2])
                ensure_user(target_user)
                r_price = float(get_setting('review_rate'))
                
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (r_price, target_user))
                conn.commit()
                conn.close()
                
                set_setting('review_count', str(int(get_setting('review_count')) + 1))
                process_referral(target_user)
                add_log(target_user, "REVIEW", f"+{r_price} BDT", "APPROVED")
                send_message(target_user, f"🎉 **গুগল রিভিউ এপ্রুভ হয়েছে!** +{r_price} BDT যোগ হয়েছে।")
                send_message(ADMIN_ID, f"✅ Review এপ্রুভড (User: `{target_user}`)")

            elif cb_data.startswith("rej_rev_"):
                target_user = int(cb_data.split("_")[2])
                add_log(target_user, "REVIEW", "0 BDT", "REJECTED")
                send_message(target_user, "❌ আপনার গুগল রিভিউটি রিজেক্ট করা হয়েছে।")
                send_message(ADMIN_ID, f"❌ Review রিজেক্ট করা হয়েছে (User: `{target_user}`)")

            elif cb_data.startswith("reply_supp_"):
                user_states[ADMIN_ID] = f"WAITING_SUPP_REPLY_{int(cb_data.split('_')[2])}"
                send_message(ADMIN_ID, "💬 **ইউজারকে পাঠানোর মতো উত্তরটি লিখে পাঠিয়ে দিন:**")
            return

        if "message" in update:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            user_id = msg["from"]["id"]
            text = msg.get("text", "")

            if text.startswith("/start"):
                user_states[user_id] = None
                user_gmail_drafts[user_id] = ""
                args = text.split()
                ref_by = int(args[1]) if len(args) > 1 and args[1].isdigit() and int(args[1]) != user_id else None
                ensure_user(user_id, ref_by)
                
                if not check_joined(user_id):
                    send_message(chat_id, "⚠️ **বট ব্যবহার করতে অফিশিয়াল চ্যানেলগুলোতে জয়েন করুন:**", force_join_markup())
                else:
                    send_message(chat_id, "👋 **Submit Pro** বটে আপনাকে স্বাগতম!", main_keyboard(user_id))
                return

            ensure_user(user_id)

            if not check_joined(user_id):
                send_message(chat_id, "⚠️ **চ্যানেলগুলোতে জয়েন হয়ে ভেরিফাই করুন!**", force_join_markup())
                return

            if text in ["💼 Gmail Sell", "⭐ Google Review", "👤 My Account", "💳 Withdraw", "🎥 কাজের ভিডিও", "🎧 Support System", "⚙️ Admin Panel"]:
                user_states[user_id] = None
                user_gmail_drafts[user_id] = ""

            if text == "💼 Gmail Sell":
                if get_setting('gmail_status') == "OFF":
                    send_message(chat_id, "❌ বর্তমানে জিমেইল সেলের কাজ বন্ধ রয়েছে।")
                    return
                
                user_states[user_id] = "WAITING_BULK_GMAIL"
                user_gmail_drafts[user_id] = ""
                
                demo_text = f"📧 **Gmail Submission Setup**\n\n{get_setting('gmail_notice')}\n\n🔑 **পাসওয়ার্ড কপি করুন (টাচ করুন):**\n`{get_setting('gmail_pass')}`\n💵 **রেট:** {get_setting('gmail_price')} BDT\n\n📌 **কীভাবে জিমেইল জমা দিবেন:**\n`email1@gmail.com {get_setting('gmail_pass')}`\n`email2@gmail.com {get_setting('gmail_pass')}`\n\nযতগুলো ইচ্ছে লিখে পাঠিয়ে **Submit** বাটনে চাপ দিন।"
                send_message(chat_id, demo_text, {'inline_keyboard': [[{'text': '📥 Submit All Gmails', 'callback_data': 'submit_bulk_gmail'}]]})
                return

            if user_states.get(user_id) == "WAITING_BULK_GMAIL":
                updated_draft = (user_gmail_drafts.get(user_id, "") + "\n" + text).strip()
                user_gmail_drafts[user_id] = updated_draft
                
                draft_msg = "📝 **আপনার জিমেইল লিস্ট তৈরি হচ্ছে...**\n\nআপনার লেখাটি নিচে যুক্ত হয়েছে। আরও দিতে মেসেজ করুন বা জমা দিতে **Submit** বাটনে চাপ দিন:\n\n```\n" + updated_draft + "\n```"
                send_message(chat_id, draft_msg, {'inline_keyboard': [[{'text': '📥 Submit All Gmails', 'callback_data': 'submit_bulk_gmail'}]]})
                return

            if user_states.get(user_id) == "WAITING_SUPPORT_MSG":
                user_states[user_id] = None
                send_message(ADMIN_ID, f"🎧 **নতুন Support Message!**\n\n👤 ID: `{user_id}`\n💬 {text}", {'inline_keyboard': [[{'text': '💬 Reply User', 'callback_data': f'reply_supp_{user_id}'}]]})
                send_message(chat_id, "✅ **আপনার সাপোর্ট মেসেজ পাঠানো হয়েছে!**", main_keyboard(user_id))
                return

            if text == "🎧 Support System":
                user_states[user_id] = "WAITING_SUPPORT_MSG"
                send_message(chat_id, "🎧 **Help & Support**\n\nআপনার সমস্যাটি নিচে লিখে আমাদের পাঠান:")
                return

            if text == "👤 My Account":
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("SELECT balance, referrals FROM users WHERE user_id=?", (user_id,))
                row = cursor.fetchone()
                conn.close()
                
                bot_info = json.loads(urllib.request.urlopen(API_URL + "getMe").read().decode('utf-8'))
                ref_link = f"https://t.me/{bot_info['result']['username']}?start={user_id}"
                send_message(chat_id, f"👤 **আপনার প্রোফাইল**\n\n💰 **ব্যালেন্স:** `{row[0] if row else 0.0}` BDT\n👥 **মোট রেফার:** `{row[1] if row else 0}` জন\n\n🔗 **রেফার লিংক:**\n`{ref_link}`")
                return

            if text == "⭐ Google Review":
                if get_setting('review_status') == "OFF":
                    send_message(chat_id, "❌ বর্তমানে গুগল রিভিউর কাজ বন্ধ রয়েছে।")
                    return
                if int(get_setting('review_count')) >= int(get_setting('review_limit')):
                    send_message(chat_id, "❌ গুগল রিভিউর দৈনিক লিমিট শেষ হয়ে গেছে!")
                else:
                    user_states[user_id] = "WAITING_REVIEW_NAME"
                    send_message(chat_id, f"⭐ **Google Review Work**\n\n🔗 **লিংক:** {get_setting('review_link')}\n💵 **রেট:** {get_setting('review_rate')} BDT\n\n💬 **কমেন্ট কপি করুন:**\n`{get_random_comment()}`\n\nআপনার **Google Account Name** লিখে পাঠান:")
                return

            if user_states.get(user_id) == "WAITING_REVIEW_NAME":
                if text:
                    user_states[user_id] = f"WAITING_REVIEW_PHOTO_{text}"
                    send_message(chat_id, f"✅ নাম রেকর্ড করা হয়েছে: **{text}**\n\nএখন রিভিউর একটি **Screenshot** ফটো হিসাবে পাঠান।")
                return

            if "photo" in msg and user_states.get(user_id, "").startswith("WAITING_REVIEW_PHOTO_"):
                google_name = user_states[user_id].replace("WAITING_REVIEW_PHOTO_", "")
                photo_id = msg["photo"][-1]["file_id"]
                user_states[user_id] = None
                add_log(user_id, "REVIEW", f"Name: {google_name}", "PENDING")
                send_photo(ADMIN_ID, photo_id, f"⭐ **নতুন Google Review!**\n\n👤 ID: `{user_id}`\n📛 গুগল নাম: **{google_name}**", {'inline_keyboard': [[
                    {'text': '✅ Approve', 'callback_data': f'app_rev_{user_id}'},
                    {'text': '❌ Reject', 'callback_data': f'rej_rev_{user_id}'}
                ]]})
                send_message(chat_id, "✅ **আপনার রিভিউ জমা নেওয়া হয়েছে!**", main_keyboard(user_id))
                return

            if text == "💳 Withdraw":
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
                bal = cursor.fetchone()[0]
                conn.close()
                send_message(chat_id, f"💰 **ব্যালেন্স:** `{bal}` BDT\nসর্বনিম্ন উইথড্র: `{get_setting('min_withdraw')}` BDT\n\nমেথড বেছে নিন:", {'inline_keyboard': [
                    [{'text': 'Bkash (বিকাশ)', 'callback_data': 'wd_method_bkash'},
                     {'text': 'Nagad (নগদ)', 'callback_data': 'wd_method_nagad'}]
                ]})
                return

            state = user_states.get(user_id, "")
            if state.startswith("WAITING_WD_DETAILS_"):
                method = state.replace("WAITING_WD_DETAILS_", "").upper()
                try:
                    parts = text.split()
                    num, amount = parts[0], float(parts[1])
                    min_wd = float(get_setting('min_withdraw'))
                    conn = get_db()
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
                        add_log(user_id, "WITHDRAW", f"{method}: {num} - {amount} BDT", "PENDING")
                        send_message(ADMIN_ID, f"🚨 **Withdraw Request!**\n\n👤 ID: `{user_id}`\n💳 মেথড: **{method}**\n📱 নম্বর: `{num}`\n💵 পরিমাণ: **{amount} BDT**")
                        send_message(chat_id, f"✅ **{method} উইথড্র জমা হয়েছে!**", main_keyboard(user_id))
                    conn.close()
                except Exception:
                    send_message(chat_id, "❌ **ফরম্যাট ভুল!** উদাহরণ: `01700000000 50`")
                return

            if text == "🎥 কাজের ভিডিও":
                send_message(chat_id, f"🎥 **কাজের ভিডিও গাইড:**\n\n1. জিমেইল কাজ: {get_setting('video_gmail')}\n2. গুগল রিভিউ: {get_setting('video_review')}")
                return

            if text == "⚙️ Admin Panel" and user_id == ADMIN_ID:
                send_message(chat_id, "⚙️ **এডমিন কন্ট্রোল ড্যাশবোর্ড**", get_admin_menu_markup())
                return

            if user_id == ADMIN_ID:
                if user_states.get(user_id) == "WAITING_COMMENT_POOL":
                    user_states[user_id] = None
                    conn = get_db()
                    cursor = conn.cursor()
                    for c in text.split('\n'):
                        c = c.strip()
                        if c:
                            cursor.execute("INSERT OR IGNORE INTO review_comments (comment_text) VALUES (?)", (c,))
                    conn.commit()
                    conn.close()
                    send_message(ADMIN_ID, "✅ **কমেন্ট পুল যুক্ত করা হয়েছে!**")
                    return

                if user_states.get(user_id) == "WAITING_BROADCAST_MSG":
                    user_states[user_id] = None
                    conn = get_db()
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
                    send_message(ADMIN_ID, f"✅ **ব্রডকাস্ট সম্পন্ন!** `{count}` জন ইউজারের কাছে পৌঁছেছে।")
                    return

                state = user_states.get(user_id, "")
                if state.startswith("WAITING_SUPP_REPLY_"):
                    target_u = int(state.replace("WAITING_SUPP_REPLY_", ""))
                    user_states[user_id] = None
                    send_message(target_u, f"🎧 **এডমিন রিপ্লাই:**\n\n{text}")
                    send_message(ADMIN_ID, f"✅ User `{target_u}`-কে রিপ্লাই পাঠানো হয়েছে।")
                    return

    except Exception as e:
        print(f"Error handling update: {e}")

# ৪. বট অটো-রিকানেক্ট ও লং-পোলিং সুরক্ষা
def bot_loop():
    clear_webhook()
    offset = 0
    while True:
        try:
            req = urllib.request.Request(f"{API_URL}getUpdates?offset={offset}&timeout=10")
            data = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
            for result in data.get("result", []):
                offset = result["update_id"] + 1
                handle_update(result)
        except Exception as e:
            time.sleep(2)

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot_loop()
