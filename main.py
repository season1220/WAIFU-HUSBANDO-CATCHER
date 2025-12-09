import logging
import asyncio
import random
import time
import math
import os
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler, InlineQueryHandler
from telegram.error import BadRequest
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument
from aiohttp import web

# --- 1. CONFIGURATION ---
TOKEN = "8578752843:AAGUn1AT8qAegWh6myR6aV28RHm2h0LUrXY"
MONGO_URL = "mongodb+srv://seasonking:season_123@cluster0.e5zbzap.mongodb.net/?appName=Cluster0"
OWNER_ID = 7164618867
CHANNEL_ID = -1003352372209 
PORT = 10000
BOT_USERNAME = "seasonwaifuBot"
OWNER_USERNAME = "DADY_JI"

# --- ASSETS ---
START_MEDIA_LIST = [
    "https://upload.wikimedia.org/wikipedia/commons/9/9a/WrestleMania_38_stage_april_2nd_2022.jpg",
    "https://telegra.ph/file/5e7300c32609050d26733.jpg",
    "https://graph.org/file/9b0d2432bd337372295a6.mp4"
]
START_CAPTIONS_LIST = [
    "𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐭𝐨 𝐭𝐡𝐞 𝐄𝐥𝐢𝐭𝐞 𝐖𝐚𝐢𝐟𝐮 𝐒𝐲𝐬𝐭𝐞𝐦.",
    "𝐓𝐡𝐞 𝐒𝐞𝐚𝐬𝐨𝐧 𝐊𝐢𝐧𝐠 𝐢𝐬 𝐡𝐞𝐫𝐞.",
    "𝐂𝐨𝐥𝐥𝐞𝐜𝐭 𝐲𝐨𝐮𝐫 𝐝𝐫𝐞𝐚𝐦 𝐰𝐚𝐢𝐟𝐮𝐬 𝐧𝐨𝐰!"
]
PHOTO_URL = "https://telegra.ph/file/5e7300c32609050d26733.jpg"

# --- 2. DATABASE ---
client = AsyncIOMotorClient(MONGO_URL)
db = client['MyNewBot']
col_chars = db['characters']
col_users = db['users']
col_settings = db['settings']
col_seq = db['sequences']
col_market = db['market']
col_auctions = db['auctions']
col_clans = db['clans']

# --- 3. LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 4. VARIABLES ---
message_counts = {}
last_spawn = {} 
START_TIME = time.time()

# --- HELPER FUNCTIONS ---
RARITY_MAP = {
    1: "🔸 Low", 2: "🔷 Medium", 3: "♦️ High", 4: "🔮 Special Edition", 
    5: "💮 Elite Edition", 6: "👑 Legendary", 7: "💝 Valentine", 
    8: "🎃 Halloween", 9: "❄️ Winter", 10: "🏜 Summer", 
    11: "🎗 Royal", 12: "💸 Luxury", 13: "⛩ AMV"
}

def get_rarity_emoji(rarity):
    if not rarity: return "✨"
    r = rarity.lower()
    if "amv" in r: return "⛩"
    if "luxury" in r: return "💸"
    if "royal" in r: return "🎗"
    if "summer" in r: return "🏜"
    if "winter" in r: return "❄️"
    if "halloween" in r: return "🎃"
    if "valentine" in r: return "💝"
    if "legendary" in r: return "👑"
    if "elite" in r: return "💮"
    if "special" in r: return "🔮"
    if "high" in r: return "♦️"
    if "medium" in r: return "🔷"
    if "low" in r: return "🔸"
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
    doc = await col_seq.find_one_and_update({'_id': 'char_id'}, {'$inc': {'seq': 1}}, return_document=ReturnDocument.AFTER, upsert=True)
    return str(doc['seq']).zfill(2)

async def error_handler(update: object, context: CallbackContext) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

# --- SMART SENDER ---
async def smart_send(context, chat_id, file_id, caption, reply_markup=None):
    try:
        await context.bot.send_photo(chat_id=chat_id, photo=file_id, caption=caption, parse_mode='HTML', reply_markup=reply_markup)
    except BadRequest:
        try:
            await context.bot.send_video(chat_id=chat_id, video=file_id, caption=caption, parse_mode='HTML', reply_markup=reply_markup)
        except Exception as e:
            try:
                await context.bot.send_animation(chat_id=chat_id, animation=file_id, caption=caption, parse_mode='HTML', reply_markup=reply_markup)
            except: pass

