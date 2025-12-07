import importlib
import time
import random
import re
import asyncio
from html import escape 

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, filters

from shivu import collection, top_global_groups_collection, group_user_totals_collection, user_collection, user_totals_collection, application, SUPPORT_CHAT, UPDATE_CHAT, db, LOGGER, shivuu

# --- 🟢 AUTOMATIC MODULE LOADER (MAGIC) ---
from shivu.modules import ALL_MODULES

LOGGER.info("Modules Load ho rahe hain...")
for module_name in ALL_MODULES:
    try:
        importlib.import_module("shivu.modules." + module_name)
        LOGGER.info(f"✅ Loaded: {module_name}")
    except Exception as e:
        LOGGER.error(f"❌ Failed to load {module_name}: {e}")
# -------------------------------------------

locks = {}
message_counters = {}
spam_counters = {}
last_characters = {}
sent_characters = {}
first_correct_guesses = {}
message_counts = {}
last_user = {}
warned_users = {}
spawn_times = {}

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
    spawn_times[chat_id] = time.time()
    
    if chat_id in first_correct_guesses: del first_correct_guesses[chat_id]

    try:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=character['img_url'],
            caption=f"""A New {character['rarity']} Character Appeared...\n/guess Character Name and add in Your Harem""",
            parse_mode='Markdown'
        )
    except Exception as e:
        LOGGER.error(f"Error sending photo: {e}")

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
        
        # TIME & REWARD
        time_taken = "Unknown"
        if chat_id in spawn_times:
            seconds = time.time() - spawn_times[chat_id]
            time_taken = f"{seconds:.2f} seconds"
        
        # COINS (Character Catcher Style)
        COIN_REWARD = 50
        await user_collection.update_one({'id': user_id}, {'$inc': {'balance': COIN_REWARD}})

        # DB Updates
        user = await user_collection.find_one({'id': user_id})
        if user:
            await user_collection.update_one({'id': user_id}, {'$push': {'characters': last_characters[chat_id]}})
        else:
            await user_collection.insert_one({'id': user_id, 'first_name': update.effective_user.first_name, 'characters': [last_characters[chat_id]]})

        await group_user_totals_collection.update_one({'user_id': user_id, 'group_id': chat_id}, {'$inc': {'count': 1}}, upsert=True)
        await top_global_groups_collection.update_one({'group_id': chat_id}, {'$inc': {'count': 1}, '$set': {'group_name': update.effective_chat.title}}, upsert=True)

        keyboard = [[InlineKeyboardButton(f"See Harem", switch_inline_query_current_chat=f"collection.{user_id}")]]
        await update.message.reply_text(
            f'<b><a href="tg://user?id={user_id}">{escape(update.effective_user.first_name)}</a></b>, you\'ve captured a new character! 🎊\n\n'
            f'📛 <b>NAME:</b> {last_characters[chat_id]["name"]} \n'
            f'🌈 <b>ANIME:</b> {last_characters[chat_id]["anime"]} \n'
            f'✨ <b>RARITY:</b> {last_characters[chat_id]["rarity"]}\n\n'
            f'💰 <b>COINS:</b> +{COIN_REWARD}\n'
            f'⏱️ <b>TIME:</b> {time_taken}', 
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
    
    character = next((c for c in user['characters'] if c['id'] == char_id), None)
    if character:
        await user_collection.update_one({'id': user_id}, {'$set': {'favorites': [char_id]}})
        await update.message.reply_text(f'Character added to favorites.')
    else:
        await update.message.reply_text('You do not own this character.')

def main():
    LOGGER.info("Starting Bot...")
    application.add_handler(CommandHandler(["guess", "protecc", "collect", "grab", "hunt"], guess, block=False))
    application.add_handler(CommandHandler("fav", fav, block=False))
    application.add_handler(MessageHandler(filters.ALL, message_counter, block=False))
    
    shivuu.start()
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
