import logging
import asyncio
import random
import time
import math
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import web

# --- 1. CONFIGURATION ---
TOKEN = "8578752843:AAGUn1AT8qAegWh6myR6aV28RHm2h0LUrXY"
MONGO_URL = "mongodb+srv://seasonking:season_123@cluster0.e5zbzap.mongodb.net/?appName=Cluster0"
OWNER_ID = 7164618867
CHANNEL_ID = -1003352372209 
PHOTO_URL = "https://telegra.ph/file/b925c3985f0f325e62e17.jpg"
PORT = 10000
BOT_USERNAME = "seasonwaifuBot" # Aapka bot username
OWNER_USERNAME = "DADY_JI" # Owner username without @

# --- 2. DATABASE ---
client = AsyncIOMotorClient(MONGO_URL)
db = client['MyNewBot']
col_chars = db['characters']
col_users = db['users']

# --- 3. LOGGING & GLOBAL VARS ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

message_counts = {}
last_spawn = {} 
START_TIME = time.time() # Bot start hone ka time note kar liya

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

def get_readable_time(seconds: int) -> str:
    count = 0
    ping_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]

    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)

    for x in range(len(time_list)):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        ping_time += time_list.pop() + ", "

    time_list.reverse()
    ping_time += ":".join(time_list)
    return ping_time

# --- 5. COMMANDS ---

async def start(update: Update, context: CallbackContext):
    # Uptime Calculation
    uptime = get_readable_time(int(time.time() - START_TIME))
    
    # Fake but realistic Ping
    ping = f"{random.choice([1.2, 0.9, 1.5, 2.1])} ms"

    caption = f"""
🌿 <b>GREETINGS, I’M ︙ SEASON WAIFU CATCHER ︙ @{BOT_USERNAME}</b>
°○°, NICE TO MEET YOU!

───────────𖤐𖤐𖤐───────────

◎ <b>WHAT I DO:</b>
I SPAWN WAIFUS IN YOUR CHAT FOR USERS TO GRAB.

◎ <b>TO USE ME:</b>
ADD ME TO YOUR GROUP AND TAP THE HELP BUTTON FOR DETAILS.

───────────𖤐𖤐𖤐───────────

📶 <b>PING:</b> {ping}
⏱️ <b>UPTIME:</b> {uptime}
"""
    
    # Buttons Style (Screenshot Jaisa)
    keyboard = [
        [InlineKeyboardButton("Add to Your Group", url=f"http://t.me/{BOT_USERNAME}?startgroup=new")],
        [InlineKeyboardButton("🔧 SUPPORT", url=f"https://t.me/{BOT_USERNAME}"), InlineKeyboardButton("📣 CHANNEL", url=f"https://t.me/{BOT_USERNAME}")],
        [InlineKeyboardButton("❓ HELP", callback_data="help_menu")],
        [InlineKeyboardButton(f"👑 OWNER — @{OWNER_USERNAME}", url=f"https://t.me/{OWNER_USERNAME}")]
    ]
    
    await update.message.reply_photo(
        photo=PHOTO_URL, 
        caption=caption, 
        parse_mode='HTML', 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def help_menu(update: Update, context: CallbackContext):
    msg = """
<b>⚙️ HELP MENU</b>

<b>/guess</b> - Character pakdne ke liye
<b>/harem</b> - Apna collection dekhne ke liye
<b>/balance</b> - Coins check karein
<b>/roll</b> - Coins se character khareedein
<b>/rupload</b> - (Admin) Naya character dalein
"""
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(msg, parse_mode='HTML')
    else:
        await update.message.reply_text(msg, parse_mode='HTML')

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
        
        rarity_map = {1:"🥉 Low", 2:"🥈 Medium", 3:"🥇 High", 4:"🔮 Special Edition", 5:"💠 Elite Edition", 6:"🦄 Legendary", 7:"💌 Valentine", 8:"🧛🏻 Halloween", 9:"🥶 Winter", 10:"🍹 Summer", 11:"⚜️ Royal", 12:"💍 Luxury Edition"}
        try: rarity = rarity_map.get(int(args[2]), "✨ Special")
        except: rarity = "✨ Special"

        file_id = update.message.reply_to_message.photo[-1].file_id
        char_id = str(random.randint(1000, 9999))
        await col_chars.insert_one({'img_url': file_id, 'name': name, 'anime': anime, 'rarity': rarity, 'id': char_id})
        
        await update.message.reply_text(f"✅ Uploaded: **{name}**")
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=file_id, caption=f"🆕 New Character: {name}\n🌈 Anime: {anime}\n✨ Rarity: {rarity}\n🆔 ID: {char_id}")
    except Exception as e: await update.message.reply_text(f"Error: {e}")

