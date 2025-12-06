from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, user_totals_collection

# Aapki Owner ID
OWNER_ID = 7164618867

async def changetime(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    chat_id = str(update.effective_chat.id)
    
    # 1. Input Check (Number diya hai ya nahi)
    if not context.args:
        await update.message.reply_text("⚠️ **Format:** `/ctime [Number]`\nExample: `/ctime 100`", parse_mode='Markdown')
        return
    
    try:
        new_freq = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid number.")
        return

    # 2. OWNER LOGIC (No Limits) 👑
    if user_id == OWNER_ID:
        # Owner kuch bhi set kar sakta hai (1, 5, 10...)
        await user_totals_collection.update_one({'chat_id': chat_id}, {'$set': {'message_frequency': new_freq}}, upsert=True)
        await update.message.reply_text(f"👑 **Owner Override:** Spawn frequency set to **{new_freq}** messages.")
        return

    # 3. ADMIN CHECK 👮
    member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
    if member.status not in ['administrator', 'creator']:
        await update.message.reply_text("❌ Sirf Group Admins ye setting change kar sakte hain.")
        return

    # 4. ADMIN LIMITS (Min 80) 🛡️
    if new_freq < 80:
        await update.message.reply_text("❌ **Too Fast!** Minimum limit **80** messages hai.")
        return
    
    if new_freq > 10000:
        await update.message.reply_text("❌ **Too Slow!** Maximum limit **10,000** hai.")
        return

    # 5. SAVE TO DATABASE 💾
    await user_totals_collection.update_one({'chat_id': chat_id}, {'$set': {'message_frequency': new_freq}}, upsert=True)
    await update.message.reply_text(f"✅ **Success:** Character ab har **{new_freq}** messages ke baad aayega.")

application.add_handler(CommandHandler("ctime", changetime))
