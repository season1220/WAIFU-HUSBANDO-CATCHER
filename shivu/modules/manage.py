from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, collection, db

# --- SETTINGS ---
OWNER_ID = 7164618867
sudo_collection = db["sudo_users_list"]
# ----------------

async def check_perms(user_id):
    if user_id == OWNER_ID:
        return True
    is_sudo = await sudo_collection.find_one({'user_id': user_id})
    return bool(is_sudo)

async def rdelete(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if not await check_perms(user_id):
        await update.message.reply_text("❌ Aapke paas delete karne ki power nahi hai.")
        return

    try:
        args = context.args
        if len(args) != 1:
            await update.message.reply_text("⚠️ Use: `/rdelete ID`")
            return
        char_id = args[0]
        result = await collection.delete_one({'id': char_id})
        if result.deleted_count > 0:
            await update.message.reply_text(f"✅ ID {char_id} Deleted.")
        else:
            await update.message.reply_text(f"❌ ID {char_id} not found.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def rupdate(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if not await check_perms(user_id):
        await update.message.reply_text("❌ Aapke paas update karne ki power nahi hai.")
        return

    try:
        args = context.args
        if len(args) < 3:
            await update.message.reply_text("⚠️ Use: `/rupdate ID field Value`")
            return
        char_id = args[0]
        field = args[1].lower()
        new_value = " ".join(args[2:])
        
        if field in ['name', 'anime']:
            new_value = new_value.replace('-', ' ').title()

        result = await collection.update_one({'id': char_id}, {'$set': {field: new_value}})
        if result.modified_count > 0:
            await update.message.reply_text(f"✅ Updated {field} for ID {char_id}.")
        else:
            await update.message.reply_text(f"⚠️ No changes made.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

application.add_handler(CommandHandler("rdelete", rdelete, block=False))
application.add_handler(CommandHandler("rupdate", rupdate, block=False))
