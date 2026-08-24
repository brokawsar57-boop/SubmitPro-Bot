import os
import sqlite3
import urllib.request
import urllib.parse
import json
import time
from threading import Thread
from flask import Flask

# --- মৌলিক কনফিগারেশন ---
BOT_TOKEN = "8882134412:AAHCFAVuRk6h0-oyafS0B_bgOWSln6VqkQs"
ADMIN_ID = 7699501193  # আপনার দেওয়া টেলিগ্রাম আইডি
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

# --- ২৪ ঘণ্টা সার্ভারে ফ্রিতে চালু রাখার জন্য ফ্ল্যাস্ক ওয়েব সার্ভার ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Submit Pro Bot is Active 24/7!"

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# --- ডাটাবেজ তৈরি ও সেটিংস ---
def init_db():
    conn = sqlite3.connect("submit_pro.db")
    cursor = conn.cursor()
    
    # ইউজার টেবিল
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        balance REAL DEFAULT 0.0,
                        referrals INTEGER DEFAULT 0,
                        referred_by INTEGER,
                        has_worked INTEGER DEFAULT 0
                    )''')
    
    # সেটিংস টেবিল
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )''')
    
    default_settings = {
        'channels': '@yourchannel1,@yourchannel2',
        'ref_rate': '5.0',
        'gmail_pass': 'SetPass123',
        'gmail_price': '10.0',
        'min_withdraw': '50.0',
        'bkash_status': 'ON',
        'nagad_status': 'ON',
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

# --- টেলিগ্রাম এপিআই হেল্পার ফাংশন ---
def send_message(chat_id, text, reply_markup=None):
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup)
    try:
        req = urllib.request.Request(API_URL + "sendMessage", json.dumps(data).encode('utf-8'), {'Content-Type': 'application/json'})
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"Error sending msg: {e}")

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

# --- মেম্বারদের মেসেজ প্রসেসিং ---
user_states = {}

