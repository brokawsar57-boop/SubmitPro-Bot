import os
import sqlite3
import urllib.request
import urllib.parse
import json
import time
from threading import Thread
from flask import Flask

BOT_TOKEN = "8882134412:AAHCFAVuRk6h0-oyafS0B_bgOWSln6VqkQs"
ADMIN_ID = 7699501193
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

app = Flask(__name__)

@app.route('/')
def home():
    return "Submit Pro Bot is Active 24/7!"

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

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
    
    default_settings = {
        'channels': '@freeearningksteam,@freeearningsupport2',
        'ref_rate': '5.0',
        'gmail_pass': 'SetPass123',
        'gmail_price': '10.0',
        'min_withdraw': '50.0',
        'video_gmail': 'https://youtube.com',
        'video_review': 'https://youtube.com',
        'review_link': 'https://maps.google.com',
        'review_rate': '15.0',
        'review_limit': '10',
        'review_count': '0'
    }
    
    for key, val in default_settings.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, val))
    conn.commit()
    conn.close()

init_db()

def get_setting(key):
    conn = sqlite3.connect("submit_pro.db")
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else ""

def set_setting(key, val):
    conn = sqlite3.connect("submit_pro.db")
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, val))
    conn.commit()
    conn.close()

def send_message(chat_id, text, reply_markup=None):
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup)
    try:
        req = urllib.request.Request(API_URL + "sendMessage", json.dumps(data).encode('utf-8'), {'Content-Type': 'application/json'})
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"Error sending msg: {e}")

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
            [{'text': '🎥 কাজের ভিডিও'}]
        ],
        'resize_keyboard': True
    }
    if user_id == ADMIN_ID:
        kb['keyboard'].append([{'text': '⚙️ Admin Panel'}])
    return kb

user_states = {}

