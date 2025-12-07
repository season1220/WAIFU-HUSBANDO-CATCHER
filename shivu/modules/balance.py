import time
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, user_collection

async def balance(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    user = await user_collection.find_one({'id': user_id})
    
    bal = user.get('balance', 0) if user else 0
    await update.message.reply_text(f"💰 **Aapka Balance:** {bal} Coins", parse_mode='Markdown')

async def daily(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    user = await user_collection.find_one({'id': user_id})
    
    if not user:
        await update.message.reply_text("Pehle koi character pakdo!")
        return

    # Time Check (24 Hours)
    last_daily = user.get('last_daily', 0)
    if time.time() - last_daily < 86400:
        remaining = int(86400 - (time.time() - last_daily))
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        await update.message.reply_text(f"❌ **Wait karo!** Agla reward {hours}h {minutes}m baad milega.")
        return

    # Reward
    reward = 200
    await user_collection.update_one({'id': user_id}, {
        '$inc': {'balance': reward},
        '$set': {'last_daily': time.time()}
    })
    
    await update.message.reply_text(f"🎁 **Daily Reward Claimed!**\nAapko mile **{reward} Coins**! 🎉")

async def pay(update: Update, context: CallbackContext) -> None:
    sender_id = update.effective_user.id
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply karein: `/pay [Amount]`")
        return

    receiver_id = update.message.reply_to_message.from_user.id
    if sender_id == receiver_id: return

    try:
        amount = int(context.args[0])
    except:
        await update.message.reply_text("❌ Amount number hona chahiye.")
        return

    if amount <= 0: return

    sender = await user_collection.find_one({'id': sender_id})
    if not sender or sender.get('balance', 0) < amount:
        await update.message.reply_text("❌ Gareeb ho aap! Itne paise nahi hain.")
        return

    await user_collection.update_one({'id': sender_id}, {'$inc': {'balance': -amount}})
    await user_collection.update_one({'id': receiver_id}, {'$inc': {'balance': amount}}, upsert=True)
    
    await update.message.reply_text(f"💸 **Transfer Successful!**\nSent: {amount} coins.")

application.add_handler(CommandHandler("balance", balance))
application.add_handler(CommandHandler("daily", daily))
application.add_handler(CommandHandler("pay", pay))
