import importlib
import time
import random
import re
import asyncio
from html import escape 

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, filters

# Ab import karte waqt error nahi aayega kyunki __init__ clean hai
from shivu import collection, top_global_groups_collection, group_user_totals_collection, user_collection, user_totals_collection
from shivu import application, SUPPORT_CHAT, UPDATE_CHAT, db, LOGGER, shivuu

# --- MODULES LOAD ---
# Yahan hum modules load karenge
from shivu.modules import upload, manage, start, help
# --------------------

# --- GLOBAL VARS ---
locks = {}
message_counters = {}
spam_counters = {}
last_characters = {}
sent_characters = {}
first_correct_guesses = {}
message_counts = {}
last_user = {}
warned_users = {}

async def message_counter(update: Update, context: CallbackContext) -> None:
    chat_id = str(update.effective_chat.id)
    user_id = update.effective_user.id
    if chat_id not in locks: locks[chat_id] = asyncio.Lock()
    async with locks[chat_id]:
        chat_freq = await user_totals_collection.find_one({'chat_id': chat_id})
        msg_freq = chat_freq.get('message_frequency', 100) if chat_freq else 100
        
        if chat_id in last_user and last_user[chat_id]['user_id'] == user_id:
            last_user[chat_id]['count'] += 1
            if last_user[chat_id]['count'] >= 10:
                if user_id not in warned_users or time.time() - warned_users[user_id] > 600:
                    await update.message.reply_text(f"⚠️ Don't Spam... Ignored for 10 mins.")
                    warned_users[user_id] = time.time()
                return
        else:
            last_user[chat_id] = {'user_id': user_id, 'count': 1}

        message_counts[chat_id] = message_counts.get(chat_id, 0) + 1
        if message_counts[chat_id] % msg_freq == 0:
            await send_image(update, context)
            message_counts[chat_id] = 0

async def send_image(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    all_chars = list(await collection.find({}).to_list(length=None))
    if not all_chars: return
    
    if chat_id not in sent_characters: sent_characters[chat_id] = []
    if len(sent_characters[chat_id]) == len(all_chars): sent_characters[chat_id] = []

    character = random.choice([c for c in all_chars if c['id'] not in sent_characters[chat_id]])
    sent_characters[chat_id].append(character['id'])
    last_characters[chat_id] = character
    if chat_id in first_correct_guesses: del first_correct_guesses[chat_id]

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption=f"""A New {character['rarity']} Character Appeared...\n/guess Character Name and add in Your Harem""",
        parse_mode='Markdown'
    )

async def guess(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if chat_id not in last_characters: return
    if chat_id in first_correct_guesses:
        await update.message.reply_text(f'❌️ Already Guessed...')
        return

    guess = ' '.join(context.args).lower() if context.args else ''
    name_parts = last_characters[chat_id]['name'].lower().split()
    
    if sorted(name_parts) == sorted(guess.split()) or any(part == guess for part in name_parts):
        first_correct_guesses[chat_id] = user_id
        
        user = await user_collection.find_one({'id': user_id})
        if user:
            await user_collection.update_one({'id': user_id}, {'$push': {'characters': last_characters[chat_id]}})
        else:
            await user_collection.insert_one({'id': user_id, 'first_name': update.effective_user.first_name, 'characters': [last_characters[chat_id]]})

        keyboard = [[InlineKeyboardButton(f"See Harem", switch_inline_query_current_chat=f"collection.{user_id}")]]
        await update.message.reply_text(
            f'<b><a href="tg://user?id={user_id}">{escape(update.effective_user.first_name)}</a></b> You Guessed a New Character ✅️ \n\n'
            f'𝗡𝗔𝗠𝗘: <b>{last_characters[chat_id]["name"]}</b> \n'
            f'𝗔𝗡𝗜𝗠𝗘: <b>{last_characters[chat_id]["anime"]}</b> \n'
            f'𝗥𝗔𝗜𝗥𝗧𝗬: <b>{last_characters[chat_id]["rarity"]}</b>', 
            parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text('Please Write Correct Character Name... ❌️')

async def fav(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if not context.args: return
    char_id = context.args[0]
    user = await user_collection.find_one({'id': user_id})
    if not user: return
    
    # Check if user has character
    has_char = next((c for c in user['characters'] if c['id'] == char_id), None)
    if has_char:
        await user_collection.update_one({'id': user_id}, {'$set': {'favorites': [char_id]}})
        await update.message.reply_text(f'Character added to favorites.')
    else:
        await update.message.reply_text('You do not own this character.')

def main():
    LOGGER.info("Starting Bot...")
    application.add_handler(CommandHandler(["guess", "protecc", "collect", "grab", "hunt"], guess, block=False))
    application.add_handler(CommandHandler("fav", fav, block=False))
    application.add_handler(MessageHandler(filters.ALL, message_counter, block=False))
    
    # Start Shivuu (Pyrogram) in background
    shivuu.start()
    
    # Start Application (PTB)
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