def handle_update(update):
    if "callback_query" in update:
        cb = update["callback_query"]
        cb_data = cb["data"]
        user_id = cb["from"]["id"]
        
        if cb_data == "verify_membership":
            if check_joined(user_id):
                send_message(user_id, "✅ **ভেরিফিকেশন সফল হয়েছে!**\n\nকাজ শুরু করতে নিচের অপশন নির্বাচন করুন।", main_keyboard(user_id))
            else:
                send_message(user_id, "❌ **আপনি এখনো সবগুলো চ্যানেলে জয়েন করেননি!**\n\nসবগুলোতে জয়েন করে আবার Verify বাটনে চাপ দিন।")
            return

        if cb_data.startswith("app_gmail_"):
            target_user = int(cb_data.split("_")[2])
            g_price = float(get_setting('gmail_price'))
            
            conn = sqlite3.connect("submit_pro.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET balance = balance + ?, has_worked = 1 WHERE user_id=?", (g_price, target_user))
            
            cursor.execute("SELECT referred_by, has_worked FROM users WHERE user_id=?", (target_user,))
            row = cursor.fetchone()
            if row and row[0] and row[1] == 0:
                ref_by = row[0]
                ref_rate = float(get_setting('ref_rate'))
                cursor.execute("UPDATE users SET balance = balance + ?, referrals = referrals + 1 WHERE user_id=?", (ref_rate, ref_by))
                send_message(ref_by, f"🎉 আপনার রেফারেল সফলভাবে একটি কাজ জমা দিয়েছে! অ্যাকাউন্টে {ref_rate} BDT যোগ হয়েছে।")
                
            conn.commit()
            conn.close()
            send_message(target_user, f"✅ আপনার Gmail এপ্রুভ হয়েছে! {g_price} BDT ব্যালেন্সে যোগ করা হয়েছে।")
            send_message(ADMIN_ID, f"✅ User {target_user}-এর জিমেইল এপ্রুভ করা হয়েছে।")

        elif cb_data.startswith("rej_gmail_"):
            target_user = int(cb_data.split("_")[2])
            send_message(target_user, "❌ দুঃখিত! আপনার জমা দেওয়া জিমেইলটি রিজেক্ট করা হয়েছে।")
            send_message(ADMIN_ID, f"❌ User {target_user}-এর জিমেইল রিজেক্ট করা হয়েছে।")
        return

    if "message" in update and "text" in update["message"]:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]
        text = msg["text"]

        if text.startswith("/start"):
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
                send_message(chat_id, "⚠️ **বটটি ব্যবহার করতে হলে আপনাকে আমাদের অফিশিয়াল চ্যানেলগুলোতে জয়েন করতে হবে!**\n\nনিচের চ্যানেলগুলোতে জয়েন করে 'Verify' বাটনে ক্লিক করুন।", force_join_markup())
            else:
                send_message(chat_id, "👋 **Submit Pro** বটে আপনাকে স্বাগতম! কাজ শুরু করতে নিচের অপশন নির্বাচন করুন.", main_keyboard(user_id))
            return

        if not check_joined(user_id):
            send_message(chat_id, "⚠️ **কাজ শুরু করতে আগে নিচের চ্যানেলগুলোতে জয়েন হয়ে ভেরিফাই করুন!**", force_join_markup())
            return

        if text == "👤 My Account":
            conn = sqlite3.connect("submit_pro.db")
            cursor = conn.cursor()
            cursor.execute("SELECT balance, referrals FROM users WHERE user_id=?", (user_id,))
            row = cursor.fetchone()
            conn.close()
            bal = row[0] if row else 0.0
            refs = row[1] if row else 0
            
            bot_info = json.loads(urllib.request.urlopen(API_URL + "getMe").read().decode('utf-8'))
            bot_username = bot_info['result']['username']
            ref_link = f"https://t.me/{bot_username}?start={user_id}"
            
            send_message(chat_id, f"👤 **আপনার প্রোফাইল**\n\n💰 ব্যালেন্স: `{bal}` BDT\n👥 সফল রেফার: `{refs}` জন\n\n🔗 **রেফার লিংক:**\n`{ref_link}`")
            return

        if text == "💼 Gmail Sell":
            g_pass = get_setting('gmail_pass')
            g_price = get_setting('gmail_price')
            user_states[user_id] = "WAITING_GMAIL"
            send_message(chat_id, f"📧 **Gmail Sell Work**\n\n🔑 **পাসওয়ার্ড:** `{g_pass}`\n💵 **রেট:** {g_price} BDT\n\nআপনার **Gmail Username** এবং **Password** নিচে লিখে পাঠান:")
            return

        if user_states.get(user_id) == "WAITING_GMAIL":
            user_states[user_id] = None
            markup = {'inline_keyboard': [[
                {'text': '✅ Approve', 'callback_data': f'app_gmail_{user_id}'},
                {'text': '❌ Reject', 'callback_data': f'rej_gmail_{user_id}'}
            ]]}
            send_message(ADMIN_ID, f"📥 **নতুন Gmail জমা পড়েছে!**\n\n👤 ইউজার ID: `{user_id}`\n📝 **তথ্য:**\n`{text}`", markup)
            send_message(chat_id, "✅ আপনার জিমেইল সাবমিট হয়েছে!")
            return

        if text == "⭐ Google Review":
            r_link = get_setting('review_link')
            r_rate = get_setting('review_rate')
            r_limit = int(get_setting('review_limit'))
            r_count = int(get_setting('review_count'))
            if r_count >= r_limit:
                send_message(chat_id, "❌ গুগল রিভিউ কাজের লিমিট শেষ হয়ে গেছে!")
            else:
                send_message(chat_id, f"⭐ **Google Review Work**\n\n🔗 **লিংক:** {r_link}\n💵 **রেট:** {r_rate} BDT\n\nরিভিউ দিয়ে আপনার তথ্য লিখে পাঠান:")
            return

        if text == "🎥 কাজের ভিডিও":
            send_message(chat_id, f"🎥 **কাজের ভিডিও গাইড:**\n\n1. জিমেইল কাজ: {get_setting('video_gmail')}\n2. গুগল রিভিউ: {get_setting('video_review')}")
            return

        if text == "💳 Withdraw":
            conn = sqlite3.connect("submit_pro.db")
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
            bal = cursor.fetchone()[0]
            conn.close()
            user_states[user_id] = "WAITING_WITHDRAW"
            send_message(chat_id, f"💰 ব্যালেন্স: `{bal}` BDT\nসর্বনিম্ন উইথড্র: `{get_setting('min_withdraw')}` BDT\n\nনাম্বার ও পরিমাণ পাঠান (যেমন: 01700000000 50):")
            return

        if user_states.get(user_id) == "WAITING_WITHDRAW":
            user_states[user_id] = None
            try:
                parts = text.split()
                num, amount = parts[0], float(parts[1])
                min_wd = float(get_setting('min_withdraw'))
                conn = sqlite3.connect("submit_pro.db")
                cursor = conn.cursor()
                cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
                bal = cursor.fetchone()[0]
                if amount >= min_wd and amount <= bal:
                    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (amount, user_id))
                    conn.commit()
                    send_message(ADMIN_ID, f"🚨 **Withdraw Request!**\n\n👤 User: `{user_id}`\n📱 Number: `{num}`\n💵 Amount: {amount} BDT")
                    send_message(chat_id, "✅ উইথড্র রিকোয়েস্ট সফল হয়েছে।")
                else:
                    send_message(chat_id, "❌ অপর্যাপ্ত ব্যালেন্স বা ভুল অ্যামাউন্ট।")
                conn.close()
            except Exception:
                send_message(chat_id, "❌ ফরম্যাট সঠিক হয়নি।")
            return

        if text == "⚙️ Admin Panel" and user_id == ADMIN_ID:
            send_message(chat_id, "⚙️ **Admin Commands:**\n\n1. চ্যানেল সেটআপ: `/set_channels @ch1,@ch2`\n2. পাসওয়ার্ড সেটআপ: `/set_pass newpass`\n3. জিমেইল রেট: `/set_gprice 10`\n4. রিভিউ লিংক: `/set_rlink url`")
            return

        if text.startswith("/set_channels") and user_id == ADMIN_ID:
            chs = text.split(maxsplit=1)[1] if len(text.split()) > 1 else ""
            set_setting('channels', chs)
            send_message(chat_id, f"✅ চ্যানেল আপডেট করা হয়েছে: `{chs}`")
            return

def bot_loop():
    offset = 0
    while True:
        try:
            req = urllib.request.urlopen(f"{API_URL}getUpdates?offset={offset}&timeout=10")
            data = json.loads(req.read().decode('utf-8'))
            for result in data.get("result", []):
                offset = result["update_id"] + 1
                handle_update(result)
        except Exception:
            time.sleep(2)

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot_loop()
