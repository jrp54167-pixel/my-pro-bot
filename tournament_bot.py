import os
import sqlite3
import logging
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================= DUMMY WEB SERVER FOR RENDER =================
web_app = Flask('')

@web_app.route('/')
def home():
    return "Bot is Alive & Running!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# ================= CONFIGURATION =================
TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_ID = 7190437569

JOIN_BONUS = 50.0   # সাইনআপ বোনাস ৫০ টাকা
MIN_DEPOSIT = 50.0  # মিনিমাম ডিপোজিট শর্ত ৫০ টাকা
REFER_BONUS = 5.0   # প্রতি রেফারে ৫ টাকা

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ================= DATABASE SETUP =================
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0.0,
            has_deposited INTEGER DEFAULT 0,
            referred_by INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            match_id TEXT PRIMARY KEY,
            category TEXT,
            title TEXT,
            fee REAL,
            prize REAL,
            per_kill REAL,
            map_name TEXT,
            match_time TEXT,
            slots INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT balance, has_deposited FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        referred_by = None
        if args and args[0].isdigit():
            ref_id = int(args[0])
            if ref_id != user_id:
                referred_by = ref_id
        
        # নতুন ইউজারকে ৫০ টাকা বোনাস
        cursor.execute("INSERT INTO users (user_id, balance, has_deposited, referred_by) VALUES (?, ?, 0, ?)", 
                       (user_id, JOIN_BONUS, referred_by))
        
        welcome_text = (
            f"🎉 **স্বাগতম!** আপনি পেয়েছেন ৳{JOIN_BONUS:.2f} সাইনআপ বোনাস!\n\n"
            f"⚠️ **শর্ত:** এই বোনাসটি আনলক করতে এবং ম্যাচ খেলে উইথড্র দিতে অন্তত **৳{MIN_DEPOSIT:.2f}** ডিপোজিট করতে হবে।\n"
        )
        
        if referred_by:
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (REFER_BONUS, referred_by))
            try:
                await context.bot.send_message(
                    chat_id=referred_by,
                    text=f"🎊 **অভিনন্দন!** আপনার রেফার লিংকে নতুন সদস্য জয়েন করায় আপনি ৳{REFER_BONUS:.2f} বোনাস পেয়েছেন!"
                )
            except Exception:
                pass
        conn.commit()
    else:
        welcome_text = "👋 **আমাদের ই-স্পোর্টস টুর্নামেন্ট বোটে আপনাকে পুনরায় স্বাগতম!**\n"
    
    conn.close()
    
    bot_obj = await context.bot.get_me()
    refer_link = f"https://t.me/{bot_obj.username}?start={user_id}"
    
    welcome_text += f"\n🔗 **আপনার রেফারেল লিংক:**\n`{refer_link}`\n\n📢 আপনার বন্ধুদের ইনভাইট করুন এবং প্রতি রেফারে পান ৳{REFER_BONUS:.2f} বোনাস!"
    
    keyboard = [
        [InlineKeyboardButton("🏆 Active Matches", callback_data="matches")],
        [InlineKeyboardButton("💰 Wallet & Balance", callback_data="wallet")],
        [InlineKeyboardButton("📞 Support", callback_data="support")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)

async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance, has_deposited FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    balance = row[0] if row else 0.0
    has_deposited = row[1] if row else 0
    
    if has_deposited == 1:
        status = "✅ **Unlocked** (উইথড্র ও গেম প্লে করার উপযোগী)"
    else:
        status = f"🔒 **Locked** (ব্যবহার করতে অন্তত ৳{MIN_DEPOSIT:.2f} ডিপোজিট করুন)"
    
    text = (
        f"💳 **আপনার মূল ব্যালেন্স:** ৳{balance:.2f}\n"
        f"📌 **বোনাস স্ট্যাটাস:** {status}\n\n"
        f"💡 মিনিমাম ৳{MIN_DEPOSIT:.2f} ডিপোজিট করলেই বোনাসসহ পুরো টাকা আনলক ও উইথড্র করতে পারবেন!"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ আপনি এই কমান্ড ব্যবহার করার অনুমোদন পাননি।")
        return
        
    text = (
        "🛠️ **অ্যাডমিন কন্ট্রোল প্যানেল**\n\n"
        "১. নতুন ম্যাচ যোগ করতে পাঠান:\n"
        "`MatchID | Category | Title | Fee | Prize | PerKill | Map | Time | Slots`\n\n"
        "২. কোনো ইউজার ৫০+ টাকা ডিপোজিট করলে বোনাস আনলক করতে পাঠান:\n"
        "`UNLOCK | User_ID`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id == ADMIN_ID:
        # ৫০ টাকা ডিপোজিট নিশ্চিত করার পর আনলক কমান্ড
        if text.startswith("UNLOCK"):
            try:
                target_user = int(text.split("|")[1].strip())
                conn = sqlite3.connect("database.db")
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET has_deposited = 1 WHERE user_id = ?", (target_user,))
                conn.commit()
                conn.close()
                await update.message.reply_text(f"✅ User ID: `{target_user}` এর ৫০ টাকার বোনাস ও ব্যালেন্স আনলক করা হয়েছে!")
                
                # প্লেয়ারকে মেসেজ পাঠানো
                try:
                    await context.bot.send_message(
                        chat_id=target_user,
                        text="🎉 **অভিনন্দন!** আপনার ডিপোজিট সফল হয়েছে এবং আপনার ৫০ টাকা বোনাসসহ মূল ব্যালেন্স সম্পূর্ণ আনলক করে দেওয়া হয়েছে!"
                    )
                except Exception:
                    pass
                return
            except Exception:
                await update.message.reply_text("❌ আনলক ফরম্যাট ভুল! লিখুন: `UNLOCK | User_ID`")
                return

        # ম্যাচ এড করার অপশন
        if "|" in text:
            parts = [p.strip() for p in text.split("|")]
            if len(parts) == 9:
                match_id, category, title, fee, prize, per_kill, map_name, match_time, slots = parts
                conn = sqlite3.connect("database.db")
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO matches VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (match_id, category, title, float(fee), float(prize), float(per_kill), map_name, match_time, int(slots)))
                conn.commit()
                conn.close()
                await update.message.reply_text("✅ **ম্যাচ সফলভাবে যুক্ত/আপডেট করা হয়েছে!**")
            else:
                await update.message.reply_text("❌ **Format Error!** সঠিকভাবে ৯টি তথ্য দিন।")

async def show_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM matches")
    matches = cursor.fetchall()
    conn.close()
    
    if not matches:
        text = "🏆 **বর্তমানে কোনো একটিভ ম্যাচ নেই!**"
    else:
        text = "🏆 **চলমান ম্যাচ সমূহের তালিকা:**\n\n"
        for m in matches:
            text += f"🎮 **{m[2]}** ({m[1]})\n🆔 ID: `{m[0]}`\n💰 Fee: ৳{m[3]} | Prize: ৳{m[4]} | PerKill: ৳{m[5]}\n🗺️ Map: {m[6]} | ⏰ Time: {m[7]}\n👥 Slots: {m[8]}\n------------------------------\n"
            
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "wallet":
        await wallet(update, context)
    elif query.data == "matches":
        await show_matches(update, context)
    elif query.data == "support":
        await query.answer()
        await query.edit_message_text("📞 সহায়তার জন্য এডমিনকে সরাসরি মেসেজ দিন: @finalzonebd", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]))
    elif query.data == "main_menu":
        await query.answer()
        await start(update, context)

def main():
    keep_alive()
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.run_polling()

if __name__ == "__main__":
    main()