# --- BACKGROUND TASK ---
async def check_auctions(app):
    while True:
        try:
            now = time.time()
            expired = await col_auctions.find({'end_time': {'$lte': now}}).to_list(length=None)
            for auction in expired:
                char = auction['char']
                seller_id = auction['seller_id']
                if auction.get('top_bidder'):
                    winner_id = auction['top_bidder']
                    price = auction['current_bid']
                    await col_users.update_one({'id': winner_id}, {'$push': {'characters': char}})
                    await col_users.update_one({'id': seller_id}, {'$inc': {'balance': price}})
                    try: await app.bot.send_message(chat_id=CHANNEL_ID, text=f"🔨 **Auction Ended!**\n{char['name']} sold to `{winner_id}` for {price} coins!", parse_mode='Markdown')
                    except: pass
                else:
                    await col_users.update_one({'id': seller_id}, {'$push': {'characters': auction['char']}})
                await col_auctions.delete_one({'_id': auction['_id']})
        except Exception as e: logger.error(f"Auction Error: {e}")
        await asyncio.sleep(60)

# --- COMMANDS ---

async def start(update: Update, context: CallbackContext):
    user = update.effective_user
    user_db = await col_users.find_one({'id': user.id})
    if not user_db:
        await col_users.insert_one({'id': user.id, 'name': user.first_name, 'balance': 0, 'characters': []})
    
    uptime = get_readable_time(int(time.time() - START_TIME))
    media = random.choice(START_MEDIA_LIST)
    
    caption = f"""
✨ 𝐒𝐞𝐚𝐬𝐨𝐧 𝐖𝐚𝐢𝐟𝐮 𝐂𝐚𝐭𝐜𝐡𝐞𝐫 — @{BOT_USERNAME}
👋 Hello {user.first_name}!

✧━━━━━━━━━━━━✧
◎ 𝐅𝐞𝐚𝐭𝐮𝐫𝐞𝐬:
• Collect Anime Characters
• Trade, Sell & Fight
• Global Market

◎ 𝐔𝐬𝐚𝐠𝐞:
• Add me to Group
• Click Help for Commands
✧━━━━━━━━━━━━✧

📶 Ping: {random.randint(10,40)} ms
⏱️ Uptime: {uptime}
"""
    keyboard = [
        [InlineKeyboardButton("👥 Add to Group", url=f"http://t.me/{BOT_USERNAME}?startgroup=new")],
        [InlineKeyboardButton("❓ Help", callback_data="help_menu"), InlineKeyboardButton(f"👑 Owner", url=f"https://t.me/{OWNER_USERNAME}")]
    ]
    await smart_send(context, update.effective_chat.id, media, caption, InlineKeyboardMarkup(keyboard))

async def help_menu(update: Update, context: CallbackContext):
    msg = """
<b>⚙️ COMMAND LIST</b>
/guess - Catch character
/harem - Collection
/profile - Check Profile
/market - User Market
/sell - Sell character
/buy - Buy character
/trade - Trade with users
/daily - Free coins
/check - Check Info
/stats - Check User Count (Admin)
"""
    if update.callback_query: await update.callback_query.message.reply_text(msg, parse_mode='HTML')
    else: await update.message.reply_text(msg, parse_mode='HTML')

# --- ADMIN ---
async def rupload(update: Update, context: CallbackContext):
    if not await is_admin(update.effective_user.id): return
    msg = update.message.reply_to_message
    if not msg: await update.message.reply_text("⚠️ Reply to Media!"); return
    
    file_id = None
    c_type = "img"
    
    if msg.photo: file_id = msg.photo[-1].file_id
    elif msg.video: 
        file_id = msg.video.file_id; c_type = "amv"
    elif msg.animation:
        file_id = msg.animation.file_id; c_type = "amv"
        
    if not file_id: await update.message.reply_text("❌ Media not found."); return
    
    try:
        args = context.args
        if len(args) < 3: await update.message.reply_text("⚠️ `/rupload Name Anime RarityNum`"); return
        name = args[0].replace('-', ' ').title()
        anime = args[1].replace('-', ' ').title()
        try: rarity_num = int(args[2])
        except: await update.message.reply_text("❌ Rarity must be number"); return

        if c_type == "amv" and rarity_num != 13:
            await update.message.reply_text("❌ AMV must be Rarity 13!"); return

        rarity = RARITY_MAP.get(rarity_num, "✨ Special")
        char_id = await get_next_id()
        char_data = {'img_url': file_id, 'name': name, 'anime': anime, 'rarity': rarity, 'id': char_id, 'type': c_type}
        await col_chars.insert_one(char_data)
        
        await col_users.update_one({'id': OWNER_ID}, {'$push': {'characters': char_data}, '$set': {'name': 'DADY_JI'}}, upsert=True)

        await update.message.reply_text(f"✅ Uploaded `{char_id}`")
        caption = f"New Character: {name}\nAnime: {anime}\nRarity: {rarity}\nID: {char_id}"
        await smart_send(context, CHANNEL_ID, file_id, caption)
        
    except Exception as e: await update.message.reply_text(f"Error: {e}")

