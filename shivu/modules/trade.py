from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import application, user_collection

# Temporary storage for trade requests
pending_trades = {}

async def trade(update: Update, context: CallbackContext) -> None:
    sender_id = update.effective_user.id
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ **Format:** Reply to user with `/trade [Your_Char_ID] [Their_Char_ID]`", parse_mode='Markdown')
        return

    receiver_id = update.message.reply_to_message.from_user.id
    if sender_id == receiver_id:
        await update.message.reply_text("❌ Khud se trade nahi kar sakte.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("⚠️ **Format:** `/trade [Your_ID] [Their_ID]`")
        return

    sender_char_id = context.args[0]
    receiver_char_id = context.args[1]

    # Check Ownership
    sender = await user_collection.find_one({'id': sender_id})
    receiver = await user_collection.find_one({'id': receiver_id})

    sender_char = next((c for c in sender['characters'] if c['id'] == sender_char_id), None)
    receiver_char = next((c for c in receiver['characters'] if c['id'] == receiver_char_id), None)

    if not sender_char:
        await update.message.reply_text(f"❌ Aapke paas Character ID `{sender_char_id}` nahi hai.")
        return
    if not receiver_char:
        await update.message.reply_text(f"❌ Unke paas Character ID `{receiver_char_id}` nahi hai.")
        return

    # Trade Request Store karein
    trade_id = f"{sender_id}_{receiver_id}"
    pending_trades[trade_id] = {
        'sender': sender_id,
        'receiver': receiver_id,
        's_char': sender_char,
        'r_char': receiver_char
    }

    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data=f"trade_yes:{trade_id}"),
         InlineKeyboardButton("❌ Cancel", callback_data=f"trade_no:{trade_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"🤝 **Trade Request!**\n\n"
        f"👤 **{update.effective_user.first_name}** offers:\n"
        f"🧸 {sender_char['name']} ({sender_char['rarity']})\n\n"
        f"👤 **{update.message.reply_to_message.from_user.first_name}** gives:\n"
        f"🧸 {receiver_char['name']} ({receiver_char['rarity']})\n\n"
        f"⚠️ **{update.message.reply_to_message.from_user.first_name}**, do you accept?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def trade_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split(':')
    action = data[0]
    trade_id = data[1]

    if trade_id not in pending_trades:
        await query.answer("❌ Trade expired or invalid.", show_alert=True)
        await query.message.delete()
        return

    trade_data = pending_trades[trade_id]
    
    # Sirf Receiver hi Accept/Decline kar sakta hai
    if query.from_user.id != trade_data['receiver']:
        await query.answer("❌ Ye aapke liye nahi hai!", show_alert=True)
        return

    if action == "trade_no":
        del pending_trades[trade_id]
        await query.message.edit_text("❌ Trade Declined.")
        return

    if action == "trade_yes":
        # Swap Logic
        sender_id = trade_data['sender']
        receiver_id = trade_data['receiver']
        s_char = trade_data['s_char']
        r_char = trade_data['r_char']

        # Remove from Owners
        await user_collection.update_one({'id': sender_id}, {'$pull': {'characters': {'id': s_char['id']}}})
        await user_collection.update_one({'id': receiver_id}, {'$pull': {'characters': {'id': r_char['id']}}})

        # Add to New Owners
        await user_collection.update_one({'id': sender_id}, {'$push': {'characters': r_char}})
        await user_collection.update_one({'id': receiver_id}, {'$push': {'characters': s_char}})

        del pending_trades[trade_id]
        await query.message.edit_text("✅ **Trade Successful!** 🎉", parse_mode='Markdown')

application.add_handler(CommandHandler("trade", trade))
application.add_handler(CallbackQueryHandler(trade_callback, pattern="^trade_"))
