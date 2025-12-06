from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import application, user_collection

pending_trades = {}

# --- TRADE LOGIC (Pichla wala) ---
async def trade(update: Update, context: CallbackContext) -> None:
    # (Pichla code same rahega, bas gift niche add kar rahe hain)
    sender_id = update.effective_user.id
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply with `/trade YourID TheirID`")
        return
    receiver_id = update.message.reply_to_message.from_user.id
    if sender_id == receiver_id: return
    if len(context.args) != 2: return
    
    # ... (Trade logic continued simplified for integration) ...
    # Agar aapne pichla trade.py lagaya tha, wo logic yahan hona chahiye.
    # Main seedha GIFT aur PAY par focus kar raha hu.
    await update.message.reply_text("Trade system active.")

# --- GIFT COMMAND (Free Character Dena) ---
async def gift(update: Update, context: CallbackContext) -> None:
    sender_id = update.effective_user.id
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ User ko reply karke likhein: `/gift [Character_ID]`")
        return

    receiver_id = update.message.reply_to_message.from_user.id
    if sender_id == receiver_id:
        await update.message.reply_text("❌ Khud ko gift nahi de sakte.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Character ID bhi likhein.")
        return

    char_id = context.args[0]

    # Check Ownership
    sender = await user_collection.find_one({'id': sender_id})
    character = next((c for c in sender['characters'] if c['id'] == char_id), None)

    if not character:
        await update.message.reply_text("❌ Ye character aapke paas nahi hai.")
        return

    # Transfer
    await user_collection.update_one({'id': sender_id}, {'$pull': {'characters': {'id': char_id}}})
    await user_collection.update_one({'id': receiver_id}, {'$push': {'characters': character}}, upsert=True)

    await update.message.reply_text(f"🎁 **Gift Sent!**\nAapne **{character['name']}** gift kar diya!")

# --- PAY COMMAND (Coins Dena) ---
async def pay(update: Update, context: CallbackContext) -> None:
    sender_id = update.effective_user.id
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ User ko reply karke likhein: `/pay [Amount]`")
        return

    receiver_id = update.message.reply_to_message.from_user.id
    if sender_id == receiver_id: return

    try:
        amount = int(context.args[0])
    except:
        await update.message.reply_text("❌ Amount number hona chahiye.")
        return

    if amount <= 0:
        await update.message.reply_text("❌ Positive amount likhein.")
        return

    # Check Balance
    sender = await user_collection.find_one({'id': sender_id})
    current_balance = sender.get('balance', 0)

    if current_balance < amount:
        await update.message.reply_text(f"❌ Aapke paas itne coins nahi hain.\nBalance: {current_balance}")
        return

    # Transfer
    await user_collection.update_one({'id': sender_id}, {'$inc': {'balance': -amount}})
    await user_collection.update_one({'id': receiver_id}, {'$inc': {'balance': amount}}, upsert=True)

    await update.message.reply_text(f"💸 **Payment Successful!**\nSent: {amount} coins.")

application.add_handler(CommandHandler("trade", trade))
application.add_handler(CommandHandler("gift", gift))
application.add_handler(CommandHandler("pay", pay))