def handle_update(update):
    # ১. অটো-অ্যাপ্রুভ জয়েন রিকোয়েস্ট
    if "chat_join_request" in update:
        chat_id = update["chat_join_request"]["chat"]["id"]
        u_id = update["chat_join_request"]["from"]["id"]
        urllib.request.urlopen(f"{API_URL}approveChatJoinRequest?chat_id={chat_id}&user_id={u_id}")
        send_message(u_id, "✅ আপনার গ্রুপ জয়েন রিকোয়েস্ট এক্সেপ্ট করা হয়েছে!")
        return

    # ২. কলব্যাক কোয়েরি (অ্যাপ্রুভ / রিজেক্ট বাটন)
    if "callback_query" in update:
        cb = update["callback_query"]
        cb_data = cb["data"]
        
        if cb_data.startswith("app_gmail_"):
            parts = cb_data.split("_")
            target_user = int(parts[2])
            g_price = float(get_setting('gmail_price'))
            
            conn = sqlite3.connect("submit_pro.db")
            cursor = conn.cursor()
            
            # কাজ সম্পন্ন হিসেবে মার্ক ও ব্যালেন্স যোগ
            cursor.execute("UPDATE users SET balance = balance + ?, has_worked = 1 WHERE user_id=?", (g_price, target_user))
            
            # রেফারেল বোনাস চেক (প্রথম কাজ করলে রেফারকারী বোনাস পাবে)
            cursor.execute("SELECT referred_by, has_worked FROM users WHERE user_id=?", (target_user,))
            row = cursor.fetchone()
            if row and row[0] and row[1] == 0:
                ref_by = row[0]
                ref_rate = float(get_setting('ref_rate'))
                cursor.execute("UPDATE users SET balance = balance + ?, referrals = referrals + 1 WHERE user_id=?", (ref_rate, ref_by))
                send_message(ref_by, f"🎉 আপনার রেফারেল সফলভাবে একটি কাজ জমা দিয়েছে! আপনার অ্যাকাউন্টে {ref_rate} BDT বোনাস যোগ হয়েছে।")
                
            conn.commit()
            conn.close()
            
            send_message(target_user, f"✅ আপনার জমা দেওয়া **Gmail** এপ্রুভ হয়েছে! {g_price} BDT আপনার ব্যালেন্সে যোগ করা হয়েছে।")
            send_message(ADMIN_ID, f"✅ User {target_user}-এর জিমেইল এপ্রুভ করা হয়েছে।")

        elif cb_data.startswith("rej_gmail_"):
            target_user = int(cb_data.split("_")[2])
            send_message(target_user, "❌ দুঃখিত! আপনার জমা দেওয়া জিমেইলটি রিজেক্ট করা হয়েছে।")
            send_message(ADMIN_ID, f"❌ User {target_user}-এর জিমেইল রিজেক্ট করা হয়েছে।")
            
        return

    # ৩. মেসেজ হ্যান্ডলার
    if "message" in update and "text" in update["message"]:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]
        text = msg["text"]

        # স্টার্ট কমান্ড
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
            
            send_message(chat_id, "👋 **Submit Pro** বটে আপনাকে স্বাগতম! কাজ শুরু করতে নিচের অপশন নির্বাচন করুন।", main_keyboard(user_id))
            return

        # মাই অ্যাকাউন্ট ও রেফার
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
            
            msg_text = f"👤 **আপনার প্রোফাইল**\n\n💰 ব্যালেন্স: `{bal}` BDT\n👥 মোট সফল রেফার: `{refs}` জন\n\n🔗 **আপনার রেফার লিংক:**\n`{ref_link}`\n\n*(শর্ত: আপনার রেফার করা মেম্বারকে অন্তত ১টি কাজ জমা দিতে হবে, তবেই রেফারের টাকা যোগ হবে।)*"
            send_message(chat_id, msg_text)
            return

        # জিমেইল সেল অপশন
        if text == "💼 Gmail Sell":
            g_pass = get_setting('gmail_pass')
            g_price = get_setting('gmail_price')
            
            msg_text = f"📧 **Gmail Sell Work**\n\n🔑 **পাসওয়ার্ড (ট্যাপ করে কপি করুন):**\n`{g_pass}`\n\n💵 **রেট:** {g_price} BDT\n\nজিমেইল তৈরি হয়ে গেলে আপনার **Gmail Username** এবং **Password** নিচে লিখে পাঠান:"
            user_states[user_id] = "WAITING_GMAIL"
            send_message(chat_id, msg_text)
            return

        # জিমেইল সাবমিশন প্রসেস
        if user_states.get(user_id) == "WAITING_GMAIL":
            user_states[user_id] = None
            gmail_data = text
            
            # এডমিনের কাছে নোটিফিকেশন পাঠানো
            markup = {
                'inline_keyboard': [[
                    {'text': '✅ Approve', 'callback_data': f'app_gmail_{user_id}'},
                    {'text': '❌ Reject', 'callback_data': f'rej_gmail_{user_id}'}
                ]]
            }
            
            admin_msg = f"📥 **নতুন Gmail জমা পড়েছে!**\n\n👤 ইউজার ID: `{user_id}`\n📝 **তথ্য (কপি করতে ট্যাপ করুন):**\n`{gmail_data}`"
            send_message(ADMIN_ID, admin_msg, markup)
            send_message(chat_id, "✅ আপনার জিমেইল সাবমিট হয়েছে! এডমিন দেখে এপ্রুভ করলে ব্যালেন্সে টাকা যোগ হয়ে যাবে।")
            return

        # গুগল রিভিউ কাজ
        if text == "⭐ Google Review":
            r_link = get_setting('review_link')
            r_rate = get_setting('review_rate')
            r_limit = int(get_setting('review_limit'))
            r_count = int(get_setting('review_count'))
            
            if r_count >= r_limit:
                send_message(chat_id, "❌ এই মুহূর্তের গুগল রিভিউ কাজের লিমিট শেষ হয়ে গেছে! নতুন লিংক আসা পর্যন্ত অপেক্ষা করুন।")
            else:
                msg_text = f"⭐ **Google Review Work**\n\n🔗 **লিংক:** {r_link}\n💵 **রেট:** {r_rate} BDT\n📊 **অবশিষ্ট লিমিট:** {r_limit - r_count} টি\n\nকাজের নিয়ম: ফাইভ স্টার রিভিউ দিয়ে আপনার জিমেইল আইডি ও স্ক্রিনশটের তথ্য নিচে লিখুন:"
                send_message(chat_id, msg_text)
            return

        # কাজের ভিডিও
        if text == "🎥 কাজের ভিডিও":
            v_g = get_setting('video_gmail')
            v_r = get_setting('video_review')
            send_message(chat_id, f"🎥 **কাজের ভিডিও গাইড:**\n\n1. জিমেইল কাজের ভিডিও: {v_g}\n2. গুগল রিভিউ কাজের ভিডিও: {v_r}")
            return

        # উইথড্র সেকশন
        if text == "💳 Withdraw":
            conn = sqlite3.connect("submit_pro.db")
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
            row = cursor.fetchone()
            bal = row[0] if row else 0.0
            conn.close()
            
            min_wd = get_setting('min_withdraw')
            send_message(chat_id, f"💰 আপনার বর্তমান ব্যালেন্স: `{bal}` BDT\n\nসর্বনিম্ন উইথড্র: `{min_wd}` BDT\nপেমেন্ট নিতে আপনার **বিকাশ/নগদ নাম্বার ও টাকার পরিমাণ** পাঠান (যেমন: 01700000000 50):")
            user_states[user_id] = "WAITING_WITHDRAW"
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
                
                if amount < min_wd:
                    send_message(chat_id, f"❌ সর্বনিম্ন উইথড্র অ্যামাউন্ট {min_wd} BDT।")
                elif amount > bal:
                    send_message(chat_id, "❌ আপনার ব্যালেন্সে পর্যাপ্ত টাকা নেই!")
                else:
                    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (amount, user_id))
                    conn.commit()
                    send_message(ADMIN_ID, f"🚨 **নতুন Withdraw Request!**\n\n👤 User: `{user_id}`\n📱 Number: `{num}`\n💵 Amount: {amount} BDT")
                    send_message(chat_id, "✅ উইথড্র রিকোয়েস্ট পাঠানো হয়েছে। দ্রুত আপনাকে পেমেন্ট করা হবে।")
                conn.close()
            except Exception:
                send_message(chat_id, "❌ ফরম্যাট সঠিক হয়নি! আবার সঠিকভাবে লিখুন (উদাহরণ: 01700000000 50)।")
            return

        # এডমিন প্যানেল
        if text == "⚙️ Admin Panel" and user_id == ADMIN_ID:
            send_message(chat_id, "⚙️ **Admin Panel**\n\nএখানে আপনি ডাটাবেজ আপডেট করতে পারবেন।\nউদাহরণ: জিমেইল পাসওয়ার্ড পরিবর্তন করতে ডায়াল করুন:\n`/set_pass newpass123`")
            return

        if text.startswith("/set_pass") and user_id == ADMIN_ID:
            new_p = text.split()[1]
            set_setting('gmail_pass', new_p)
            send_message(chat_id, f"✅ জিমেইল পাসওয়ার্ড আপডেট করা হয়েছে: `{new_p}`")
            return

# --- বটের প্রধান লুপ ---
def bot_loop():
    offset = 0
    print("Submit Pro Bot is starting...")
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
    # ফ্ল্যাস্ক ওয়েবসাইট চালু
    Thread(target=run_web).start()
    # বট লুপ চালু
    bot_loop()
