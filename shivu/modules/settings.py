from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, user_collection, group_user_totals_collection

async def hclaim(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("⚠️ ID likhein: `/hclaim [ID]`")
        return
    
    char_id = context.args[0]
    user = await user_collection.find_one({'id': user_id})
    if not user: return

    # Check agar user ke paas character hai
    has_char = next((c for c in user.get('characters', []) if c['id'] == char_id), None)
    
    if not has_char:
        await update.message.reply_text("❌ Ye character aapke paas nahi hai.")
        return

    await user_collection.update_one({'id': user_id}, {'$set': {'hclaim': char_id}})
    await update.message.reply_text(f"💍 **Success!**\nAapne **{has_char['name']}** ko apna Main Partner chuna hai! ❤️", parse_mode='Markdown')

async def hmode(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Admin Check
    member = await context.bot.get_chat_member(chat_id, user_id)
    if member.status not in ['administrator', 'creator']:
        await update.message.reply_text("❌ Sirf Admins ye kar sakte hain.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Use: `/hmode on` (Only Admins) or `/hmode off` (Everyone)")
        return
    
    mode = context.args[0].lower()
    
    if mode == "on":
        await group_user_totals_collection.update_one({'group_id': chat_id}, {'$set': {'only_admins': True}}, upsert=True)
        await update.message.reply_text("🔒 **Harem Mode ON:** Sirf Admins guess kar sakte hain.")
    elif mode == "off":
        await group_user_totals_collection.update_one({'group_id': chat_id}, {'$set': {'only_admins': False}}, upsert=True)
        await update.message.reply_text("🔓 **Harem Mode OFF:** Sab log guess kar sakte hain.")
    else:
        await update.message.reply_text("⚠️ Use: `on` ya `off`")

application.add_handler(CommandHandler("hclaim", hclaim))
application.add_handler(CommandHandler("hmode", hmode))
