from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler
from shivu import application

async def help(update: Update, context: CallbackContext):
    help_text = """
<b>⚙️ Help Menu:</b>

<b>🎮 Game Commands:</b>
/guess - Guess the character
/fav - Add character to favorites
/trade - Trade characters with users
/gift - Gift characters
/collection - View your collection
/balance - Check balance
/top - Check leaderboard
/harem - View your Harem

<b>💎 Rarity List:</b>
1. 🥉 Low
2. 🥈 Medium
3. 🥇 High
4. 🔮 Special Edition
5. 💠 Elite Edition
6. 🦄 Legendary
7. 💌 Valentine
8. 🧛🏻 Halloween
9. 🥶 Winter
10. 🍹 Summer
11. ⚜️ Royal
12. 💍 Luxury Edition
"""
    # Agar message hai (command se aaya)
    if update.message:
        await update.message.reply_text(help_text, parse_mode='HTML')
    # Agar callback hai (button se aaya)
    elif update.callback_query:
        await update.callback_query.edit_message_caption(caption=help_text, parse_mode='HTML')

async def help_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    help_text = """
<b>⚙️ Help Menu:</b>

<b>🎮 Game Commands:</b>
/guess - Guess the character
/fav - Add character to favorites
/trade - Trade characters with users
/gift - Gift characters
/collection - View your collection
/balance - Check balance
/top - Check leaderboard
/harem - View your Harem

<b>💎 Rarity List:</b>
1. 🥉 Low
2. 🥈 Medium
3. 🥇 High
4. 🔮 Special Edition
5. 💠 Elite Edition
6. 🦄 Legendary
7. 💌 Valentine
8. 🧛🏻 Halloween
9. 🥶 Winter
10. 🍹 Summer
11. ⚜️ Royal
12. 💍 Luxury Edition
"""
    await query.edit_message_caption(caption=help_text, parse_mode='HTML')

# Handlers add karna zaroori hai
application.add_handler(CallbackQueryHandler(help_callback, pattern='help'))
