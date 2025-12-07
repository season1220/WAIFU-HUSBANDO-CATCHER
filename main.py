import logging
import asyncio
import random
import time
import math
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument
from aiohttp import web

# --- 1. CONFIGURATION ---
TOKEN = "8578752843:AAGUn1AT8qAegWh6myR6aV28RHm2h0LUrXY"
MONGO_URL = "mongodb+srv://seasonking:season_123@cluster0.e5zbzap.mongodb.net/?appName=Cluster0"
OWNER_ID = 7164618867
CHANNEL_ID = -1003352372209 
PHOTO_URL = "https://telegra.ph/file/5e7300c32609050d26733.jpg"
PORT = 10000
BOT_USERNAME = "seasonwaifuBot"
OWNER_USERNAME = "DADY_JI"

# --- 2. DATABASE ---
client = AsyncIOMotorClient(MONGO_URL)
db = client['MyNewBot']
col_chars = db['characters']
col_users = db['users']
col_settings = db['settings']
col_seq = db['sequences']

# --- 3. LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 4. VARIABLES ---
message_counts = {}
last_spawn = {} 
START_TIME = time.time()

# --- HELPER FUNCTIONS ---
RARITY_MAP = {
    1: "🥉 Low", 2: "🥈 Medium", 3: "🥇 High", 4: "🔮 Special Edition", 
    5: "💠 Elite Edition", 6: "🦄 Legendary", 7: "💌 Valentine", 
    8: "🧛🏻 Halloween", 9: "🥶 Winter", 10: "🍹 Summer", 
    11: "⚜️ Royal", 12: "💍 Luxury Edition"
}

RARITY_PRICE = {
    "Low": 200, "Medium": 500, "High": 1000, "Special Edition": 2000,
    "Elite Edition": 3000, "Legendary": 5000, "Valentine": 6000,
    "Halloween": 6000, "Winter": 6000, "Summer": 6000,
    "Royal": 10000, "Luxury Edition": 20000
}

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
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]
    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0: break
        time_list.append(int(result))
        seconds = int(remainder)
    for x in range(len(time_list)): time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4: time_list.pop()
    time_list.reverse()
    return ":".join(time_list)

async def is_admin(user_id):
    if user_id == OWNER_ID: return True
    doc = await col_settings.find_one({'_id': 'admins'})
    if doc and user_id in doc.get('list', []): return True
    return False

async def get_next_id():
    doc = await col_seq.find_one_and_update(
        {'_id': 'char_id'}, {'$inc': {'seq': 1}}, 
        return_document=ReturnDocument.AFTER, upsert=True
    )
    return str(doc['seq']).zfill(2)

# --- 5. COMMANDS ---

async def start(update: Update, context: CallbackContext):
    uptime = get_readable_time(int(time.time() - START_TIME))
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

───────────
"""
    keyboard = [
        [InlineKeyboardButton("👥 ADD ME TO YOUR GROUP", url=f"http://t.me/{BOT_USERNAME}?startgroup=new")],
        [InlineKeyboardButton("🔧 SUPPORT", url=f"https://t.me/{BOT_USERNAME}"), InlineKeyboardButton("📣 CHANNEL", url=f"https://t.me/{BOT_USERNAME}")],
        [InlineKeyboardButton("❓ HELP", callback_data="help_menu")],
        [InlineKeyboardButton(f"👑 OWNER — @{OWNER_USERNAME}", url=f"https://t.me/{OWNER_USERNAME}")]
    ]
    await update.message.reply_photo(photo=PHOTO_URL, caption=caption, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def help_menu(update: Update, context: CallbackContext):
    msg = """
