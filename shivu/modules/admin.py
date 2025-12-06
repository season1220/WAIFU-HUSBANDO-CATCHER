import asyncio
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, db, user_collection

# --- SETTINGS ---
OWNER_ID = 7164618867
sudo_collection = db["sudo_users_list"]
# ----------------

async def addsudo(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Sirf Owner hi ye kar sakta hai.")
        return
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user.id
        name = update.message.reply_to_message.from_user.first_name
    else:
        try:
            target = int(context.args[0])
            name = "User"
        except:
            await update.message.reply_text("⚠️ Reply karein ya ID dein.")
            return
    
    await sudo_collection.insert_one({'user_id': target, 'name': name})
    await update.message.reply_text(f"✅ {name} ab Admin hai.")

async def rmsudo(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Sirf Owner hi ye kar sakta hai.")
        return
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user.id
    else:
        try:
            target = int(context.args[0])
        except:
            await update.message.reply_text("⚠️ Reply karein ya ID dein.")
            return
    
    await sudo_collection.delete_one({'user_id': target})
    await update.message.reply_text(f"✅ Power hata di gayi.")

async def sudolist(update: Update, context: CallbackContext) -> None:
    users = await sudo_collection.find({}).to_list(length=None)
    msg = "👑 **Admins:**\n"
    for u in users: msg += f"👤 `{u['user_id']}`\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

# --- NEW BROADCAST COMMAND ---
async def bcast(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Sirf Owner.")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Us message par reply karein jo sabko bhejna hai.")
        return

    msg_to_send = update.message.reply_to_message
    users = await user_collection.find({}).to_list(length=None)
    
    sent = 0
    failed = 0
    status_msg = await update.message.reply_text(f"📢 Broadcast shuru... Total Users: {len(users)}")

    for user in users:
        try:
            await msg_to_send.copy(chat_id=user['id'])
            sent += 1
        except:
            failed += 1
        
        # Har 100 users ke baad thoda wait karein taaki bot block na ho
        if sent % 100 == 0:
            await asyncio.sleep(1)

    await status_msg.edit_text(f"✅ **Broadcast Complete!**\n📨 Sent: {sent}\n❌ Failed: {failed}")

application.add_handler(CommandHandler("addsudo", addsudo))
application.add_handler(CommandHandler("rmsudo", rmsudo))
application.add_handler(CommandHandler("sudolist", sudolist))
application.add_handler(CommandHandler("bcast", bcast))
