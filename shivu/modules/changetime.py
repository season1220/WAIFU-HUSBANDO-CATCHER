from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, user_totals_collection

# --- 👑 OWNER SETTINGS ---
# Yahan apni Asli ID dalein
OWNER_ID = 7164618867
# -------------------------

async def changetime(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    chat_id = str(update.effective_chat.id)
    
    # 1. Check agar number diya hai
    if not context.args:
        await update.message.reply_text("⚠️ **Format:** `/changetime [Number]`", parse_mode='Markdown')
        return
    
    try:
        new_freq = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Number likhna padega (e.g., 100).")
        return

    # 2. 👑 OWNER POWER (Limitless)
    # Agar user ID match hoti hai, toh koi rok-tok nahi
    if user_id == OWNER_ID:
        await user_totals_collection.update_one({'chat_id': chat_id}, {'$set': {'message_frequency': new_freq}}, upsert=True)
        await update.message.reply_text(f"👑 **Owner Override:** Spawn frequency set to **{new_freq}** messages.\n(Logon ko pareshan mat karna! 😈)")
        return

    # 3. 👮 ADMIN CHECK & LIMITS
    member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
    if member.status not in ['administrator', 'creator']:
        await update.message.reply_text("❌ Sirf Admins ye kar sakte hain.")
        return

    # Admins ke liye Limit (80 se 10000)
    if new_freq < 80:
        await update.message.reply_text("❌ **Too Fast!** Minimum limit **80** hai (Spam rokne ke liye).")
        return
    
    if new_freq > 10000:
        await update.message.reply_text("❌ **Too Slow!** Maximum limit **10,000** hai.")
        return

    # 4. Save
    await user_totals_collection.update_one({'chat_id': chat_id}, {'$set': {'message_frequency': new_freq}}, upsert=True)
    await update.message.reply_text(f"✅ **Success:** Ab har **{new_freq}** messages par character aayega.")

# Dono commands kaam karengi
application.add_handler(CommandHandler("changetime", changetime))
application.add_handler(CommandHandler("ctime", changetime))
