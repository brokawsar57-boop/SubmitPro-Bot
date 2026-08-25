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
    return "Submit Pro Bot - Final Stable Version Active!"

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def get_db():
    conn = sqlite3.connect("submit_pro.db", timeout=30.0)
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
    
    # মোট বট স্টার্টকারী ইউজার
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    # যারা কাজ করেছে (has_worked = 1 অথবা logs এ রেকর্ড আছে)
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM users WHERE has_worked = 1")
    active_workers = cursor.fetchone()[0]
    
    # মোট জিমেইল কাজ জমা পড়ার সংখ্যা
    cursor.execute("SELECT COUNT(*) FROM logs WHERE type='GMAIL'")
    total_gmail_logs = cursor.fetchone()[0]
    
    # মোট রিভিউ কাজের সংখ্যা
    cursor.execute("SELECT COUNT(*) FROM logs WHERE type='REVIEW'")
    total_review_logs = cursor.fetchone()[0]
    
    conn.close()
    
    stats_text = (
        f"📊 **বট ব্যবহারকারী ও কাজের পরিসংখ্যান:**\n\n"
        f"👥 **মোট বট স্টার্ট করেছে:** `{total_users}` জন\n"
        f"💼 **মোট কাজ সম্পন্নকারী ইউজার:** `{active_workers}` জন\n\n"
        f"📥 **মোট জিমেইল সাবমিশন:** `{total_gmail_logs}` টি\n"
        f"⭐ **মোট গুগল রিভিউ সাবমিশন:** `{total_review_logs}` টি\n"
    )
    return stats_text

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

