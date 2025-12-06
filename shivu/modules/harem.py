from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import application, user_collection
import math

async def harem(update: Update, context: CallbackContext, page=0) -> None:
    user_id = update.effective_user.id
    
    # Check agar user ne kisi aur ka harem dekhna chaha (Reply karke)
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
        user_name = update.message.reply_to_message.from_user.first_name
    elif context.args:
        try:
            user_id = int(context.args[0])
            user_name = "User"
        except:
            await update.message.reply_text("❌ Valid ID dalein.")
            return
    else:
        user_name = update.effective_user.first_name

    user = await user_collection.find_one({'id': user_id})
    if not user:
        await update.message.reply_text(f"{user_name} ne abhi tak koi character nahi pakda.")
        return

    characters = user.get('characters', [])
    
    # Sorting (Rarity ke hisaab se)
    # Aap chahein to isse hata sakte hain agar simple rakhna hai
    rarity_value = {
        "💍 Luxury Edition": 12, "⚜️ Royal": 11, "🍹 Summer": 10, "🥶 Winter": 9,
        "🧛🏻 Halloween": 8, "💌 Valentine": 7, "🦄 Legendary": 6, "💠 Elite Edition": 5,
        "🔮 Special Edition": 4, "🥇 High": 3, "🥈 Medium": 2, "🥉 Low": 1
    }
    characters = sorted(characters, key=lambda x: rarity_value.get(x['rarity'], 0), reverse=True)

    if not characters:
        await update.message.reply_text(f"{user_name} ke paas koi characters nahi hain.")
        return

    # Pagination Logic (15 Characters per page)
    CHUNK_SIZE = 15
    total_pages = math.ceil(len(characters) / CHUNK_SIZE)
    
    # Callback data se page number nikalna
    if isinstance(page, str):
        page = int(page)
    
    if page < 0 or page >= total_pages:
        page = 0

    current_chunk = characters[page * CHUNK_SIZE:(page + 1) * CHUNK_SIZE]
    
    msg = f"<b>🍃 {user_name}'s Harem ({len(characters)})</b>\n\n"
    
    for char in current_chunk:
        msg += f"🆔 <b>{char['id']}</b> : {char['rarity'][0]} {char['name']} ({char['anime']})\n"

    # Buttons for Next/Back
    keyboard = []
    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"harem:{user_id}:{page-1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"harem:{user_id}:{page+1}"))
        keyboard.append(nav_buttons)
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(msg, parse_mode='HTML', reply_markup=reply_markup)
    else:
        # Edit message for button click
        await update.callback_query.edit_message_text(msg, parse_mode='HTML', reply_markup=reply_markup)

async def harem_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split(':')
    user_id = int(data[1])
    page = int(data[2])
    
    # Check if correct user clicked
    if query.from_user.id != user_id and query.from_user.id != update.effective_chat.id:
        await query.answer("❌ Ye aapka harem nahi hai!", show_alert=True)
        return

    await harem(update, context, page)

application.add_handler(CommandHandler(["harem", "collection"], harem))
application.add_handler(CallbackQueryHandler(harem_callback, pattern="^harem"))