<b>⚙️ HELP MENU</b>
/guess - Character pakdne ke liye
/harem - Collection dekhne ke liye
/shop - Cosmic Bazaar
/trade - Character trade karein
/gift - Free gift karein
/daily - Free rewards
/balance - Paise check karein
"""
    if update.callback_query: await update.callback_query.message.reply_text(msg, parse_mode='HTML')
    else: await update.message.reply_text(msg, parse_mode='HTML')

# --- ADMIN COMMANDS ---

async def rupload(update: Update, context: CallbackContext):
    if not await is_admin(update.effective_user.id): return
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
        try: rarity = RARITY_MAP.get(int(args[2]), "✨ Special")
        except: rarity = "✨ Special"

        file_id = update.message.reply_to_message.photo[-1].file_id
        char_id = await get_next_id()

        uploader_name = update.effective_user.first_name
        uploader_id = update.effective_user.id

        char_data = {'img_url': file_id, 'name': name, 'anime': anime, 'rarity': rarity, 'id': char_id}
        await col_chars.insert_one(char_data)
        
        await col_users.update_one(
            {'id': uploader_id},
            {'$push': {'characters': char_data}, '$set': {'name': uploader_name}},
            upsert=True
        )

        await update.message.reply_text(f"✅ **Uploaded!**\n🆔 ID: `{char_id}`")
        caption = (f"Character Name: {name}\nAnime Name: {anime}\nRarity: {rarity}\nID: {char_id}\nAdded by <a href='tg://user?id={uploader_id}'>{uploader_name}</a>")
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=file_id, caption=caption, parse_mode='HTML')
    except Exception as e: await update.message.reply_text(f"Error: {e}")

async def addshop(update: Update, context: CallbackContext):
    if not await is_admin(update.effective_user.id): return
    try:
        args = context.args
        if len(args) < 2: return
        char_id, price = args[0], int(args[1])
        await col_chars.update_one({'id': char_id}, {'$set': {'price': price}})
        await update.message.reply_text(f"✅ Added to Shop: {price} coins")
    except: pass

async def delete(update: Update, context: CallbackContext):
    if not await is_admin(update.effective_user.id): return
    if not context.args: return
    char_id = context.args[0]
    res = await col_chars.delete_one({'id': char_id})
    if res.deleted_count: await update.message.reply_text(f"✅ Deleted `{char_id}`.")
    else: await update.message.reply_text("❌ ID not found.")

async def changetime(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not await is_admin(user_id): return
    if not context.args: return
    try: freq = int(context.args[0])
    except: return
    if user_id != OWNER_ID and freq < 80: return
    await col_settings.update_one({'_id': str(update.effective_chat.id)}, {'$set': {'freq': freq}}, upsert=True)
    await update.message.reply_text(f"✅ Frequency: **{freq}**")

async def bcast(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID: return
    if not update.message.reply_to_message: return
    msg = update.message.reply_to_message
    users = await col_users.find({}).to_list(length=None)
    sent = 0
    await update.message.reply_text(f"📢 Broadcasting...")
    for u in users:
        try:
            await msg.copy(chat_id=u['id'])
            sent += 1
            await asyncio.sleep(0.1)
        except: pass
    await update.message.reply_text(f"✅ Sent to {sent} users.")

# --- FEATURES ---

async def daily(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    if not user: return
    last_daily = user.get('last_daily', 0)
    if time.time() - last_daily < 86400:
        await update.message.reply_text("❌ Kal aana!")
        return
    await col_users.update_one({'id': user_id}, {'$inc': {'balance': 500}, '$set': {'last_daily': time.time()}})
    await update.message.reply_text("🎁 **Daily Reward!** Received **500 coins**!")

async def gift(update: Update, context: CallbackContext):
    sender_id = update.effective_user.id
    if not update.message.reply_to_message: return
    receiver_id = update.message.reply_to_message.from_user.id
    if sender_id == receiver_id: return
    if not context.args: return
    char_id = context.args[0]
    
    sender = await col_users.find_one({'id': sender_id})
    character = next((c for c in sender.get('characters', []) if c['id'] == char_id), None)
    if not character:
        await update.message.reply_text("❌ Character nahi mila.")
        return
    
    await col_users.update_one({'id': sender_id}, {'$pull': {'characters': {'id': char_id}}})
    await col_users.update_one({'id': receiver_id}, {'$push': {'characters': character}}, upsert=True)
    await update.message.reply_text(f"🎁 **{character['name']}** gifted successfully!")

async def trade(update: Update, context: CallbackContext):
    await gift(update, context)

async def top(update: Update, context: CallbackContext):
    cursor = col_users.find({})
    users = []
    async for user in cursor:
        if 'characters' in user:
            users.append({'name': user.get('name', 'Unknown'), 'count': len(user['characters'])})
    users = sorted(users, key=lambda x: x['count'], reverse=True)[:10]
    msg = "🏆 **LEADERBOARD**\n\n"
    for i, user in enumerate(users, 1): msg += f"{i}. {user['name']} ➾ {user['count']}\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def balance(update: Update, context: CallbackContext):
    user = await col_users.find_one({'id': update.effective_user.id})
    await update.message.reply_text(f"💰 **Balance:** {user.get('balance', 0) if user else 0} coins")

# --- SHOP & RCLAIM ---

async def rclaim(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    if not user: return
    last_rclaim = user.get('last_rclaim', 0)
    if time.time() - last_rclaim < 86400:
        await update.message.reply_text("❌ Free Character Claimed! Kal aana.")
        return
    pipeline = [{'$sample': {'size': 1}}]
    chars = await col_chars.aggregate(pipeline).to_list(length=1)
    if not chars: return
    char = chars[0]
    await col_users.update_one({'id': user_id}, {'$push': {'characters': char}, '$set': {'last_rclaim': time.time()}})
    await update.message.reply_photo(photo=char['img_url'], caption=f"🎁 **FREE CHARACTER!**\n📛 {char['name']}\n✨ {char['rarity']}")

async def shop(update: Update, context: CallbackContext):
    await send_shop_item(update, context)

async def send_shop_item(update: Update, context: CallbackContext):
    pipeline = [{'$match': {'price': {'$exists': True}}}, {'$sample': {'size': 1}}]
    chars = await col_chars.aggregate(pipeline).to_list(length=1)
    if not chars:
        pipeline_random = [{'$sample': {'size': 1}}]
        chars = await col_chars.aggregate(pipeline_random).to_list(length=1)
        if not chars: return
        char = chars[0]
        price = 500
        for r_name, r_price in RARITY_PRICE.items():
            if r_name in char['rarity']: price = r_price; break
    else:
        char = chars[0]
        price = char['price']

    caption = f"""