def process_referral(target_user):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT referred_by, has_worked FROM users WHERE user_id=?", (target_user,))
    row = cursor.fetchone()
    
    if row and row[0] and row[1] == 0:
        ref_by = row[0]
        ref_rate = float(get_setting('ref_rate'))
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (ref_rate, ref_by))
        cursor.execute("UPDATE users SET has_worked = 1 WHERE user_id=?", (target_user,))
        send_message(ref_by, f"🎉 **রেফারেল বোনাস সফল!**\n\nআপনার রেফার করা সদস্য প্রথম কাজ সম্পন্ন করায় **{ref_rate} BDT** যোগ করা হয়েছে।")
    else:
        cursor.execute("UPDATE users SET has_worked = 1 WHERE user_id=?", (target_user,))
        
    conn.commit()
    conn.close()

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
                    stats_msg = get_user_stats()
                    kb = {'inline_keyboard': [[{'text': '🔙 Back', 'callback_data': 'adm_main_menu'}]]}
                    send_message(user_id, stats_msg, kb)
                    return

                if cb_data == "adm_gmail_menu":
                    kb = {'inline_keyboard': [
                        [{'text': '🔄 Status (ON/OFF)', 'callback_data': 'toggle_gmail_status'}],
                        [{'text': '📜 Gmail History', 'callback_data': 'hist_GMAIL'}],
                        [{'text': '🔙 Back', 'callback_data': 'adm_main_menu'}]
                    ]}
                    st = get_setting('gmail_status')
                    send_message(user_id, f"📥 **Gmail Store Management**\n\nস্ট্যাটাস: **{st}**", kb)
                    return

                if cb_data == "adm_review_menu":
                    kb = {'inline_keyboard': [
                        [{'text': '🔄 Status (ON/OFF)', 'callback_data': 'toggle_review_status'}],
                        [{'text': '➕ Add Comments', 'callback_data': 'adm_add_comments'}],
                        [{'text': '📜 Review History', 'callback_data': 'hist_REVIEW'}],
                        [{'text': '🔙 Back', 'callback_data': 'adm_main_menu'}]
                    ]}
                    st = get_setting('review_status')
                    send_message(user_id, f"⭐ **Google Review Management**\n\nস্ট্যাটাস: **{st}**", kb)
                    return

                if cb_data == "adm_withdraw_menu":
                    bkash = get_setting('bkash_status')
                    nagad = get_setting('nagad_status')
                    kb = {'inline_keyboard': [
                        [{'text': f'Bkash ({bkash})', 'callback_data': 'toggle_bkash'},
                         {'text': f'Nagad ({nagad})', 'callback_data': 'toggle_nagad'}],
                        [{'text': '📜 Withdraw History', 'callback_data': 'hist_WITHDRAW'}],
                        [{'text': '🔙 Back', 'callback_data': 'adm_main_menu'}]
                    ]}
                    send_message(user_id, f"💳 **Withdraw Store Management**\n\nসর্বনিম্ন উইথড্র: `{get_setting('min_withdraw')}` BDT", kb)
                    return

                if cb_data.startswith("hist_"):
                    log_type = cb_data.replace("hist_", "")
                    history_text = get_history(log_type)
                    send_message(user_id, history_text)
                    return

                if cb_data == "toggle_gmail_status":
                    cur = get_setting('gmail_status')
                    set_setting('gmail_status', "OFF" if cur == "ON" else "ON")
                    send_message(user_id, "✅ জিমেইল কাজের স্ট্যাটাস আপডেট হয়েছে।")
                    return

                if cb_data == "toggle_review_status":
                    cur = get_setting('review_status')
                    set_setting('review_status', "OFF" if cur == "ON" else "ON")
                    send_message(user_id, "✅ রিভিউ কাজের স্ট্যাটাস আপডেট হয়েছে।")
                    return

                if cb_data == "toggle_bkash":
                    cur = get_setting('bkash_status')
                    set_setting('bkash_status', "OFF" if cur == "ON" else "ON")
                    send_message(user_id, "✅ বিকাশ স্ট্যাটাস আপডেট হয়েছে।")
                    return

                if cb_data == "toggle_nagad":
                    cur = get_setting('nagad_status')
                    set_setting('nagad_status', "OFF" if cur == "ON" else "ON")
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
                st = get_setting(f"{method}_status")
                if st == "OFF":
                    send_message(user_id, f"❌ বর্তমানে **{method.upper()}** উইথড্র বন্ধ আছে।")
                    return
                user_states[user_id] = f"WAITING_WD_DETAILS_{method}"
                send_message(user_id, f"📲 **{method.upper()} উইথড্র**\n\nআপনার **{method.upper()} নম্বর** এবং **টাকার পরিমাণ** স্পেস দিয়ে লিখুন।\n\n📌 *উদাহরণ:* `01700000000 50`")
                return

            if cb_data.startswith("app_gmail_"):
                parts = cb_data.split("_")
                target_user = int(parts[2])
                qty = int(parts[3]) if len(parts) > 3 else 1
                ensure_user(target_user)
                
                g_price = float(get_setting('gmail_price'))
                total_reward = g_price * qty
                
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
                
                cur_cnt = int(get_setting('review_count'))
                set_setting('review_count', str(cur_cnt + 1))
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
                target_user = int(cb_data.split("_")[2])
                user_states[ADMIN_ID] = f"WAITING_SUPP_REPLY_{target_user}"
                send_message(ADMIN_ID, f"💬 **User `{target_user}` কে রিপ্লাই লিখুন:**")
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
                
                g_pass = get_setting('gmail_pass')
                g_price = get_setting('gmail_price')
                notice = get_setting('gmail_notice')
                
                user_states[user_id] = "WAITING_BULK_GMAIL"
                user_gmail_drafts[user_id] = ""
                
                demo_text = f"📧 **Gmail Submission Setup**\n\n{notice}\n\n🔑 **পাসওয়ার্ড কপি করুন (টাচ করুন):**\n`{g_pass}`\n💵 **রেট:** {g_price} BDT\n\n📌 **কীভাবে এক বা একাধিক জিমেইল জমা দিবেন (ডেমো):**\n`email1@gmail.com {g_pass}`\n`email2@gmail.com {g_pass}`\n`email3@gmail.com {g_pass}`\n\nএকসাথে ১টি বা ১০টি যতগুলো ইচ্ছে নিচে লিখে পাঠিয়ে **Submit** বাটনে চাপ দিন।"
                
                sub_markup = {'inline_keyboard': [[{'text': '📥 Submit All Gmails', 'callback_data': 'submit_bulk_gmail'}]]}
                send_message(chat_id, demo_text, sub_markup)
                return

            if user_states.get(user_id) == "WAITING_BULK_GMAIL":
                current_draft = user_gmail_drafts.get(user_id, "")
                updated_draft = (current_draft + "\n" + text).strip()
                user_gmail_drafts[user_id] = updated_draft
                
                sub_markup = {'inline_keyboard': [[{'text': '📥 Submit All Gmails', 'callback_data': 'submit_bulk_gmail'}]]}
                send_message(chat_id, f"📝 **আপনার জিমেইল লিস্ট তৈরি হচ্ছে...**\n\nআপনার লেখাটি নিচে যুক্ত করা হয়েছে। আরও জিমেইল দিতে মেসেজ করুন অথবা জমা দিতে নিচের **Submit** বাটনে চাপ দিন:\n\n```\n{updated_draft}\n
