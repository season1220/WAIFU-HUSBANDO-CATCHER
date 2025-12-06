import importlib
import time
import random
import re
import asyncio
from html import escape 

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, filters

from shivu import collection, top_global_groups_collection, group_user_totals_collection, user_collection, user_totals_collection, application, SUPPORT_CHAT, UPDATE_CHAT, db, LOGGER, shivuu

# --- MODULES LOADING ---
# Dhyan rahe: Ye files (changetime.py, extras.py, settings.py) modules folder me honi chahiye
from shivu.modules import upload, manage, start, help, harem, leaderboard, trade, extras, settings, changetime
# -----------------------

locks = {}
message_counters = {}
spam_counters = {}
last_characters = {}
sent_characters = {}
first_correct_guesses = {}
message_counts = {}
last_user = {}
warned_users = {}
spawn_times = {} # Time note karne ke liye

# --- MAIN SPAWNING ENGINE ---
async def message_counter(update: Update, context: CallbackContext) -> None:
    chat_id = str(update.effective_chat.id)
    user_id = update.effective_user.id
    
    if chat_id not in locks: locks[chat_id] = asyncio.Lock()
    async with locks[chat_id]:
        
        # Frequency Check
        chat_freq = await user_totals_collection.find_one({'chat_id': chat_id})
        msg_freq = chat_freq.get('message_frequency', 100) if chat_freq else 100
        
        # Spam Logic
        if chat_id in last_user and last_user[chat_id]['user_id'] == user_id:
            last_user[chat_id]['count'] += 1
            if last_user[chat_id]['count'] >= 10:
                if user_id not in warned_users or time.time() - warned_users[user_id] > 600:
                    warned_users[user_id] = time.time()
                return
        else:
            last_user[chat_id] = {'user_id': user_id, 'count': 1}

        # Counting
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
    
    # Time Note kiya
    spawn_times[chat_id] = time.time()

    if chat_id in first_correct_guesses: del first_correct_guesses[chat_id]

    try:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=character['img_url'],
            caption=f"""A New {character['rarity']} Character Appeared...\n/guess Character Name and add in Your Harem""",
            parse_mode='Markdown'
        )
    except Exception as