🌟 **COSMIC BAZAAR** 🌟
<b>Hero:</b> {char['name']}
<b>Realm:</b> {char['anime']}
<b>Legend Tier:</b> {get_rarity_emoji(char['rarity'])} {char['rarity']}
<b>Cost:</b> {price} Coins
<b>ID:</b> {char['id']}
"""
    keyboard = [[InlineKeyboardButton("Claim Hero!", callback_data=f"buy_{char['id']}_{price}")],[InlineKeyboardButton("Next Hero", callback_data="shop_next")]]
    if update.callback_query:
        await update.callback_query.message.delete()
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=char['img_url'], caption=caption, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_photo(photo=char['img_url'], caption=caption, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def shop_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split('_')
    user_id = query.from_user.id
    if data[0] == "shop": await send_shop_item(update, context); return
    if data[0] == "buy":
        char_id = data[1]
        price = int(data[2])
        user = await col_users.find_one({'id': user_id})
        if user.get('balance', 0) < price:
            await query.answer("❌ Not enough coins!", show_alert=True)
            return
        char = await col_chars.find_one({'id': char_id})
        if not char: return
        await col_users.update_one({'id': user_id}, {'$inc': {'balance': -price}, '$push': {'characters': char}})
        await query.answer("✅ Purchased!", show_alert=True)
        await query.message.edit_caption(caption=f"✅ **SOLD!**\n{char['name']} is yours!")

# --- HAREM (STYLE UPDATE) ---
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
    total_count = sum(len(v) for v in anime_map.values())
    
    msg = f"<b>🍃 {user_name}'s Harem - Page {page+1}/{total_pages}</b>\n\n"
    
    for anime in current_animes:
        chars = anime_map[anime]
        # Anime Header e.g., "One Piece 2/356" (Total DB count hard to fetch efficiently, using user count)
        msg += f"<b>{anime}</b> {len(chars)}\n"
        for char in chars:
            # STYLE MATCH: ♦️ [ 🎗️ ] ID Name ×1
            emoji = get_rarity_emoji(char['rarity'])
            msg += f"♦️ [ {emoji} ] <code>{char['id']}</code> {char['name']} ×1\n"
        msg += "\n"

    buttons = []
    nav = []
    if page > 0: nav.append(InlineKeyboardButton("⬅️", callback_data=f"h_prev_{user_id}_{page}"))
    if page < total_pages - 1: nav.append(InlineKeyboardButton("➡️", callback_data=f"h_next_{user_id}_{page}"))
    buttons.append(nav)
    # Button Style Match
    buttons.append([
        InlineKeyboardButton(f"Collection ({total_count})", callback_data="dummy"),
        InlineKeyboardButton("❤️ AMV (0)", callback_data="dummy")
    ])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    if update.callback_query: await update.callback_query.edit_message_text(msg, parse_mode='HTML', reply_markup=reply_markup)
    else: await update.message.reply_text(msg, parse_mode='HTML', reply_markup=reply_markup)

async def harem_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split('_')
    if data[0] == "h":
        user_id, current_page = int(data[2]), int(data[3])
        if query.from_user.id != user_id:
            await query.answer("❌ Not your harem!", show_alert=True); return
        user = await col_users.find_one({'id': user_id})
        anime_map = defaultdict(list)
        for char in user['characters']: anime_map[char['anime']].append(char)
        new_page = current_page - 1 if data[1] == "prev" else current_page + 1
        await send_harem_page(update, context, sorted(anime_map.keys()), anime_map, new_page, user_id, user.get('name', 'User'))
    if query.data == "help_menu": await help_menu(update, context)

# --- GAME ENGINE ---
async def message_handler(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    if chat_id not in message_counts: message_counts[chat_id] = 0
    message_counts[chat_id] += 1
    settings = await col_settings.find_one({'_id': chat_id})
    freq = settings.get('freq', 100) if settings else 100
    if message_counts[chat_id] >= freq:
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

# --- MAIN ---
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
    app.add_handler(CommandHandler("addshop", addshop))
    app.add_handler(CommandHandler("delete", delete))
    app.add_handler(CommandHandler("changetime", changetime))
    app.add_handler(CommandHandler("ctime", changetime)) 
    
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("gift", gift))
    app.add_handler(CommandHandler("trade", trade)) 
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(CommandHandler("rclaim", rclaim))
    
    app.add_handler(CommandHandler("harem", harem))
    app.add_handler(CommandHandler("guess", guess))
    app.add_handler(CallbackQueryHandler(harem_callback, pattern="^h_"))
    app.add_handler(CallbackQueryHandler(shop_callback, pattern="^(shop|buy)"))
    app.add_handler(CallbackQueryHandler(help_menu, pattern="help_menu"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    print("✅ Bot Started Successfully...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