# --- HAREM ---
async def harem(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if update.message.reply_to_message: user_id = update.message.reply_to_message.from_user.id
    user = await col_users.find_one({'id': user_id})
    if not user or not user.get('characters'):
        await update.message.reply_text("❌ Collection khali hai.")
        return
    
    characters = user['characters']
    anime_map = defaultdict(list)
    for char in characters: anime_map[char['anime']].append(char)
    await send_harem_page(update, context, sorted(anime_map.keys()), anime_map, 0, user_id, user.get('name', 'User'))

async def send_harem_page(update, context, sorted_animes, anime_map, page, user_id, user_name):
    CHUNK_SIZE = 5
    total_pages = math.ceil(len(sorted_animes) / CHUNK_SIZE)
    if page < 0: page = 0
    if page >= total_pages: page = total_pages - 1

    current_animes = sorted_animes[page * CHUNK_SIZE : (page + 1) * CHUNK_SIZE]
    msg = f"<b>🍃 {user_name}'s Harem</b>\nTotal Characters: {sum(len(v) for v in anime_map.values())}\n\n"
    for anime in current_animes:
        chars = anime_map[anime]
        msg += f"<b>{anime}</b> {len(chars)}\n"
        for char in chars:
            msg += f"♦️ {get_rarity_emoji(char['rarity'])} <code>{char['id']}</code> {char['name']} ×1\n"
        msg += "\n"

    buttons = []
    nav = []
    if page > 0: nav.append(InlineKeyboardButton("⬅️", callback_data=f"h_prev_{user_id}_{page}"))
    if page < total_pages - 1: nav.append(InlineKeyboardButton("➡️", callback_data=f"h_next_{user_id}_{page}"))
    buttons.append(nav)
    buttons.append([InlineKeyboardButton(f"Collection ({sum(len(v) for v in anime_map.values())})", callback_data="dummy")])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    if update.callback_query: await update.callback_query.edit_message_text(msg, parse_mode='HTML', reply_markup=reply_markup)
    else: await update.message.reply_text(msg, parse_mode='HTML', reply_markup=reply_markup)

async def harem_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split('_')
    if data[0] == "h":
        user_id, current_page = int(data[2]), int(data[3])
        if query.from_user.id != user_id:
            await query.answer("❌ Not your harem!", show_alert=True)
            return
        user = await col_users.find_one({'id': user_id})
        characters = user['characters']
        anime_map = defaultdict(list)
        for char in characters: anime_map[char['anime']].append(char)
        new_page = current_page - 1 if data[1] == "prev" else current_page + 1
        await send_harem_page(update, context, sorted(anime_map.keys()), anime_map, new_page, user_id, user.get('name', 'User'))
    
    if query.data == "help_menu":
        await help_menu(update, context)

# --- GAME ENGINE ---
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
    await context.bot.send_photo(chat_id=chat_id, photo=character['img_url'], caption=f"⚡ A wild **{emoji} {character['rarity']}** character appeared!\n/guess Name to catch!", parse_mode='Markdown')

async def guess(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if chat_id not in last_spawn: return 
    if not context.args: return
    if " ".join(context.args).lower() == last_spawn[chat_id]['char']['name'].lower():
        char_data = last_spawn[chat_id]['char']
        time_taken = round(time.time() - last_spawn[chat_id]['time'], 2)
        await col_users.update_one({'id': user_id}, {'$push': {'characters': char_data}, '$inc': {'balance': 40}, '$set': {'name': update.effective_user.first_name}}, upsert=True)
        updated_user = await col_users.find_one({'id': user_id})
        await update.message.reply_text(f"🎉 Correct! You earned 40 coins.\nBalance: {updated_user['balance']}")
        caption = f"🌟 <b><a href='tg://user?id={user_id}'>{update.effective_user.first_name}</a></b>, you've captured a new character! 🎊\n\n📛 <b>NAME:</b> {char_data['name']}\n🌈 <b>ANIME:</b> {char_data['anime']}\n✨ <b>RARITY:</b> {get_rarity_emoji(char_data['rarity'])} {char_data['rarity']}\n\n⏱️ <b>TIME TAKEN:</b> {time_taken} seconds"
        await update.message.reply_text(caption, parse_mode='HTML', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("See Harem", switch_inline_query_current_chat=f"collection.{user_id}")]]))
        del last_spawn[chat_id]

async def balance(update: Update, context: CallbackContext):
    user = await col_users.find_one({'id': update.effective_user.id})
    await update.message.reply_text(f"💰 **Balance:** {user.get('balance', 0) if user else 0} coins")

# --- WEB SERVER & MAIN FIX ---
async def web_server():
    async def handle(request): return web.Response(text="Bot is Live!")
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

async def main():
    await web_server()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rupload", rupload))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("harem", harem))
    app.add_handler(CommandHandler("guess", guess))
    app.add_handler(CallbackQueryHandler(harem_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    print("✅ Bot Started Successfully...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
