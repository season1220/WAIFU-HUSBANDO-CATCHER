from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, db

# Database Collection for Sudo Users
sudo_collection = db["sudo_users_list"]

# Aapki Owner ID (Isse replace karein agar alag hai)
OWNER_ID = 7164618867

async def addsudo(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    
    # Sirf OWNER hi naya admin bana sakta hai
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ Sirf Owner hi naye Admins jod sakta hai.")
        return

    # Check karein ki reply kiya hai ya ID di hai
    if not update.message.reply_to_message and not context.args:
        await update.message.reply_text("⚠️ Kisi user ke message par **Reply** karein ya ID likhein.\nExample: `/addsudo 12345678`")
        return

    if update.message.reply_to_message:
        target_user_id = update.message.reply_to_message.from_user.id
        target_name = update.message.reply_to_message.from_user.first_name
    else:
        try:
            target_user_id = int(context.args[0])
            target_name = str(target_user_id)
        except ValueError:
            await update.message.reply_text("❌ ID number honi chahiye.")
            return

    # Database mein save karein
    existing = await sudo_collection.find_one({'user_id': target_user_id})
    if existing:
        await update.message.reply_text(f"⚠️ {target_name} pehle se hi Admin hai.")
    else:
        await sudo_collection.insert_one({'user_id': target_user_id, 'name': target_name})
        await update.message.reply_text(f"✅ **{target_name}** ko Upload Power de di gayi hai! 🎉")

async def rmsudo(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ Sirf Owner hi power hata sakta hai.")
        return

    if not update.message.reply_to_message and not context.args:
        await update.message.reply_text("⚠️ Reply karein ya ID dein hataane ke liye.")
        return

    if update.message.reply_to_message:
        target_user_id = update.message.reply_to_message.from_user.id
    else:
        try:
            target_user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ ID number honi chahiye.")
            return

    result = await sudo_collection.delete_one({'user_id': target_user_id})
    if result.deleted_count > 0:
        await update.message.reply_text(f"✅ User ki Upload Power cheen li gayi hai. 🗑️")
    else:
        await update.message.reply_text("⚠️ Ye user list mein nahi mila.")

async def sudolist(update: Update, context: CallbackContext) -> None:
    sudo_users = await sudo_collection.find({}).to_list(length=None)
    
    if not sudo_users:
        await update.message.reply_text("📂 Abhi koi extra Admin nahi hai.")
        return

    msg = "👑 **Uploaders List:**\n\n"
    for user in sudo_users:
        msg += f"👤 `{user['user_id']}` - {user.get('name', 'Unknown')}\n"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

# Handlers
application.add_handler(CommandHandler("addsudo", addsudo))
application.add_handler(CommandHandler("rmsudo", rmsudo))
application.add_handler(CommandHandler("sudolist", sudolist))
