import logging
import asyncio
import random
import time
import math
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from motor.motor_asyncio import AsyncIOMotorClient

# --- 1. CONFIGURATION ---
TOKEN = "8578752843:AAHNWJAKLmZ_pc9tHPgyhUtnjOKxtXD6mM8"
MONGO_URL = "mongodb+srv://seasonking:season_123@cluster0.e5zbzap.mongodb.net/?appName=Cluster0"
OWNER_ID = 7164618867
CHANNEL_ID = -1003352372209 
PHOTO_URL = "https://telegra.ph/file/b925c3985f0f325e62e17.jpg"

# --- 2. DATABASE ---
client = AsyncIOMotorClient(MONGO_URL)
db = client['MyNewBot']
col_chars = db['characters']
col_users = db['users']

# --- 3. LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 4. VARIABLES ---
message_counts = {}
last_spawn = {} 

# --- HELPER: Rarity Emoji ---
def get_rarity_emoji(rarity):
    r = rarity.lower()
    if "luxury" in r: return "💍"
    if "royal" in r: return "⚜️"
    if "summer" in r: return "🍹"
    if "winter" in r: return "🥶"
    if "halloween" in r: return "🧛🏻"
    if "valentine" in r: return "💌"
    if "legendary" in r: return "🦄"
    if "elite" in r: return "💠"
    if "special" in r: return "🔮"
    if "high" in r: return "🥇"
    if "medium" in r: return "🥈"
    if "low" in r: return "🥉"
    return "✨"

# --- 5. COMMANDS ---

async def start(update: Update, context: CallbackContext):
    caption = (
        "👋 **Namaste! Main Season Waifu hu!**\n\n"
        "Same to Same Nobita Style!\n"
        "Add me to your group to start."
    )
    keyboard = [[InlineKeyboardButton("➕ Add Me to Group", url="http://t.me/seasonwaifuBot?startgroup=new")]]
    await update.message.reply_photo(photo=PHOTO_URL, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))

# --- UPLOAD ---
async def rupload(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID: return
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.message.reply_text("⚠️ Reply to a photo!")
        return

    try:
        args = context.args
        if len(args) < 3:
            await update.message.reply_text("⚠️ `/rupload Name Anime Number`")
            return

        name = args[0].replace('-', ' ').title()
        anime = args[1].replace('-', ' ').title()
        
        # Rarity Map
        rarity_map = {1:"🥉 Low", 2:"🥈 Medium", 3:"🥇 High", 4:"🔮 Special Edition", 5:"💠 Elite Edition", 6:"🦄 Legendary", 7:"💌 Valentine", 8:"🧛🏻 Halloween", 9:"🥶 Winter", 10:"🍹 Summer", 11:"⚜️ Royal", 12:"💍 Luxury Edition"}
        
        try:
            r_num = int(args[2])
            rarity = rarity_map.get(r_num, "✨ Special")
        except:
            rarity = "✨ Special"

        file_id = update.message.reply_to_message.photo[-1].file_id
        char_id = str(random.randint(1000, 9999))

        char_data = {'img_url': file_id, 'name': name, 'anime': anime, 'rarity': rarity, 'id': char_id}
        await col_chars.insert_one(char_data)
        
        await update.message.reply_text(f"✅ Uploaded: **{name}**")
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=file_id, caption=f"🆕 New Character: {name}\n🌈 Anime: {anime}\n✨ Rarity: {rarity}\n🆔 ID: {char_id}")

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

