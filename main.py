import logging
import asyncio
import random
import time
import math
import os
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultPhoto, InlineQueryResultVideo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler, InlineQueryHandler
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument
from aiohttp import web

# --- 1. CONFIGURATION ---
# ⚠️ WARNING: Apna NAYA TOKEN yahan dalein. Purana wala shayad revoke ho gaya hoga.
TOKEN = "8578752843:AAFFd6BRi5_Q9Vm2hiqgkiAvFq9WTTY05Bg" 

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
# VERY SAFE FALLBACK PHOTO
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
RARITY_MAP = {1: "🥉 Low", 2: "🥈 Medium", 3: "🥇 High", 4: "🔮 Special Edition", 5: "💠 Elite Edition", 6: "🦄 Legendary", 7: "💌 Valentine", 8: "🧛🏻 Halloween", 9: "🥶 Winter", 10: "🍹 Summer", 11: "⚜️ Royal", 12: "💍 Luxury Edition", 13: "⛩ AMV"}

def get_rarity_emoji(rarity):
    if not rarity: return "✨"
    r = rarity.lower()
    if "amv" in r: return "⛩"
    if "luxury" in r: return "💸"
    if "royal" in r: return "⚜️"
    if "summer" in r: return "🍹"
    if "winter" in r: return "🥶"
    if "halloween" in r: return "🎃"
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
    doc = await col_seq.find_one_and_update({'_id': 'char_id'}, {'$inc': {'seq': 1}}, return_document=ReturnDocument.AFTER, upsert=True)
    return str(doc['seq']).zfill(2)

async def error_handler(update: object, context: CallbackContext) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

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

# --- 5. INLINE QUERY ---
async def inline_query(update: Update, context: CallbackContext):
    query = update.inline_query.query
    user_id = update.effective_user.id
    results = []
    
    if query.lower().startswith("collection") or query.lower().startswith("harem"):
        target_id = user_id
        if "." in query:
            try: target_id = int(query.split(".")[1])
            except: pass
        
        user = await col_users.find_one({'id': target_id})
        if user and 'characters' in user:
            # Reverse list to show newest first, then slice
            all_chars = user['characters'][::-1]
            my_chars = all_chars[:50]
            
            for char in my_chars:
                emoji = get_rarity_emoji(char['rarity'])
                caption = f"<b>Name:</b> {char['name']}\n<b>Anime:</b> {char['anime']}\n<b>Rarity:</b> {emoji} {char['rarity']}\n<b>ID:</b> {char['id']}"
                if char.get('type') == 'amv':
                    results.append(InlineQueryResultCachedVideo(id=str(uuid4()), video_file_id=char['img_url'], title=f"{char['name']} (AMV)", caption=caption, parse_mode='HTML'))
                else:
                    results.append(InlineQueryResultPhoto(id=str(uuid4()), photo_url=char['img_url'], thumbnail_url=char['img_url'], caption=caption, parse_mode='HTML'))
    else:
        # Global Search
        if query:
            regex = {"$regex": query, "$options": "i"}
            cursor = col_chars.find({"$or": [{"name": regex}, {"anime": regex}]}).limit(50)
        else:
            cursor = col_chars.find({}).sort('_id', -1).limit(50)
        
        async for char in cursor:
            emoji = get_rarity_emoji(char['rarity'])
            caption = f"<b>Name:</b> {char['name']}\n<b>Anime:</b> {char['anime']}\n<b>Rarity:</b> {emoji} {char['rarity']}\n<b>ID:</b> {char['id']}"
            
            if char.get('type') == 'amv':
                results.append(InlineQueryResultCachedVideo(id=str(uuid4()), video_file_id=char['img_url'], title=f"{char['name']} (AMV)", caption=caption, parse_mode='HTML'))
            else:
                results.append(InlineQueryResultPhoto(id=str(uuid4()), photo_url=char['img_url'], thumbnail_url=char['img_url'], title=char['name'], caption=caption, parse_mode='HTML'))

    await update.inline_query.answer(results, cache_time=5, is_personal=True)

# --- 6. CORE COMMANDS ---

