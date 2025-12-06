from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, collection

# --- OWNER SETTINGS ---
sudo_users = [7164618867]
# ----------------------

async def rdelete(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if user_id not in sudo_users:
        await update.message.reply_text("❌ Only the Owner can use this command.")
        return

    try:
        args = context.args
        if len(args) != 1:
            await update.message.reply_text("⚠️ Usage: `/rdelete <Character-ID>`")
            return
        char_id = args[0]
        result = await collection.delete_one({'id': char_id})
        if result.deleted_count > 0:
            await update.message.reply_text(f"✅ Character ID <b>{char_id}</b> deleted successfully.", parse_mode='HTML')
        else:
            await update.message.reply_text(f"❌ Character ID <b>{char_id}</b> not found in database.", parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def rupdate(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if user_id not in sudo_users:
        await update.message.reply_text("❌ Only the Owner can use this command.")
        return

    try:
        args = context.args
        if len(args) < 3:
            await update.message.reply_text(
                "⚠️ Usage: `/rupdate <ID> <Field> <New Value>`\n\n"
                "<b>Valid Fields:</b> name, anime, rarity, img_url",
                parse_mode='HTML'
            )
            return
        
        char_id = args[0]
        field = args[1].lower()
        new_value = " ".join(args[2:])
        
        if field in ['name', 'anime']:
            new_value = new_value.replace('-', ' ').title()

        result = await collection.update_one({'id': char_id}, {'$set': {field: new_value}})
        if result.modified_count > 0:
            await update.message.reply_text(f"✅ Updated <b>{field}</b> for ID <b>{char_id}</b>.\nNew Value: {new_value}", parse_mode='HTML')
        else:
            await update.message.reply_text(f"⚠️ No changes made. Check if ID exists or value is same.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

application.add_handler(CommandHandler("rdelete", rdelete, block=False))
application.add_handler(CommandHandler("rupdate", rupdate, block=False))
