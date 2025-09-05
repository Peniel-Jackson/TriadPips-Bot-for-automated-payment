import os
import time
import json
import threading
import requests
import smtplib
from email.mime.text import MIMEText
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext

# ---------------- Config ----------------
BOT_TOKEN = "8216881905:AAFo0Lnufs8crn2IZ-p8gSaaxV3QK-i0KLs"
ADMIN_ID = 8085393860
GROUP_ID = -1003024212139
LINK_FILE = "selar_link.txt"
PAYMENTS_FILE = "payments.json"
SUBSCRIPTIONS_FILE = "subscriptions.json"

# Email config
EMAIL_USER = "triadpips@gmail.com"
EMAIL_PASS = "szec vqbd ftdm wmbh"
ADMIN_EMAIL = "triadpips@gmail.com"

# Selar API
SELAR_API_KEY = "sat_766e7801cx65111668i15l71713a32f314111"
ALLOWED_PRODUCT_PREFIX = "TriadPips Forex Academy VIP"
CUSTOM_FIELD_NAME = "Telegram ID"

# ---------------- Globals ----------------
subscriptions = {}
SELAR_LINK = ""

# ---------------- Utilities ----------------
def load_link():
    if os.path.exists(LINK_FILE):
        with open(LINK_FILE, "r") as f:
            return f.read().strip()
    return "https://selar.com/triadpipsvip"

def save_link(link):
    with open(LINK_FILE, "w") as f:
        f.write(link)

def load_subscriptions():
    global subscriptions
    if os.path.exists(SUBSCRIPTIONS_FILE):
        with open(SUBSCRIPTIONS_FILE, "r") as f:
            subscriptions = json.load(f)

def save_subscriptions():
    with open(SUBSCRIPTIONS_FILE, "w") as f:
        json.dump(subscriptions, f, indent=2)

def load_payments():
    if os.path.exists(PAYMENTS_FILE):
        with open(PAYMENTS_FILE, "r") as f:
            return json.load(f)
    return []

def save_payment(payment):
    payments = load_payments()
    payments.append(payment)
    with open(PAYMENTS_FILE, "w") as f:
        json.dump(payments, f, indent=2)

def add_user_to_group(user_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/inviteChatMember"
    requests.post(url, data={"chat_id": GROUP_ID, "user_id": user_id})

def remove_user_from_group(user_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/kickChatMember"
    requests.post(url, data={"chat_id": GROUP_ID, "user_id": user_id})

def send_email(to_email, subject, message):
    if not to_email or to_email == "Unknown Email":
        return
    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = to_email
    msg["Bcc"] = ADMIN_EMAIL
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, [to_email, ADMIN_EMAIL], msg.as_string())
    except Exception as e:
        print("❌ Email sending failed:", e)

# ---------------- Telegram Commands ----------------
def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    msg = (
        f"👋 Welcome {user.first_name}!\n\n"
        f"Your Telegram ID is: `{user.id}`\n\n"
        "👉 Keep this ID safe, you’ll need it when paying.\n\n"
        "💳 To join *TriadPips Forex Academy VIP*, click the button below:"
    )
    keyboard = [[InlineKeyboardButton("💳 Subscribe Now", url=SELAR_LINK)]]
    update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

def set_link(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        update.message.reply_text("🚫 Not authorized.")
        return
    if not context.args:
        update.message.reply_text("⚠️ Usage: /setlink <new_link>")
        return
    new_link = context.args[0]
    save_link(new_link)
    global SELAR_LINK
    SELAR_LINK = new_link
    update.message.reply_text(f"✅ Selar link updated:\n{new_link}")

def check_subscription(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    if user_id not in subscriptions:
        update.message.reply_text("❌ You don’t have an active subscription.")
        return
    expiry = subscriptions[user_id]["expiry"]
    remaining = int(expiry - time.time())
    if remaining <= 0:
        update.message.reply_text("❌ Your subscription has expired.")
        return
    years, rem = divmod(remaining, 31536000)
    months, rem = divmod(rem, 2592000)
    days, rem = divmod(rem, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    msg = f"⏳ Time remaining: {years}y {months}m {days}d {hours}h {minutes}m {seconds}s"
    update.message.reply_text(msg)

def payments(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        update.message.reply_text("🚫 Not authorized.")
        return
    all_payments = load_payments()
    if not all_payments:
        update.message.reply_text("ℹ️ No payments recorded yet.")
        return
    msg = "📒 Payment History (last 5):\n\n"
    for p in all_payments[-5:]:
        date_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(p["timestamp"]))
        msg += f"👤 {p.get('user_id', 'N/A')} | {p['product']} | {p.get('plan', 'N/A')} | {date_str}\n"
    update.message.reply_text(msg)

# ---------------- Selar API ----------------
def fetch_selar_payments():
    headers = {"Authorization": f"Bearer {SELAR_API_KEY}"}
    url = "https://selar.com/api/v1/payments"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print("❌ Failed to fetch payments:", response.text)
            return []
    except Exception as e:
        print("❌ Selar API request failed:", e)
        return []

def process_payments():
    payments_data = fetch_selar_payments()
    for p in payments_data:
        product_name = p.get("product_name", "")
        if not product_name.startswith(ALLOWED_PRODUCT_PREFIX):
            continue
        buyer_email = p.get("buyer_email", "Unknown Email")
        custom_fields = p.get("custom_fields", {})
        if CUSTOM_FIELD_NAME not in custom_fields or not str(custom_fields[CUSTOM_FIELD_NAME]).isdigit():
            save_payment({
                "user_id": "INVALID",
                "product": product_name,
                "plan": p.get("plan", "UNKNOWN"),
                "timestamp": int(time.time()),
                "buyer_email": buyer_email
            })
            send_email(
                buyer_email,
                "Action Required - TriadPips Forex Academy VIP",
                "Hello,\n\nWe received your payment but you did not provide a valid Telegram ID.\n\n"
                "Please reply to this email with your Telegram ID so we can activate your subscription.\n\n"
                "Thanks,\nPeniel Jackson"
            )
            continue
        user_id = str(custom_fields[CUSTOM_FIELD_NAME])
        plan = p.get("plan", "monthly").lower()
        expiry = time.time() + (30*24*3600 if plan=="monthly" else 365*24*3600)
        if user_id not in subscriptions or subscriptions[user_id]["expiry"] < expiry:
            subscriptions[user_id] = {"expiry": expiry, "reminded": False}
            save_subscriptions()
            add_user_to_group(user_id)
            save_payment({
                "user_id": user_id,
                "product": product_name,
                "plan": plan,
                "timestamp": int(time.time()),
                "buyer_email": buyer_email
            })
            # Telegram thank-you
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                          data={"chat_id": user_id,
                                "text": f"🙏 Thank you for your {plan} subscription!\n✅ You’ve been added to the group.\n📅 Subscription active."})
            # Email thank-you
            send_email(
                buyer_email,
                "Subscription Activated - TriadPips Forex Academy VIP",
                f"Hello,\n\nThank you for your {plan} subscription to TriadPips Forex Academy VIP.\n\n"
                f"Your Telegram ID: {user_id}\nGroup access activated.\n"
                f"Expiry Date: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expiry))}\n\n"
                "Best regards,\nPeniel Jackson"
            )
            # Notify admin
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                          data={"chat_id": ADMIN_ID,
                                "text": f"✅ User {user_id} subscribed to {plan} ({product_name}) and was added to the group."})

# ---------------- Subscription Checker ----------------
def subscription_checker():
    while True:
        process_payments()
        now = time.time