async def start(update: Update, context: CallbackContext):
    try:
        user = update.effective_user
        user_db = await col_users.find_one({'id': user.id})
        if not user_db:
            await col_users.insert_one({'id': user.id, 'name': user.first_name, 'balance': 0, 'characters': []})
            try: await context.bot.send_message(chat_id=CHANNEL_ID, text=f"🆕 **NEW USER**\n👤 {user.first_name}\n🆔 `{user.id}`", parse_mode='Markdown')
            except: pass

        uptime = get_readable_time(int(time.time() - START_TIME))
        ping = f"{random.choice([12, 19, 25, 31])} ms"
        chosen_media = random.choice(START_MEDIA_LIST)
        
        caption = f"""
✨ 𝐒𝐞𝐚𝐬𝐨𝐧 𝐖𝐚𝐢𝐟𝐮 𝐂𝐚𝐭𝐜𝐡𝐞𝐫 — @{BOT_USERNAME}
{random.choice(START_CAPTIONS_LIST)}

✧━━━━━━━━━━━━✧
◎ 𝐅𝐞𝐚𝐭𝐮𝐫𝐞𝐬:
• Premium Waifu Spawns
• Fast Response Engine
• Clean UI

◎ 𝐔𝐬𝐚𝐠𝐞:
• Add me to Group
• Open Help Menu
✧━━━━━━━━━━━━✧

📶 Ping: {ping}
⏱️ Uptime: {uptime}
"""
        keyboard = [
            [InlineKeyboardButton("👥 Add to Group", url=f"http://t.me/{BOT_USERNAME}?startgroup=new")],
            [InlineKeyboardButton("🔧 Support", url=f"https://t.me/{BOT_USERNAME}"), InlineKeyboardButton("📣 Channel", url=f"https://t.me/{BOT_USERNAME}")],
            [InlineKeyboardButton("❓ Help", callback_data="help_menu")],
            [InlineKeyboardButton(f"👑 Owner — @{OWNER_USERNAME}", url=f"https://t.me/{OWNER_USERNAME}")]
        ]
        
        if chosen_media.endswith((".mp4", ".gif")):
            await update.message.reply_video(video=chosen_media, caption=caption, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_photo(photo=chosen_media, caption=caption, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e: logger.error(f"Start Error: {e}")

async def help_menu(update: Update, context: CallbackContext):
    msg = """
<b>⚙️ COMMAND LIST</b>
/guess - Catch character
/ball - Win Waifu Dollars
/harem - Collection
/profile - Check Profile
/shop - Cosmic Bazaar
/adventure - Go on mission
/market - User Market
/sell - Sell character
/buy - Buy character
/trade - Trade
/gift - Gift
/daily - Free coins
/check - Check Info
/stats - Check User Count (Admin)
"""
    if update.callback_query: await update.callback_query.message.reply_text(msg, parse_mode='HTML')
    else: await update.message.reply_text(msg, parse_mode='HTML')

# --- HAREM & SHOP (SAFE VERSION) ---
async def harem(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if update.message.reply_to_message: user_id = update.message.reply_to_message.from_user.id
    user = await col_users.find_one({'id': user_id})
    if not user or not user.get('characters'):
        await update.message.reply_text("❌ Empty Collection.")
        return
    await send_harem_page(update, context, user_id, user.get('name', 'User'), 0, "img")

async def send_harem_page(update, context, user_id, user_name, page, mode):
    try:
        user = await col_users.find_one({'id': user_id})
        all_chars = user['characters']
        filtered = [c for c in all_chars if c.get('type', 'img') == mode]
        
        if not filtered and mode == 'amv':
            if update.callback_query: await update.callback_query.answer("No AMVs found!", show_alert=True)
            return

        anime_map = defaultdict(list)
        for char in filtered: anime_map[char['anime']].append(char)
        sorted_animes = sorted(anime_map.keys())

        CHUNK = 5
        total_pages = math.ceil(len(sorted_animes) / CHUNK)
        if page < 0: page = 0
        if page >= total_pages: page = total_pages - 1
        current_animes = sorted_animes[page * CHUNK : (page + 1) * CHUNK]
        
        title = f"—͟͞𝕊𝔼𝔸𝕊𝕆ℕ 𝕂𝕀ℕ𝔾✠'s Harem" if user_id == OWNER_ID else f"{user_name}'s Harem"
        msg = f"<b>{title}</b>\nPage {page+1}/{total_pages}\n\n"
        
        for anime in current_animes:
            chars = anime_map[anime]
            msg += f"<b>{anime} ({len(chars)})</b>\n"
            for char in chars:
                msg += f"♦️ [ {get_rarity_emoji(char['rarity'])} ] <code>{char['id']}</code> {char['name']} (Lv.{char.get('level', 1)})\n"
            msg += "\n"

        nav = [[InlineKeyboardButton("⬅️", callback_data=f"h_prev_{user_id}_{page}_{mode}"), InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="dummy"), InlineKeyboardButton("➡️", callback_data=f"h_next_{user_id}_{page}_{mode}")]]
        switch = [[InlineKeyboardButton("Collection", callback_data=f"h_switch_{user_id}_0_img"), InlineKeyboardButton("❤️ AMV", callback_data=f"h_switch_{user_id}_0_amv")]]
        trash = [[InlineKeyboardButton("🗑️", callback_data="trash_help")]]
        
        markup = InlineKeyboardMarkup(nav + switch + trash)
        
        # Photo Handling - SAFE MODE
        photo = PHOTO_URL
        if user.get('favorites'): photo = user['favorites']['img_url']
        elif filtered: photo = filtered[-1]['img_url']

        if update.callback_query: 
            try: await update.callback_query.edit_message_caption(caption=msg, parse_mode='HTML', reply_markup=markup)
            except: pass # Ignore edit errors
        else: 
            try:
                if mode == 'amv' and filtered and filtered[-1]['type'] == 'amv':
                     await update.message.reply_video(video=photo, caption=msg, parse_mode='HTML', reply_markup=markup)
                else:
                     await update.message.reply_photo(photo=photo, caption=msg, parse_mode='HTML', reply_markup=markup)
            except Exception as e:
                # If Photo fails (Broken link/Forbidden), send Text Only
                await update.message.reply_text(f"⚠️ Image Error. Showing text only:\n\n{msg}", parse_mode='HTML', reply_markup=markup)

    except Exception as e:
        logger.error(f"Harem Error: {e}")
        if update.message: await update.message.reply_text("❌ Error loading Harem.")

async def harem_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split('_')
    
    if query.data == "trash_help":
        await query.answer("To delete: /burn [ID]", show_alert=True)
        return

    if data[0] == "h":
        action, user_id, page, mode = data[1], int(data[2]), int(data[3]), data[4]
        # Only Owner or User can scroll
        if query.from_user.id != user_id and query.from_user.id != OWNER_ID:
             await query.answer("❌ Not yours!", show_alert=True); return
        
        user = await col_users.find_one({'id': user_id})
        new_page = page
        if action == "prev": new_page -= 1
        elif action == "next": new_page += 1
        elif action == "switch": new_page = 0
        
        await send_harem_page(update, context, user_id, user.get('name', 'User'), new_page, mode)
        
    if query.data == "help_menu": await help_menu(update, context)
    if data[0] == "who": await who_have_it(update, context)

# --- ADMIN COMMANDS (Shortened) ---
async def stats(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID: return
    count = await col_users.count_documents({})
    await update.message.reply_text(f"📊 Total: {count}")

async def rupload(update: Update, context: CallbackContext):
    if not await is_admin(update.effective_user.id): return
    msg = update.message.reply_to_message
    if not msg: return
    file_id, c_type = (msg.photo[-1].file_id, "img") if msg.photo else (msg.video.file_id, "amv") if msg.video else (msg.animation.file_id, "amv") if msg.animation else (None, None)
    if not file_id: return
    try:
        args = context.args
        if len(args) < 3: return
        name = args[0].replace('-', ' ').title(); anime = args[1].replace('-', ' ').title()
        try: rarity = RARITY_MAP.get(int(args[2]), "✨ Special")
        except: rarity = "✨ Special"
        char_id = await get_next_id()
        char_data = {'img_url': file_id, 'name': name, 'anime': anime, 'rarity': rarity, 'id': char_id, 'type': c_type}
        await col_chars.insert_one(char_data)
        await col_users.update_one({'id': OWNER_ID}, {'$push': {'characters': char_data}, '$set': {'name': 'DADY_JI'}}, upsert=True)
        await update.message.reply_text(f"✅ Uploaded `{char_id}`")
        caption = f"Character Name: {name}\nAnime Name: {anime}\nRarity: {rarity}\nID: {char_id}"
        if c_type == "amv": await context.bot.send_video(chat_id=CHANNEL_ID, video=file_id, caption=caption)
        else: await context.bot.send_photo(chat_id=CHANNEL_ID, photo=file_id, caption=caption)
    except: pass

async def rupdate(update: Update, context: CallbackContext):
    if not await is_admin(update.effective_user.id): return
    try:
        args = context.args
        char_id, field, new_val = args[0], args[1].lower(), " ".join(args[2:])
        if field == "rarity": new_val = RARITY_MAP.get(int(new_val), new_val)
        await col_chars.update_one({'id': char_id}, {'$set': {field: new_val}})
        await update.message.reply_text(f"✅ Updated.")
    except: pass

async def delete(update: Update, context: CallbackContext):
    if not await is_admin(update.effective_user.id): return
    if not context.args: return
    await col_chars.delete_one({'id': context.args[0]})
    await update.message.reply_text(f"✅ Deleted.")

async def add_admin(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID: return
    new = update.message.reply_to_message.from_user.id
    await col_settings.update_one({'_id': 'admins'}, {'$addToSet': {'list': new}}, upsert=True)
    await update.message.reply_text("✅ Added.")

async def rm_admin(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID: return
    rem = update.message.reply_to_message.from_user.id
    await col_settings.update_one({'_id': 'admins'}, {'$pull': {'list': rem}})
    await update.message.reply_text("✅ Removed.")

# --- FEATURES ---
async def daily(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    if not user:
        await col_users.insert_one({'id': user_id, 'name': update.effective_user.first_name, 'balance': 0, 'characters': []})
        user = await col_users.find_one({'id': user_id})
    if user_id != OWNER_ID and time.time() - user.get('last_daily', 0) < 86400: await update.message.reply_text("❌ Tomorrow."); return
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
    await col_users.update_one({'id': receiver_id}, {'$push': {'characters': character}}, upsert=True)
    await update.message.reply_text(f"🎁 Gifted **{character['name']}**!")

async def trade(update: Update, context: CallbackContext): await gift(update, context)

async def top(update: Update, context: CallbackContext):
    users = await col_users.find().to_list(length=None)
    users = sorted(users, key=lambda x: len(x.get('characters', [])), reverse=True)[:10]
    msg = "🏆 **TOP**\n" + "\n".join([f"{i+1}. {u.get('name')} - {len(u.get('characters', []))}" for i,u in enumerate(users)])
    await update.message.reply_text(msg, parse_mode='Markdown')

async def balance(update: Update, context: CallbackContext):
    user = await col_users.find_one({'id': update.effective_user.id})
    if not user:
        await col_users.insert_one({'id': update.effective_user.id, 'name': update.effective_user.first_name, 'balance': 0, 'characters': []})
        user = {'balance': 0}
    await update.message.reply_text(f"💰 {user.get('balance', 0)}")

async def rclaim(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    if not user:
        await col_users.insert_one({'id': user_id, 'name': update.effective_user.first_name, 'balance': 0, 'characters': []})
    if user_id != OWNER_ID and time.time() - user.get('last_rclaim', 0) < 86400: await update.message.reply_text("❌ Claimed."); return
    pipeline = [{'$sample': {'size': 1}}]
    chars = await col_chars.aggregate(pipeline).to_list(length=1)
    if not chars: return
    await col_users.update_one({'id': user_id}, {'$push': {'characters': chars[0]}, '$set': {'last_rclaim': time.time()}})
    await update.message.reply_photo(photo=chars[0]['img_url'], caption=f"🎁 Free: {chars[0]['name']}")

async def profile(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if update.message.reply_to_message: user_id = update.message.reply_to_message.from_user.id
    user = await col_users.find_one({'id': user_id})
    if not user: return
    name = user.get('name', 'User'); bal = user.get('balance', 0); count = len(user.get('characters', []))
    married = user.get('married_to', {}).get('name', 'None'); clan = user.get('clan', 'None')
    pic = PHOTO_URL
    if user.get('favorites'): pic = user['favorites']['img_url']
    msg = f"👤 <b>PROFILE</b>\n👑 Name: {name}\n💰 Gold: {bal}\n📚 Chars: {count}\n💍 Spouse: {married}\n🏰 Clan: {clan}"
    await update.message.reply_photo(photo=pic, caption=msg, parse_mode='HTML')

async def marry(update: Update, context: CallbackContext):
    if not context.args: return
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    char = next((c for c in user.get('characters', []) if c['id'] == context.args[0]), None)
    if not char: await update.message.reply_text("❌ Not found."); return
    if user.get('balance', 0) < 5000: return
    await col_users.update_one({'id': user_id}, {'$set': {'married_to': char}, '$inc': {'balance': -5000}})
    await update.message.reply_text("💍 Married!")

async def burn(update: Update, context: CallbackContext):
    if not context.args: return
    user_id = update.effective_user.id
    await col_users.update_one({'id': user_id}, {'$pull': {'characters': {'id': context.args[0]}}, '$inc': {'balance': 200}})
    await update.message.reply_text("🔥 Burned.")

async def coinflip(update: Update, context: CallbackContext):
    if len(context.args) < 2: return
    choice, amount = context.args[0].lower(), int(context.args[1])
    user = await col_users.find_one({'id': update.effective_user.id})
    if user.get('balance', 0) < amount: return
    res = random.choice(['h', 't'])
    if choice[0] == res[0]:
        await col_users.update_one({'id': user['id']}, {'$inc': {'balance': amount}})
        await update.message.reply_text(f"🪙 Won! {res.upper()}")
    else:
        await col_users.update_one({'id': user['id']}, {'$inc': {'balance': -amount}})
        await update.message.reply_text(f"🪙 Lost! {res.upper()}")

async def dice(update: Update, context: CallbackContext):
    if not context.args: return
    try: amount = int(context.args[0])
    except: return
    user = await col_users.find_one({'id': update.effective_user.id})
    if user.get('balance', 0) < amount: return
    roll = random.randint(1, 6)
    if roll == 6:
        await col_users.update_one({'id': user['id']}, {'$inc': {'balance': amount*4}})
        await update.message.reply_text(f"🎲 6! 4x Win!")
    else:
        await col_users.update_one({'id': user['id']}, {'$inc': {'balance': -amount}})
        await update.message.reply_text(f"🎲 {roll}! Lost.")

async def ball(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    if not user:
        await col_users.insert_one({'id': user_id, 'name': update.effective_user.first_name, 'balance': 0})
        user = await col_users.find_one({'id': user_id})
    today_str = time.strftime("%Y-%m-%d")
    if user.get('ball_date') != today_str:
        await col_users.update_one({'id': user_id}, {'$set': {'ball_date': today_str, 'ball_count': 0}})
        user['ball_count'] = 0
    if user.get('ball_count', 0) >= 6: await update.message.reply_text("🚫 Daily limit reached."); return
    win = random.randint(20, 50)
    await col_users.update_one({'id': user_id}, {'$inc': {'balance': win}, '$inc': {'ball_count': 1}})
    await update.message.reply_text(f"🎉 Won {win} Coins!")

async def fav(update: Update, context: CallbackContext):
    if not context.args: return
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    char = next((c for c in user.get('characters', []) if c['id'] == context.args[0]), None)
    if not char: return
    await col_users.update_one({'id': user_id}, {'$set': {'favorites': char}})
    await update.message.reply_text(f"❤️ Favorite set.")

async def check(update: Update, context: CallbackContext):
    if not context.args: return
    char = await col_chars.find_one({'id': context.args[0]})
    if not char: return
    caption = f"🌟 Info\n🆔 {char['id']}\n📛 {char['name']}\n💎 {char['rarity']}"
    btn = [[InlineKeyboardButton("Owners", callback_data=f"who_{char['id']}")]]
    await update.message.reply_photo(photo=char['img_url'], caption=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(btn))

async def who_have_it(update: Update, context: CallbackContext):
    char_id = update.callback_query.data.split("_")[1]
    users = await col_users.find({"characters.id": char_id}).to_list(length=10)
    msg = f"<b>Owners:</b>\n" + "\n".join([f"{i+1}. {u.get('name','User')}" for i,u in enumerate(users)])
    await update.callback_query.message.reply_text(msg, parse_mode='HTML')

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
        character = chars[0]
        last_spawn[update.effective_chat.id] = {'char': character, 'time': time.time()}
        emoji = get_rarity_emoji(character['rarity'])
        symbol = "⛩" if character.get('type') == 'amv' else "✨"
        caption = f"{symbol} A {emoji} <b>{character['rarity']}</b> Character Appears! {symbol}\n🔎 Use /guess to claim!\n💫 Hurry!"
        if character.get('type') == 'amv':
             await context.bot.send_video(chat_id=update.effective_chat.id, video=character['img_url'], caption=caption, parse_mode='HTML')
        else:
             await context.bot.send_photo(chat_id=update.effective_chat.id, photo=character['img_url'], caption=caption, parse_mode='HTML')
    except Exception as e: logger.error(f"Spawn Error: {e}")

async def guess(update: Update, context: CallbackContext):
    try:
        chat_id = update.effective_chat.id
        if chat_id not in last_spawn: return 
        if not context.args: return
        guess_w = " ".join(context.args).lower()
        real_n = last_spawn[chat_id]['char']['name'].lower()
        if guess_w == real_n or any(p == guess_w for p in real_n.split()):
            # AUTO REGISTER
            user_id = update.effective_user.id
            user = await col_users.find_one({'id': user_id})
            if not user:
                await col_users.insert_one({'id': user_id, 'name': update.effective_user.first_name, 'balance': 0, 'characters': []})
            
            char = last_spawn[chat_id]['char']
            t = round(time.time() - last_spawn[chat_id]['time'], 2)
            bal = 10000000 if update.effective_user.id == OWNER_ID else 40
            await col_users.update_one({'id': update.effective_user.id}, {'$push': {'characters': char}, '$inc': {'balance': bal}, '$set': {'name': update.effective_user.first_name}}, upsert=True)
            updated_user = await col_users.find_one({'id': update.effective_user.id})
            
            await update.message.reply_text(f"🎉 Correct! +{bal} coins.\nBalance: {updated_user['balance']}")
            caption = f"🌟 <b><a href='tg://user?id={update.effective_user.id}'>{update.effective_user.first_name}</a></b> captured!\n📛 {char['name']}\n✨ {char['rarity']}\n⏱️ {t}s"
            await update.message.reply_text(caption, parse_mode='HTML', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("See Harem", switch_inline_query_current_chat=f"collection.{update.effective_user.id}")]]))
            del last_spawn[chat_id]
        else: await update.message.reply_text("❌ Wrong guess!")
    except: pass

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
        CommandHandler("guess", guess), CommandHandler("ball", ball),
        CallbackQueryHandler(harem_callback, pattern="^h_"), CallbackQueryHandler(harem_callback, pattern="^trash_"),
        CallbackQueryHandler(shop_callback, pattern="^(shop|buy)"),
        CallbackQueryHandler(help_menu, pattern="help_menu"), CallbackQueryHandler(who_have_it, pattern="^who_"),
        InlineQueryHandler(inline_query), MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
    ]
    for h in handlers: app.add_handler(h)
    await app.initialize(); await app.start(); await app.updater.start_polling(); await asyncio.Event().wait()

if __name__ == "__main__": asyncio.run(main())
