from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, collection, db
from shivu.config import Config

# Owner check logic
sudo_users = [int(user) for user in Config.sudo_users] if isinstance(Config.sudo_users, (list, tuple)) else [int(Config.sudo_users)]

async def rdelete(update: Update, context: CallbackContext) -> None:
    # Sirf Owner/Sudo use kar sakte hain
    user_id = update.effective_user.id
    if user_id not in sudo_users and str(user_id) != Config.OWNER_ID:
        await update.message.reply_text("❌ Sirf Owner hi Delete kar sakta hai.")
        return

    try:
        args = context.args
        if len(args) != 1:
            await update.message.reply_text("⚠️ Galat tareeka! Use karein:\n`/rdelete Character-ID`")
            return

        char_id = args[0]
        
        # Database se delete karna
        result = await collection.delete_one({'id': char_id})

        if result.deleted_count > 0:
            await update.message.reply_text(f"✅ Character ID <b>{char_id}</b> safalta purvak DELETE kar diya gaya!", parse_mode='HTML')
        else:
            await update.message.reply_text(f"❌ Ye ID <b>{char_id}</b> database mein nahi mili.", parse_mode='HTML')

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def rupdate(update: Update, context: CallbackContext) -> None:
    # Sirf Owner/Sudo use kar sakte hain
    user_id = update.effective_user.id
    if user_id not in sudo_users and str(user_id) != Config.OWNER_ID:
        await update.message.reply_text("❌ Sirf Owner hi Update kar sakta hai.")
        return

    try:
        args = context.args
        # Format: /rupdate ID field New-Value
        if len(args) < 3:
            await update.message.reply_text(
                "⚠️ Galat tareeka! Use karein:\n"
                "`/rupdate [ID] [field] [New Value]`\n\n"
                "<b>Fields jo badal sakte hain:</b>\n"
                "• name (Character ka naam)\n"
                "• anime (Anime ka naam)\n"
                "• rarity (Rarity)\n"
                "• img_url (Photo/Video Link)",
                parse_mode='HTML'
            )
            return

        char_id = args[0]
        field = args[1].lower()
        new_value = " ".join(args[2:])

        # Field check
        valid_fields = ['name', 'anime', 'rarity', 'img_url']
        if field not in valid_fields:
            await update.message.reply_text(f"❌ Galat field! Sirf inhe badal sakte hain: {', '.join(valid_fields)}")
            return

        # Formatting (Naam ko Title case banana)
        if field in ['name', 'anime']:
            new_value = new_value.replace('-', ' ').title()

        # Database Update
        result = await collection.update_one({'id': char_id}, {'$set': {field: new_value}})

        if result.modified_count > 0:
            await update.message.reply_text(f"✅ ID <b>{char_id}</b> ka <b>{field}</b> update ho gaya:\n\n👉 <b>{new_value}</b>", parse_mode='HTML')
        elif result.matched_count > 0:
            await update.message.reply_text(f"⚠️ Ye value pehle se yahi thi, kuch change nahi hua.")
        else:
            await update.message.reply_text(f"❌ Ye ID <b>{char_id}</b> mili nahi.", parse_mode='HTML')

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# Commands Jodna
application.add_handler(CommandHandler("rdelete", rdelete, block=False))
application.add_handler(CommandHandler("rupdate", rupdate, block=False))