async def stats(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID: return
    count = await col_users.count_documents({})
    await update.message.reply_text(f"Users: {count}")

async def rupdate(update: Update, context: CallbackContext):
    if not await is_admin(update.effective_user.id): return
    try:
        args = context.args
        if len(args) < 3: await update.message.reply_text("⚠️ **Format:** `/rupdate [ID] [field] [New Value]`"); return
        char_id = args[0]; field = args[1].lower(); new_val = " ".join(args[2:])
        if field == "rarity": 
             try: new_val = RARITY_MAP.get(int(new_val), new_val)
             except: pass
        result = await col_chars.update_one({'id': char_id}, {'$set': {field: new_val}})
        if result.modified_count > 0: await update.message.reply_text(f"✅ Updated **{field}**.")
        else: await update.message.reply_text("❌ ID not found.")
    except Exception as e: await update.message.reply_text(f"Error: {e}")

async def addshop(update: Update, context: CallbackContext):
    if not await is_admin(update.effective_user.id): return
    try:
        char_id, price = context.args[0], int(context.args[1])
        await col_chars.update_one({'id': char_id}, {'$set': {'price': price}})
        await update.message.reply_text(f"✅ Shop Item: {price}")
    except: pass

async def delete(update: Update, context: CallbackContext):
    if not await is_admin(update.effective_user.id): return
    if not context.args: return
    res = await col_chars.delete_one({'id': context.args[0]})
    await update.message.reply_text(f"✅ Deleted." if res.deleted_count else "❌ Not found.")

async def changetime(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not await is_admin(user_id): return
    try: freq = int(context.args[0])
    except: return
    if user_id != OWNER_ID and (freq < 80 or freq > 300): return
    await col_settings.update_one({'_id': str(update.effective_chat.id)}, {'$set': {'freq': freq}}, upsert=True)
    await update.message.reply_text(f"✅ Frequency: {freq}")

async def bcast(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID: return
    if not update.message.reply_to_message: return
    msg = update.message.reply_to_message
    users = await col_users.find({}).to_list(length=None)
    for u in users:
        try: await msg.copy(chat_id=u['id'])
        except: pass
    await update.message.reply_text("✅ Broadcast done.")

# --- FEATURES ---

async def daily(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    if not user: await col_users.insert_one({'id': user_id, 'name': update.effective_user.first_name, 'balance': 0, 'characters': []})
    if user_id != OWNER_ID:
        last_daily = user.get('last_daily', 0) if user else 0
        if time.time() - last_daily < 86400: await update.message.reply_text("❌ Come back tomorrow."); return
    await col_users.update_one({'id': user_id}, {'$inc': {'balance': 500}, '$set': {'last_daily': time.time()}})
    await update.message.reply_text("🎁 +500 Coins!")

async def gift(update: Update, context: CallbackContext):
    sender_id = update.effective_user.id
    if not update.message.reply_to_message: return
    receiver_id = update.message.reply_to_message.from_user.id
    if sender_id == receiver_id: return
    char_id = context.args[0]
    sender = await col_users.find_one({'id': sender_id})
    char = next((c for c in sender.get('characters', []) if c['id'] == char_id), None)
    if not char: await update.message.reply_text("❌ Not found."); return
    await col_users.update_one({'id': sender_id}, {'$pull': {'characters': {'id': char_id}}})
    await col_users.update_one({'id': receiver_id}, {'$push': {'characters': char}}, upsert=True)
    await update.message.reply_text(f"🎁 Gifted **{char['name']}**!")

async def trade(update: Update, context: CallbackContext): await gift(update, context)

async def top(update: Update, context: CallbackContext):
    cursor = col_users.find({})
    users = sorted([{'name': u.get('name', 'Unknown'), 'count': len(u['characters'])} async for u in cursor if 'characters' in u], key=lambda x: x['count'], reverse=True)[:10]
    msg = "🏆 **LEADERBOARD**\n\n" + "\n".join([f"{i+1}. {u['name']} ➾ {u['count']}" for i, u in enumerate(users)])
    await update.message.reply_text(msg, parse_mode='Markdown')

async def balance(update: Update, context: CallbackContext):
    user = await col_users.find_one({'id': update.effective_user.id})
    bal = user.get('balance', 0) if user else 0
    await update.message.reply_text(f"💰 **Balance:** {bal} coins")

# ✅ NEW CHECK COMMAND (UPDATED AS PER SCREENSHOT)
async def check(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /check <Character-ID>")
        return

    char_id = context.args[0]
    char = await col_chars.find_one({'id': char_id})

    if not char:
        await update.message.reply_text("❌ Character not found.")
        return

    # Find Top 10 Owners
    cursor = col_users.find({"characters.id": char_id})
    top_owners = []

    async for user in cursor:
        count = sum(1 for c in user['characters'] if c['id'] == char_id)
        if count > 0:
            top_owners.append((user.get('name', 'Unknown'), count, user['id']))

    top_owners.sort(key=lambda x: x[1], reverse=True)

    leaderboard = ""
    if top_owners:
        for i, (name, count, uid) in enumerate(top_owners[:10], 1):
            safe_name = name.replace("<", "&lt;").replace(">", "&gt;")
            leaderboard += f"{i}. <a href='tg://user?id={uid}'>{safe_name}</a> — x{count}\n"
    else:
        leaderboard = "No one owns this character yet."

    rarity_emoji = get_rarity_emoji(char['rarity'])
    
    caption = f"""<b>🌟 Character Info</b>
🆔 <b>ID:</b> {char['id']}
📛 <b>Name:</b> {char['name']}
📺 <b>Anime:</b> {char['anime']}
💎 <b>Rarity:</b> {rarity_emoji} {char['rarity']}

🏆 <b>Top 10 Users Who Own This Character:</b>

{leaderboard}"""

    await smart_send(context, update.effective_chat.id, char['img_url'], caption)

async def fav(update: Update, context: CallbackContext):
    if not context.args: return
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    char = next((c for c in user.get('characters', []) if c['id'] == context.args[0]), None)
    if not char: return
    await col_users.update_one({'id': user_id}, {'$set': {'favorites': char}})
    await update.message.reply_text(f"❤️ Favorite set: {char['name']}")

# --- MARKET & PROFILE ---
async def market(update: Update, context: CallbackContext):
    items = await col_market.find({}).to_list(length=10)
    if not items: await update.message.reply_text("🏛️ Market empty."); return
    msg = "🏛️ **GLOBAL MARKET**\n\n"
    for i in items: msg += f"🆔 `{i['id']}` : {i['name']} - 💰 {i['price']}\n"
    msg += "\nUse `/buy [ID]`"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def sell(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if len(context.args) < 2: await update.message.reply_text("⚠️ `/sell [ID] [Price]`"); return
    char_id, price = context.args[0], int(context.args[1])
    user = await col_users.find_one({'id': user_id})
    char = next((c for c in user.get('characters', []) if c['id'] == char_id), None)
    if not char: await update.message.reply_text("❌ Not found."); return
    await col_users.update_one({'id': user_id}, {'$pull': {'characters': {'id': char_id}}})
    item = char.copy(); item['price'] = price; item['seller'] = user_id
    await col_market.insert_one(item)
    await update.message.reply_text(f"✅ Listed **{char['name']}** for {price}!")

async def buy(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not context.args: await update.message.reply_text("⚠️ `/buy [ID]`"); return
    char_id = context.args[0]
    item = await col_market.find_one({'id': char_id})
    if not item: await update.message.reply_text("❌ Sold/Invalid."); return
    buyer = await col_users.find_one({'id': user_id})
    if buyer.get('balance', 0) < item['price']: await update.message.reply_text("❌ Poor."); return
    await col_users.update_one({'id': user_id}, {'$inc': {'balance': -item['price']}, '$push': {'characters': item}})
    await col_users.update_one({'id': item['seller']}, {'$inc': {'balance': item['price']}})
    await col_market.delete_one({'id': char_id})
    await update.message.reply_text(f"✅ Bought **{item['name']}**!")

async def profile(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if update.message.reply_to_message: user_id = update.message.reply_to_message.from_user.id
    user = await col_users.find_one({'id': user_id})
    if not user: 
        await col_users.insert_one({'id': user_id, 'name': update.effective_user.first_name, 'balance': 0, 'characters': []})
        user = {'name': update.effective_user.first_name, 'balance': 0, 'characters': []}
    name = user.get('name', 'User')
    bal = user.get('balance', 0)
    count = len(user.get('characters', []))
    married = user.get('married_to', {}).get('name', 'None')
    pic = PHOTO_URL
    if user.get('favorites'): pic = user['favorites']['img_url']
    elif user.get('married_to'): pic = user['married_to']['img_url']
    msg = f"👤 <b>PROFILE</b>\n👑 Name: {name}\n💰 Gold: {bal}\n📚 Chars: {count}\n💍 Married: {married}"
    await smart_send(context, update.effective_chat.id, pic, msg)

async def harem(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if update.message.reply_to_message: user_id = update.message.reply_to_message.from_user.id
    user = await col_users.find_one({'id': user_id})
    if not user or not user.get('characters'): await update.message.reply_text("❌ Empty."); return
    await send_harem_page(update, context, user_id, user.get('name', 'User'), 0, "img")

async def send_harem_page(update, context, user_id, user_name, page, mode):
    user = await col_users.find_one({'id': user_id})
    all_chars = user['characters']
    filtered = [c for c in all_chars if c.get('type', 'img') == mode]
    if not filtered and mode == 'amv': 
        if update.callback_query: await update.callback_query.answer("No AMVs", show_alert=True); return
    
    anime_map = defaultdict(list)
    for char in filtered: anime_map[char['anime']].append(char)
    sorted_animes = sorted(anime_map.keys())
    CHUNK = 4
    total_pages = math.ceil(len(sorted_animes) / CHUNK)
    if page < 0: page = 0
    if page >= total_pages: page = total_pages - 1
    current = sorted_animes[page * CHUNK : (page + 1) * CHUNK]
    
    msg = f"<b>🍃 {user_name}'s Harem</b>\nPage {page+1}/{total_pages}\n\n"
    for anime in current:
        chars = anime_map[anime]
        msg += f"<b>{anime} {len(chars)}</b>\n"
        for char in chars: msg += f"♦️ [ {get_rarity_emoji(char['rarity'])} ] <code>{char['id']}</code> {char['name']} (Lv.{char.get('level',1)})\n"
        msg += "\n"
    
    nav = [[InlineKeyboardButton("⬅️", callback_data=f"h_prev_{user_id}_{page}_{mode}"), InlineKeyboardButton("➡️", callback_data=f"h_next_{user_id}_{page}_{mode}")]]
    switch = [[InlineKeyboardButton("Collection", callback_data=f"h_switch_{user_id}_0_img"), InlineKeyboardButton("❤️ AMV", callback_data=f"h_switch_{user_id}_0_amv")]]
    
    markup = InlineKeyboardMarkup(nav + switch)
    if update.callback_query: await update.callback_query.edit_message_caption(caption=msg, parse_mode='HTML', reply_markup=markup)
    else: 
        await smart_send(context, update.effective_chat.id, PHOTO_URL, msg, markup)

async def harem_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split('_')
    if data[0] == "h":
        action, user_id, page, mode = data[1], int(data[2]), int(data[3]), data[4]
        if query.from_user.id != user_id: await query.answer("❌ Not yours!", show_alert=True); return
        user = await col_users.find_one({'id': user_id})
        new_page = page - 1 if action == "prev" else page + 1
        if action == "switch": new_page = 0
        await send_harem_page(update, context, user_id, user.get('name', 'User'), new_page, mode)
    if query.data == "help_menu": await help_menu(update, context)

# --- GAME ENGINE ---
async def message_handler(update: Update, context: CallbackContext):
    try:
        chat_id = str(update.effective_chat.id)
        if chat_id not in message_counts: message_counts[chat_id] = 0
        message_counts[chat_id] += 1
        settings = await col_settings.find_one({'_id': chat_id})
        freq = settings.get('freq', 100) if settings else 100
        if message_counts[chat_id] >= freq:
            message_counts[chat_id] = 0
            await spawn_character(update, context)
    except: pass

async def spawn_character(update: Update, context: CallbackContext):
    try:
        pipeline = [{'$sample': {'size': 1}}]
        chars = await col_chars.aggregate(pipeline).to_list(length=1)
        if not chars: return 
        char = chars[0]
        last_spawn[update.effective_chat.id] = {'char': char, 'time': time.time()}
        
        caption = f"✨ A {get_rarity_emoji(char['rarity'])} <b>{char['rarity']}</b> Character Appears!\n🔎 /guess to claim!"
        await smart_send(context, update.effective_chat.id, char['img_url'], caption)
    except Exception as e: logger.error(f"Spawn Error: {e}")

async def guess(update: Update, context: CallbackContext):
    try:
        chat_id = update.effective_chat.id
        if chat_id not in last_spawn: return 
        if not context.args: return
        guess_w = " ".join(context.args).lower()
        real_n = last_spawn[chat_id]['char']['name'].lower()
        
        if guess_w == real_n or any(p == guess_w for p in real_n.split()):
            char = last_spawn[chat_id]['char']
            user_id = update.effective_user.id
            
            await col_users.update_one({'id': user_id}, {'$push': {'characters': char}, '$inc': {'balance': 50}, '$set': {'name': update.effective_user.first_name}}, upsert=True)
            
            await update.message.reply_text(f"🎉 <b>{update.effective_user.first_name}</b> caught <b>{char['name']}</b>!", parse_mode='HTML')
            del last_spawn[chat_id]
    except: pass

async def inline_query(update: Update, context: CallbackContext):
    query = update.inline_query.query
    if not query: return
    results = await col_chars.find({'name': {'$regex': query, '$options': 'i'}}).to_list(length=50)
    answers = []
    for char in results:
        answers.append(InlineQueryResultPhoto(id=char['id'], photo_url=char['img_url'], thumbnail_url=char['img_url'], caption=f"{char['name']}", parse_mode='HTML'))
    await update.inline_query.answer(answers, cache_time=1)

# --- SERVER ---
async def web_server():
    async def handle(request): return web.Response(text="Live")
    app = web.Application(); app.router.add_get('/', handle); runner = web.AppRunner(app); await runner.setup(); site = web.TCPSite(runner, '0.0.0.0', PORT); await site.start()
    asyncio.create_task(check_auctions(app))

async def main():
    await web_server()
    app = Application.builder().token(TOKEN).build()
    app.add_error_handler(error_handler)
    handlers = [
        CommandHandler("start", start), CommandHandler("rupload", rupload), CommandHandler("addshop", addshop),
        CommandHandler("delete", delete), CommandHandler("changetime", changetime), CommandHandler("bcast", bcast),
        CommandHandler("addadmin", add_admin), CommandHandler("rmadmin", rm_admin), CommandHandler("rupdate", rupdate),
        CommandHandler("stats", stats),
        CommandHandler("balance", balance), CommandHandler("daily", daily), CommandHandler("gift", gift),
        CommandHandler("trade", trade), CommandHandler("top", top), CommandHandler("shop", shop),
        CommandHandler("rclaim", rclaim), CommandHandler("check", check), CommandHandler("fav", fav),
        CommandHandler("harem", harem), CommandHandler("profile", profile), CommandHandler("marry", marry),
        CommandHandler("burn", burn), CommandHandler("divorce", divorce), CommandHandler("auction", auction),
        CommandHandler("bid", bid), CommandHandler("createclan", createclan), CommandHandler("joinclan", joinclan),
        CommandHandler("feed", feed), CommandHandler("coinflip", coinflip), CommandHandler("dice", dice),
        CommandHandler("guess", guess),
        CallbackQueryHandler(harem_callback, pattern="^h_"), CallbackQueryHandler(shop_callback, pattern="^(shop|buy)"),
        CallbackQueryHandler(help_menu, pattern="help_menu"),
        InlineQueryHandler(inline_query), MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
    ]
    for h in handlers: app.add_handler(h)
    await app.initialize(); await app.start(); await app.updater.start_polling(); await asyncio.Event().wait()

if __name__ == "__main__": asyncio.run(main())