# --- ADVANCED HAREM SYSTEM ---
async def harem(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    # Check agar kisi aur ka harem dekhna hai
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
    
    user = await col_users.find_one({'id': user_id})
    if not user or not user.get('characters'):
        await update.message.reply_text("❌ Collection khali hai.")
        return

    # Grouping Logic
    characters = user['characters']
    anime_map = defaultdict(list)
    
    for char in characters:
        anime_map[char['anime']].append(char)
    
    sorted_animes = sorted(anime_map.keys())
    
    # Page Logic
    page = 0
    await send_harem_page(update, context, sorted_animes, anime_map, page, user_id, user.get('name', 'User'))

async def send_harem_page(update, context, sorted_animes, anime_map, page, user_id, user_name):
    CHUNK_SIZE = 5 # Ek page par kitne anime dikhenge
    total_pages = math.ceil(len(sorted_animes) / CHUNK_SIZE)
    
    if page < 0: page = 0
    if page >= total_pages: page = total_pages - 1

    current_animes = sorted_animes[page * CHUNK_SIZE : (page + 1) * CHUNK_SIZE]
    
    msg = f"<b>🍃 {user_name}'s Harem</b>\n"
    msg += f"Total Characters: {sum(len(v) for v in anime_map.values())}\n\n"

    for anime in current_animes:
        chars = anime_map[anime]
        # Count unique chars (agar duplicate allow karna hai toh alag logic lagega)
        msg += f"<b>{anime}</b> {len(chars)}\n"
        
        for char in chars:
            emoji = get_rarity_emoji(char['rarity'])
            # Format: Emoji [ID] Name x1
            msg += f"♦️ {emoji} <code>{char['id']}</code> {char['name']} ×1\n"
        msg += "\n"

    # Buttons
    buttons = []
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"h_prev_{user_id}_{page}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("➡️", callback_data=f"h_next_{user_id}_{page}"))
    
    buttons.append(nav_row)
    buttons.append([
        InlineKeyboardButton(f"Collection ({sum(len(v) for v in anime_map.values())})", callback_data="dummy"),
        InlineKeyboardButton("❤️ AMV (0)", callback_data="dummy")
    ])
    
    reply_markup = InlineKeyboardMarkup(buttons)

    if update.callback_query:
        await update.callback_query.edit_message_text(msg, parse_mode='HTML', reply_markup=reply_markup)
    else:
        await update.message.reply_text(msg, parse_mode='HTML', reply_markup=reply_markup)

# --- CALLBACK HANDLER (Page Turn) ---
async def harem_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split('_')
    
    if data[0] == "h":
        action = data[1]
        user_id = int(data[2])
        current_page = int(data[3])

        if query.from_user.id != user_id:
            await query.answer("❌ Ye aapka harem nahi hai!", show_alert=True)
            return

        # Fetch Data again (Fresh)
        user = await col_users.find_one({'id': user_id})
        characters = user['characters']
        anime_map = defaultdict(list)
        for char in characters: anime_map[char['anime']].append(char)
        sorted_animes = sorted(anime_map.keys())

        new_page = current_page - 1 if action == "prev" else current_page + 1
        await send_harem_page(update, context, sorted_animes, anime_map, new_page, user_id, user.get('name', 'User'))

# --- GAME ENGINE (Spawn & Guess) ---
async def message_handler(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    if chat_id not in message_counts: message_counts[chat_id] = 0
    message_counts[chat_id] += 1

    if message_counts[chat_id] >= 5: 
        message_counts[chat_id] = 0
        await spawn_character(update, context)

async def spawn_character(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    pipeline = [{'$sample': {'size': 1}}]
    chars = await col_chars.aggregate(pipeline).to_list(length=1)
    if not chars: return 

    character = chars[0]
    last_spawn[chat_id] = {'char': character, 'time': time.time()}
    emoji = get_rarity_emoji(character['rarity'])

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption=f"⚡ A wild **{emoji} {character['rarity']}** character appeared!\n/guess Name to catch!",
        parse_mode='Markdown'
    )

async def guess(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if chat_id not in last_spawn: return 
    if not context.args: return

    user_guess = " ".join(context.args).lower()
    correct_name = last_spawn[chat_id]['char']['name'].lower()

    if user_guess == correct_name:
        char_data = last_spawn[chat_id]['char']
        time_taken = round(time.time() - last_spawn[chat_id]['time'], 2)
        COIN_REWARD = 40

        await col_users.update_one(
            {'id': user_id},
            {'$push': {'characters': char_data}, '$inc': {'balance': COIN_REWARD}, '$set': {'name': update.effective_user.first_name}},
            upsert=True
        )
        
        rarity_symbol = get_rarity_emoji(char_data['rarity'])
        
        await update.message.reply_text(f"🎉 Correct! You earned {COIN_REWARD} coins.")
        
        caption = (
            f"🌟 <b><a href='tg://user?id={user_id}'>{update.effective_user.first_name}</a></b>, you've captured a new character! 🎊\n\n"
            f"📛 <b>NAME:</b> {char_data['name']}\n"
            f"🌈 <b>ANIME:</b> {char_data['anime']}\n"
            f"✨ <b>RARITY:</b> {rarity_symbol} {char_data['rarity']}\n\n"
            f"⏱️ <b>TIME TAKEN:</b> {time_taken} seconds"
        )
        await update.message.reply_text(caption, parse_mode='HTML')
        del last_spawn[chat_id]

async def balance(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    bal = user.get('balance', 0) if user else 0
    await update.message.reply_text(f"💰 **Balance:** {bal} coins")

# --- RUN ---
def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rupload", rupload))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("harem", harem))
    app.add_handler(CommandHandler("guess", guess))
    app.add_handler(CallbackQueryHandler(harem_callback, pattern="^h_")) # Page Turn
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("✅ Bot Started with Advanced Harem...")
    app.run_polling()

if __name__ == "__main__":
    main()
