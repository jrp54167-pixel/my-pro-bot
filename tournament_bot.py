import re
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# --- CONFIGURATION ---
TOKEN = "8892559830:AAEVaCFwss72-E-6BcTYQkvGlS3ZoHtAe38"
ADMIN_ID = 7190437569

BKASH_NUMBER = "01301206062"

# Databases
user_balances = {}
user_profiles = {}
pending_withdraws = {}
pending_deposits = {}

# Dynamic Tournaments Data
tournaments = {
    "match_101": {
        "title": "🔥 Solo Survival Mode",
        "category": "Solo",
        "fee": 20,
        "prize": 100,
        "per_kill": 10,
        "map": "Bermuda",
        "time": "Today 08:00 PM",
        "slots": 48,
        "joined": []
    },
    "match_102": {
        "title": "💥 CS Custom 4v4 War",
        "category": "CS Custom (4v4)",
        "fee": 40,
        "prize": 200,
        "per_kill": 0,
        "map": "Clash Squad",
        "time": "Today 09:00 PM",
        "slots": 8,
        "joined": []
    },
    "match_103": {
        "title": "🐺 Lone Wolf 1v1 Battle",
        "category": "Lone Wolf",
        "fee": 15,
        "prize": 50,
        "per_kill": 0,
        "map": "Iron Cage",
        "time": "Today 10:00 PM",
        "slots": 2,
        "joined": []
    }
}

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("🏆 Active Matches"), KeyboardButton("👤 My Profile")],
        [KeyboardButton("💳 Deposit"), KeyboardButton("🏧 Withdraw")],
        [KeyboardButton("📊 Leaderboard"), KeyboardButton("📞 Support")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- START & USER PANEL ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_balances:
        user_balances[user_id] = 0
    if user_id not in user_profiles:
        user_profiles[user_id] = {"ign": "Not Set", "uid": "Not Set", "played": 0, "wins": 0}

    text = (
        f"🎮 **Welcome to Final Zone eSports!**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 **Player ID:** `{user_id}`\n"
        f"💰 **Wallet Balance:** `{user_balances[user_id]} BDT`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"নিচের মেনু থেকে সার্ভিস নির্বাচন করুন:"
    )
    await update.message.reply_text(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

# --- ADMIN PANEL ---
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ Command: /admin """
    if update.effective_user.id != ADMIN_ID:
        return

    admin_kbd = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add New Match", callback_data="admin_add_match")],
        [InlineKeyboardButton("✏️ Edit Existing Match", callback_data="admin_edit_list")],
        [InlineKeyboardButton("❌ Delete Match", callback_data="admin_delete_list")]
    ])
    await update.message.reply_text("🔐 **ADMIN MATCH MANAGEMENT**\nম্যাচ কন্ট্রোল করতে অপশন সিলেক্ট করুন:", reply_markup=admin_kbd)

# --- MAIN MESSAGE HANDLER ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "No_Username"
    text_input = update.message.text if update.message.text else ""

    if user_id not in user_balances:
        user_balances[user_id] = 0
    if user_id not in user_profiles:
        user_profiles[user_id] = {"ign": "Not Set", "uid": "Not Set", "played": 0, "wins": 0}

    # 1. Active Matches List
    if text_input == "🏆 Active Matches":
        text = "🎮 **Available Tournaments**\nআপনার পছন্দের ক্যাটাগরির ম্যাচে জয়েন করুন:\n\n"
        buttons = []
        for m_id, m in tournaments.items():
            joined_count = len(m["joined"])
            btn_text = f"[{m.get('category', 'Match')}] {m['title']} | Fee: {m['fee']} BDT ({joined_count}/{m['slots']})"
            buttons.append([InlineKeyboardButton(btn_text, callback_data=f"view_{m_id}")])

        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
        return

    # 2. Profile
    elif text_input == "👤 My Profile":
        p = user_profiles[user_id]
        profile_text = (
            f"👤 **PLAYER DASHBOARD**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 **ID:** `{user_id}`\n"
            f"👤 **Username:** @{username}\n"
            f"🎮 **IGN:** `{p['ign']}`\n"
            f"🔢 **UID:** `{p['uid']}`\n"
            f"📊 **Played:** `{p['played']}` | 💰 **Balance:** `{user_balances[user_id]} BDT`\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )
        kbd = InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Update Game Info", callback_data="set_profile_info")]])
        await update.message.reply_text(profile_text, reply_markup=kbd, parse_mode="Markdown")
        return

    # 3. Deposit (Only bKash)
    elif text_input == "💳 Deposit":
        context.user_data["state"] = "waiting_deposit"
        dep_text = (
            f"💳 **INSTANT bKash DEPOSIT**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"• **bKash (Personal):** `{BKASH_NUMBER}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ **টাকা ক্যাশ আউট/সেন্ড মানি করার পর:**\n"
            "বটে আপনার **Sender Number, Amount এবং TrxID** মেসেজ হিসেবে পাঠান।"
        )
        await update.message.reply_text(dep_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")
        return

    # 4. Withdraw
    elif text_input == "🏧 Withdraw":
        if user_balances[user_id] < 50:
            await update.message.reply_text("❌ **সর্বনিম্ন উইথড্র ৫০ BDT।**")
            return
        context.user_data["state"] = "waiting_withdraw"
        await update.message.reply_text(f"🏧 **WITHDRAWAL**\nমেসেজে লিখুন: `[bKash Number] [Amount]`\nউদাহরণ: `01711111111 100`", parse_mode="Markdown")
        return

    # 5. Leaderboard
    elif text_input == "📊 Leaderboard":
        sorted_users = sorted(user_balances.items(), key=lambda x: x[1], reverse=True)[:5]
        lb_text = "🏆 **TOP PLAYERS LEADERBOARD**\n━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (u_id, bal) in enumerate(sorted_users, 1):
            lb_text += f"{i}. User `{u_id}` — {bal} BDT\n"
        await update.message.reply_text(lb_text, parse_mode="Markdown")
        return

    # 6. Support
    elif text_input == "📞 Support":
        await update.message.reply_text("📞 **Live Support:** https://t.me/finalzonebd")
        return

    # --- STATE PROCESSORS ---
    state = context.user_data.get("state")

    if state == "adding_new_match" and user_id == ADMIN_ID:
        context.user_data["state"] = None
        try:
            # Format: MatchID | Category | Title | Fee | Prize | PerKill | Map | Time | Slots
            p = text_input.split("|")
            m_id = p[0].strip()
            tournaments[m_id] = {
                "category": p[1].strip(),
                "title": p[2].strip(),
                "fee": int(p[3].strip()),
                "prize": int(p[4].strip()),
                "per_kill": int(p[5].strip()),
                "map": p[6].strip(),
                "time": p[7].strip(),
                "slots": int(p[8].strip()),
                "joined": []
            }
            await update.message.reply_text(f"✅ **Match Created Successfully!**\nID: `{m_id}`", parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(
                "❌ **Format Error!**\nব্যবহার করুন:\n`MatchID | Category | Title | Fee | Prize | PerKill | Map | Time | Slots`"
            )

    elif state == "editing_match_data" and user_id == ADMIN_ID:
        context.user_data["state"] = None
        try:
            m_id = context.user_data.get("editing_m_id")
            p = text_input.split("|")
            tournaments[m_id]["title"] = p[0].strip()
            tournaments[m_id]["fee"] = int(p[1].strip())
            tournaments[m_id]["prize"] = int(p[2].strip())
            tournaments[m_id]["per_kill"] = int(p[3].strip())
            tournaments[m_id]["time"] = p[4].strip()
            await update.message.reply_text(f"✅ **Match Updated!**\nUpdated `{m_id}`", parse_mode="Markdown")
        except Exception:
            await update.message.reply_text("❌ **Format Error!**\nব্যবহার করুন: `Title | Fee | Prize | PerKill | Time`")

    elif state == "updating_ign_uid":
        context.user_data["state"] = None
        parts = text_input.split()
        if len(parts) >= 2:
            user_profiles[user_id]["ign"] = parts[0]
            user_profiles[user_id]["uid"] = parts[1]
            await update.message.reply_text("✅ Game Profile Updated!")

    elif state == "waiting_deposit":
        context.user_data["state"] = None
        dep_id = f"dep_{user_id}_{update.message.message_id}"
        pending_deposits[dep_id] = {"user_id": user_id, "text": text_input}
        await update.message.reply_text("⏳ **ডিপোজিট রিকোয়েস্ট জমা হয়েছে!**")
        admin_kbd = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Approve 50 BDT", callback_data=f"app_d_{dep_id}_50"), InlineKeyboardButton("✅ Approve 100 BDT", callback_data=f"app_d_{dep_id}_100")],
            [InlineKeyboardButton("❌ Reject", callback_data=f"rej_d_{dep_id}")]
        ])
        msg = f"🔔 **NEW DEPOSIT (bKash)**\n👤 @{username}\n🆔 `{user_id}`\n\nInfo: {text_input}"
        if update.message.photo:
            await context.bot.send_photo(ADMIN_ID, photo=update.message.photo[-1].file_id, caption=msg, reply_markup=admin_kbd, parse_mode="Markdown")
        else:
            await context.bot.send_message(ADMIN_ID, text=msg, reply_markup=admin_kbd, parse_mode="Markdown")

    elif state == "waiting_withdraw":
        context.user_data["state"] = None
        nums = re.findall(r"\b\d+\b", text_input)
        amt = int(nums[1]) if len(nums) > 1 else 50
        if user_balances[user_id] < amt:
            await update.message.reply_text("❌ পর্যাপ্ত টাকা নেই।")
            return
        user_balances[user_id] -= amt
        w_id = f"w_{user_id}_{update.message.message_id}"
        pending_withdraws[w_id] = {"user_id": user_id, "amount": amt}
        await update.message.reply_text(f"✅ `{amt} BDT` উইথড্র প্রসেসিংয়ে রয়েছে।")
        admin_kbd = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Approve", callback_data=f"app_w_{w_id}"), InlineKeyboardButton("❌ Reject", callback_data=f"rej_w_{w_id}")]])
        await context.bot.send_message(ADMIN_ID, text=f"💸 **WITHDRAW**\n👤 @{username}\n🆔 `{user_id}`\n💰 `{amt} BDT`\nDetails: {text_input}", reply_markup=admin_kbd, parse_mode="Markdown")

# --- CALLBACK BUTTONS ---
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    # Admin Control Options
    if data == "admin_add_match" and user_id == ADMIN_ID:
        context.user_data["state"] = "adding_new_match"
        await query.message.reply_text(
            "➕ **নতুন ম্যাচ যোগ করার ফরম্যাট:**\n\n"
            "`MatchID | Category | Title | Fee | Prize | PerKill | Map | Time | Slots`\n\n"
            "👉 **ক্যাটাগরি অপশনসমূহ:** `Solo`, `Duo`, `Squad`, `Lone Wolf`, `CS Custom (4v4)`, `Survival Mode`\n\n"
            "উদাহরণ:\n`match_104 | CS Custom (4v4) | 4v4 Clash War | 50 | 300 | 0 | Bermuda | 09 PM | 8`",
            parse_mode="Markdown"
        )

    elif data == "admin_edit_list" and user_id == ADMIN_ID:
        buttons = []
        for m_id, m in tournaments.items():
            buttons.append([InlineKeyboardButton(f"✏️ {m['title']}", callback_data=f"aedit_{m_id}")])
        await query.edit_message_text("এডিট করতে একটি ম্যাচ সিলেক্ট করুন:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("aedit_") and user_id == ADMIN_ID:
        m_id = data.replace("aedit_", "")
        context.user_data["state"] = "editing_match_data"
        context.user_data["editing_m_id"] = m_id
        await query.message.reply_text(
            f"✏️ **`{m_id}` এডিট করতে নতুন তথ্য লিখে পাঠান:**\n\n"
            f"ফরম্যাট: `Title | Fee | Prize | PerKill | Time`\n"
            f"উদাহরণ: `🔥 Solo Survival War | 20 | 100 | 10 | Tomorrow 8 PM`",
            parse_mode="Markdown"
        )

    elif data == "admin_delete_list" and user_id == ADMIN_ID:
        buttons = []
        for m_id, m in tournaments.items():
            buttons.append([InlineKeyboardButton(f"❌ Delete {m['title']}", callback_data=f"adel_{m_id}")])
        await query.edit_message_text("ডিলিট করতে কোনো ম্যাচ সিলেক্ট করুন:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("adel_") and user_id == ADMIN_ID:
        m_id = data.replace("adel_", "")
        if m_id in tournaments:
            del tournaments[m_id]
            await query.edit_message_text(f"🗑️ Match `{m_id}` Deleted!")

    # User Interactions
    elif data == "set_profile_info":
        context.user_data["state"] = "updating_ign_uid"
        await query.message.reply_text("👉 মেসেজে আপনার **In-Game Name** এবং **UID** দিন (Ex: `ProGamer 12345678`)")

    elif data.startswith("view_"):
        m_id = data.replace("view_", "")
        m = tournaments[m_id]
        text = (
            f"🏆 **{m['title']}**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 **Category:** `{m.get('category', 'Tournament')}`\n"
            f"💵 **Entry Fee:** `{m['fee']} BDT`\n"
            f"🎁 **Total Prize:** `{m['prize']} BDT`\n"
            f"🎯 **Per Kill Bonus:** `{m.get('per_kill', 0)} BDT`\n"
            f"🗺️ **Map:** `{m['map']}`\n"
            f"⏰ **Time:** `{m['time']}`\n"
            f"👥 **Slots:** `{len(m['joined'])}/{m['slots']}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )
        kbd = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Join Match", callback_data=f"joinm_{m_id}")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_matches")]
        ])
        await query.edit_message_text(text, reply_markup=kbd, parse_mode="Markdown")

    elif data == "back_matches":
        buttons = []
        for m_id, m in tournaments.items():
            btn_text = f"[{m.get('category', 'Match')}] {m['title']} | Fee: {m['fee']} BDT"
            buttons.append([InlineKeyboardButton(btn_text, callback_data=f"view_{m_id}")])
        await query.edit_message_text("🎮 **Available Tournaments**", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("joinm_"):
        m_id = data.replace("joinm_", "")
        m = tournaments[m_id]

        if user_id in m["joined"]:
            await query.message.reply_text("⚠️ আপনি অলরেডি জয়েন করেছেন!")
            return

        if len(m["joined"]) >= m["slots"]:
            await query.message.reply_text("❌ স্লট ফুল!")
            return

        p = user_profiles.get(user_id, {})
        if p.get("ign") == "Not Set":
            await query.message.reply_text("❌ আগে Profile আপডেট করে IGN ও UID সেট করুন।")
            return

        if user_balances.get(user_id, 0) >= m["fee"]:
            user_balances[user_id] -= m["fee"]
            m["joined"].append(user_id)
            user_profiles[user_id]["played"] += 1
            await query.edit_message_text(f"✅ **Registration Successful!**\nঅবশিষ্ট ব্যালেন্স: `{user_balances[user_id]} BDT`", parse_mode="Markdown")
            await context.bot.send_message(ADMIN_ID, text=f"🎮 **PLAYER JOINED**\nUser: `{user_id}`\nCategory: `{m.get('category')}`\nMatch: {m['title']}")
        else:
            await query.message.reply_text(f"❌ পর্যাপ্ত ব্যালেন্স নেই!")

    elif data.startswith("app_d_"):
        parts = data.split("_")
        dep_id = f"{parts[2]}_{parts[3]}_{parts[4]}"
        amount = int(parts[5])
        if dep_id in pending_deposits:
            u_id = pending_deposits[dep_id]["user_id"]
            user_balances[u_id] = user_balances.get(u_id, 0) + amount
            del pending_deposits[dep_id]
            await query.edit_message_text(f"✅ Approved Deposit `{amount} BDT` for ID: `{u_id}`")
            await context.bot.send_message(u_id, f"🎉 **Deposit Approved!** `{amount} BDT` যোগ হয়েছে।")

    elif data.startswith("rej_d_"):
        await query.edit_message_text("❌ Deposit Rejected.")

    elif data.startswith("app_w_"):
        w_id = data.replace("app_w_", "")
        if w_id in pending_withdraws:
            u_id = pending_withdraws[w_id]["user_id"]
            amt = pending_withdraws[w_id]["amount"]
            del pending_withdraws[w_id]
            await query.edit_message_text(f"✅ Approved Withdraw `{amt} BDT` for ID: `{u_id}`")
            await context.bot.send_message(u_id, f"🎉 **Withdraw Completed!**")

    elif data.startswith("rej_w_"):
        w_id = data.replace("rej_w_", "")
        if w_id in pending_withdraws:
            u_id = pending_withdraws[w_id]["user_id"]
            amt = pending_withdraws[w_id]["amount"]
            user_balances[u_id] = user_balances.get(u_id, 0) + amt
            del pending_withdraws[w_id]
            await query.edit_message_text(f"❌ Rejected & Refunded `{amt} BDT`")

# --- ENGINE ---
def run_bot():
    app = (
        Application.builder()
        .token(TOKEN)
        .connect_timeout(60.0)
        .read_timeout(60.0)
        .write_timeout(60.0)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_message))

    print("🚀 Pro Esports Bot Running...")
    app.run_polling(poll_interval=1.0, drop_pending_updates=True)

if __name__ == "__main__":
    run_bot()
