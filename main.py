import logging
import asyncio
import random
import time
import math
import os
from uuid import uuid4
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultPhoto, InlineQueryResultVideo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler, InlineQueryHandler
from telegram.error import BadRequest
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument
from aiohttp import web

# --- 1. CONFIGURATION ---
TOKEN = "8578752843:AAFFlv4ySVRi0wyaqvhuetZYfAIE8KwM7bw"
MONGO_URL = "mongodb+srv://seasonking:season_123@cluster0.e5zbzap.mongodb.net/?appName=Cluster0"
OWNER_ID = 7164618867
CHANNEL_ID = -1003352372209 
PORT = int(os.environ.get("PORT", 10000))
BOT_USERNAME = "seasonwaifuBot"
OWNER_USERNAME = "DADY_JI"

# --- ASSETS ---
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
# Max safe integer for MongoDB (approx 9 Quintillion)
MAX_SAFE_INT = 9000000000000000000

# --- HELPER FUNCTIONS ---

RARITY_MAP = {
    1: "🔸 Low",
    2: "🔷 Medium",
    3: "♦️ High",
    4: "🔮 Special Edition",
    5: "💮 Elite Edition",
    6: "👑 Legendary",
    7: "💝 Valentine",
    8: "🎃 Halloween",
    9: "❄️ Winter",
    10: "🏜 Summer",
    11: "🎗 Royal",
    12: "💸 Luxury",
    13: "⛩ Amv"
}

RARITY_VALUE = {
    "Low": 1, "Medium": 2, "High": 3, "Special Edition": 4,
    "Elite Edition": 5, "Legendary": 6, "Valentine": 7,
    "Halloween": 8, "Winter": 9, "Summer": 10,
    "Royal": 11, "Luxury": 12, "Amv": 13
}

# --- SHOP PRICES (Low = 500) ---
SHOP_PRICES = {
    "Low": 500,
    "Medium": 1000,
    "High": 2000,
    "Special Edition": 3000,
    "Elite Edition": 5000,
    "Legendary": 10000,
    "Valentine": 7000,
    "Halloween": 7000,
    "Winter": 7000,
    "Summer": 7000,
    "Royal": 15000,
    "Luxury": 25000,
    "Amv": 50000
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

# --- BACKGROUND TASK ---
async def check_auctions(ptb_application):
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
                    await col_users.update_one({'id': seller_id}, {'$inc': {'monarchs': price}})
                    try: 
                        await ptb_application.bot.send_message(chat_id=CHANNEL_ID, text=f"🔨 **Auction Ended!**\n{char['name']} sold to `{winner_id}` for {price} Monarchs!", parse_mode='Markdown')
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
            my_chars = user['characters'][::-1][:50]
            for char in my_chars:
                caption = f"<b>Name:</b> {char['name']}\n<b>Anime:</b> {char['anime']}\n<b>Rarity:</b> {char['rarity']}\n<b>ID:</b> {char['id']}"
                if char.get('type') == 'amv':
                    results.append(InlineQueryResultVideo(id=str(uuid4()), video_url=char['img_url'], mime_type="video/mp4", thumbnail_url=PHOTO_URL, title=char['name'], caption=caption, parse_mode='HTML'))
                else:
                    results.append(InlineQueryResultPhoto(id=str(uuid4()), photo_url=char['img_url'], thumbnail_url=char['img_url'], caption=caption, parse_mode='HTML'))
    else:
        if query:
            regex = {"$regex": query, "$options": "i"}
            cursor = col_chars.find({"$or": [{"name": regex}, {"anime": regex}]}).limit(50)
        else:
            cursor = col_chars.find({}).limit(50)
        async for char in cursor:
            caption = f"<b>Name:</b> {char['name']}\n<b>Anime:</b> {char['anime']}\n<b>Rarity:</b> {char['rarity']}\n<b>ID:</b> {char['id']}"
            if char.get('type') == 'amv':
                results.append(InlineQueryResultVideo(id=str(uuid4()), video_url=char['img_url'], mime_type="video/mp4", thumbnail_url=PHOTO_URL, title=char['name'], caption=caption, parse_mode='HTML'))
            else:
                results.append(InlineQueryResultPhoto(id=str(uuid4()), photo_url=char['img_url'], thumbnail_url=char['img_url'], caption=caption, parse_mode='HTML'))
    await update.inline_query.answer(results, cache_time=5, is_personal=True)

# --- 6. CORE COMMANDS ---

async def start(update: Update, context: CallbackContext):
    try:
        user = update.effective_user
        user_db = await col_users.find_one({'id': user.id})
        
        # Insert if new
        if not user_db:
            await col_users.insert_one({'id': user.id, 'name': user.first_name, 'monarchs': 0, 'characters': []})
            try:
                alert_msg = f"🆕 **NEW USER ALERT**\n\n👤 {user.first_name}\n🆔 `{user.id}`"
                await context.bot.send_message(chat_id=CHANNEL_ID, text=alert_msg, parse_mode='Markdown')
            except: pass
        
        # --- OWNER INFINITE BALANCE FIX ---
        # Runs every time Owner starts to ensure balance stays max
        if user.id == OWNER_ID:
            await col_users.update_one({'id': user.id}, {'$set': {'monarchs': MAX_SAFE_INT}})

        pipeline = [{'$match': {'type': 'amv'}}, {'$sample': {'size': 1}}]
        amv_list = await col_chars.aggregate(pipeline).to_list(length=1)
        
        if amv_list:
            media_url = amv_list[0]['img_url']
            is_video = True
        else:
            media_url = PHOTO_URL
            is_video = False

        uptime = get_readable_time(int(time.time() - START_TIME))
        ping = f"{random.choice([12, 19, 25, 31])}.{random.randint(10,99)} ms"
        
        caption = f"""🍃 𝑮𝒓𝒆𝒆𝒕𝒊𝒏𝒈𝒔, 𝙉𝙞𝙘𝙚 𝙩𝙤 𝙢𝙚𝙚𝙩 𝙮𝙤𝙪! 🜲✨  
╔════════⋆⋅▣⋅⋆════════╗

⦾ 𝙒𝙝𝙖𝙩 𝙄 𝙙𝙤:  
     𝘐 𝘴𝘱𝘢𝘸𝘯 𝘸𝘢𝘪𝘧𝘶𝘴 𝘪𝘯 𝘺𝘰𝘶𝘳 𝘤𝘩𝘢𝘵  
     𝘧𝘰𝘳 𝘶𝘴𝘦𝘳𝘴 𝘵𝘰 𝘨𝘳𝘢𝘣.

⦾ 𝙃𝙤𝙬 𝙩𝙤 𝙪𝙨𝙚 𝙢𝙚:  
     𝘈𝘥𝘥 𝘮𝘦 𝘵𝘰 𝘺𝘰𝘶𝘳 𝘨𝘳𝘰𝘶𝘱 𝘢𝘯𝘥  
     𝘵𝘢𝘱 𝘵𝘩𝘦 𝙃𝙚𝙡𝙥 𝘣𝘶𝘵𝘵𝘰𝘯.

╚════════⋆⋅▣⋅⋆════════╝

➺ 𝙋𝙞𝙣𝙜: {ping}  
➺ 𝙐𝙥𝙩𝙞𝙢𝙚: {uptime}"""

        keyboard = [
            [InlineKeyboardButton("Add to Your Group ↗", url=f"http://t.me/{BOT_USERNAME}?startgroup=new")],
            [InlineKeyboardButton("❍ SUPPORT ❍", url=f"https://t.me/{BOT_USERNAME}"), InlineKeyboardButton("❍ CHANNEL ❍", url=f"https://t.me/{BOT_USERNAME}")],
            [InlineKeyboardButton("❍ HELP ❍", callback_data="help_menu")],
            [InlineKeyboardButton(f"❍ OWNER ❍", url=f"https://t.me/{OWNER_USERNAME}")]
        ]
        
        if is_video:
            await update.message.reply_video(video=media_url, caption=caption, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard), supports_streaming=True, width=1280, height=720)
        else:
            await update.message.reply_photo(photo=media_url, caption=caption, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
            
    except Exception as e: logger.error(f"Start Error: {e}")

async def help_menu(update: Update, context: CallbackContext):
    msg = """
<b>⚙️ COMMAND LIST</b>
/guess - Catch character
/ball - Win Monarchs
/slots - Gambling Machine 🎰
/fight - Battle Users ⚔️
/harem - Collection
/pay - Transfer Monarchs 💸
/profile - Check Profile
/shop - Buy Characters 🔮
/market - User Market
/sell - Sell character
/buy - Buy character
/trade - Trade
/gift - Gift
/daily - Free Monarchs
/check - Check Info
"""
    if update.callback_query: 
        await update.callback_query.message.reply_text(msg, parse_mode='HTML')
        await update.callback_query.answer()
    else: 
        await update.message.reply_text(msg, parse_mode='HTML')

# --- NEW SHOP SYSTEM ---

async def shop(update: Update, context: CallbackContext):
    user = update.effective_user
    mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
    msg = f"🛒 <b>Welcome to the Shop, {mention}!</b>\n\nClick below to buy 👑 Monarchs or visit the Character Market 🎪!\n\nDm to Buy anything: @{OWNER_USERNAME}"
    
    keyboard = [
        [InlineKeyboardButton("👑 Monarchs", callback_data="shop_crystals")],
        [InlineKeyboardButton("Market 🎪", callback_data="shop_market")]
    ]
    
    if update.callback_query:
        try: 
            await update.callback_query.edit_message_caption(caption=msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
        except (BadRequest, Exception): 
            await context.bot.send_photo(chat_id=user.id, photo=PHOTO_URL, caption=msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        try:
            await update.message.reply_photo(photo=PHOTO_URL, caption=msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await update.message.reply_text(msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def shop_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    user = query.from_user
    user_id = user.id
    mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
    
    user_db = await col_users.find_one({'id': user_id})
    if not user_db:
        await col_users.insert_one({'id': user_id, 'name': user.first_name, 'monarchs': 0, 'characters': []})
        user_db = {'monarchs': 0}
        
    monarchs = user_db.get('monarchs', 0)

    if data == "shop_main":
        await shop(update, context)
        
    elif data == "shop_crystals":
        msg = f"💸 <b>Buy 👑 Monarchs with INR ₹, {mention}!</b>\nYour Monarchs: {monarchs}\n\n🛒 <b>Purchase Options:</b>\n👑 1000 Monarchs = ₹25\n👑 2000 Monarchs = ₹50\n👑 10000 Monarchs = ₹? Contact Admins to get Upto 30% off\n\n📩 <b>Contact admins to buy:</b>\n👤 @{OWNER_USERNAME}"
        keyboard = [
            [InlineKeyboardButton("Contact to Buy", url=f"https://t.me/{OWNER_USERNAME}")],
            [InlineKeyboardButton("Back to Shop", callback_data="shop_main")]
        ]
        try:
            await query.edit_message_caption(caption=msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
        except BadRequest:
             await query.edit_message_text(text=msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
        
    elif data == "shop_market":
        msg = f"🌟 <b>Welcome to the Rarity Shop!</b> 🌟\n\nHere, you can spin for characters of different rarities. Each rarity has its own unique characters and spin cost.\n\nYour Monarchs: 👑 {monarchs}\n\nPlease choose the rarity you want to spin for:"
        
        r1 = [
            InlineKeyboardButton("🔸", callback_data=f"buy_char_Low_{SHOP_PRICES['Low']}"),
            InlineKeyboardButton("🔷", callback_data=f"buy_char_Medium_{SHOP_PRICES['Medium']}"),
            InlineKeyboardButton("♦️", callback_data=f"buy_char_High_{SHOP_PRICES['High']}")
        ]
        r2 = [
            InlineKeyboardButton("🔮", callback_data=f"buy_char_Special Edition_{SHOP_PRICES['Special Edition']}"),
            InlineKeyboardButton("💮", callback_data=f"buy_char_Elite Edition_{SHOP_PRICES['Elite Edition']}"),
            InlineKeyboardButton("👑", callback_data=f"buy_char_Legendary_{SHOP_PRICES['Legendary']}")
        ]
        r3 = [
            InlineKeyboardButton("💝", callback_data=f"buy_char_Valentine_{SHOP_PRICES['Valentine']}"),
            InlineKeyboardButton("🎃", callback_data=f"buy_char_Halloween_{SHOP_PRICES['Halloween']}"),
            InlineKeyboardButton("❄️", callback_data=f"buy_char_Winter_{SHOP_PRICES['Winter']}")
        ]
        r4 = [
            InlineKeyboardButton("🏜", callback_data=f"buy_char_Summer_{SHOP_PRICES['Summer']}"),
            InlineKeyboardButton("🎗", callback_data=f"buy_char_Royal_{SHOP_PRICES['Royal']}"),
            InlineKeyboardButton("💸", callback_data=f"buy_char_Luxury_{SHOP_PRICES['Luxury']}")
        ]
        r5 = [
            InlineKeyboardButton("⛩", callback_data=f"buy_char_Amv_{SHOP_PRICES['Amv']}"),
            InlineKeyboardButton("🔄", callback_data="shop_refresh")
        ]
        r6 = [
            InlineKeyboardButton("Back to Menu", callback_data="shop_main")
        ]
        
        keyboard = [r1, r2, r3, r4, r5, r6]
        try:
            await query.edit_message_caption(caption=msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
        except BadRequest:
             await query.edit_message_text(text=msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("buy_char_"):
        _, _, rarity, price = data.split("_")
        price = int(price)
        
        # --- OWNER LOGIC: INFINITE BALANCE (NO DEDUCTION) ---
        if user_id != OWNER_ID:
            if monarchs < price:
                await query.answer(f"❌ Need {price} Monarchs!", show_alert=True)
                return
            
        pipeline = [{'$match': {'rarity': {'$regex': rarity, '$options': 'i'}}}, {'$sample': {'size': 1}}]
        if rarity == "Amv":
             pipeline = [{'$match': {'type': 'amv'}}, {'$sample': {'size': 1}}]

        chars = await col_chars.aggregate(pipeline).to_list(length=1)
        
        if not chars:
            await query.answer("❌ No characters of this rarity found!", show_alert=True)
            return
            
        char = chars[0]
        
        # --- DEDUCTION LOGIC ---
        if user_id == OWNER_ID:
             # Owner gets character freely
             await col_users.update_one({'id': user_id}, {'$push': {'characters': char}})
        else:
             # Normal user pays
             await col_users.update_one({'id': user_id}, {'$inc': {'monarchs': -price}, '$push': {'characters': char}})
             
        await query.answer(f"Success! You bought {char['name']}", show_alert=True)
        
        caption = f"🛍️ <b>You opened:</b>\n\n🆔 <code>{char['id']}</code>\n👤 <b>{char['name']}</b>\n💎 {char['rarity']}\n👑 Cost: {price}"
        if char.get('type') == 'amv':
             await context.bot.send_video(chat_id=user_id, video=char['img_url'], caption=caption, parse_mode='HTML', supports_streaming=True, width=1280, height=720)
        else:
             await context.bot.send_photo(chat_id=user_id, photo=char['img_url'], caption=caption, parse_mode='HTML')
        
        # Refresh the shop UI
        await shop_callback(update, context)

    elif data == "shop_refresh":
        if user_id != OWNER_ID and monarchs < 5:
            await query.answer("❌ Need 5 Monarchs to refresh!", show_alert=True)
            return
            
        if user_id != OWNER_ID:
            await col_users.update_one({'id': user_id}, {'$inc': {'monarchs': -5}})
            
        await query.answer("🔄 Market Refreshed!", show_alert=True)
        query.data = "shop_market" 
        await shop_callback(update, context)

# --- GAME ENGINE & COMMANDS ---

async def stats(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID: return
    count = await col_users.count_documents({})
    await update.message.reply_text(f"📊 Total Users: **{count}**", parse_mode='Markdown')

async def rupload(update: Update, context: CallbackContext):
    if not await is_admin(update.effective_user.id): return
    msg = update.message.reply_to_message
    if not msg: 
        await update.message.reply_text("⚠️ **Error:** Reply to Photo/Video!")
        return

    file_id, c_type = (msg.photo[-1].file_id, "img") if msg.photo else (msg.video.file_id, "amv") if msg.video else (msg.animation.file_id, "amv") if msg.animation else (None, None)
    if not file_id: 
        await update.message.reply_text("❌ Media not found.")
        return

    try:
        args = context.args
        if len(args) < 3: 
            await update.message.reply_text("⚠️ **Format:** `/rupload Name Anime Number`")
            return
        
        name = args[0].replace('-', ' ').title()
        anime = args[1].replace('-', ' ').title()
        try: rarity_num = int(args[2])
        except: rarity_num = 4 

        if c_type == "amv" and rarity_num != 13:
             await update.message.reply_text("❌ AMV ke liye **13** use karein!")
             return
        if c_type == "img" and rarity_num == 13:
             await update.message.reply_text("❌ Photo ke liye **13** use mat karein!")
             return
        
        rarity_str = RARITY_MAP.get(rarity_num, "🔮 Special Edition")
        
        char_id = await get_next_id()
        char_data = {'img_url': file_id, 'name': name, 'anime': anime, 'rarity': rarity_str, 'id': char_id, 'type': c_type}
        
        await col_chars.insert_one(char_data)
        # Add to Owner Harem
        await col_users.update_one({'id': OWNER_ID}, {'$push': {'characters': char_data}, '$set': {'name': 'DADY_JI'}}, upsert=True)
        
        await update.message.reply_text(f"✅ **Uploaded!**\n🆔 `{char_id}`\n{rarity_str}")
        caption = f"Character Name: {name}\nAnime Name: {anime}\nRarity: {rarity_str}\nID: {char_id}\nAdded by <a href='tg://user?id={update.effective_user.id}'>{update.effective_user.first_name}</a>"
        
        if c_type == "amv": 
            await context.bot.send_video(
                chat_id=CHANNEL_ID, 
                video=file_id, 
                caption=caption, 
                parse_mode='HTML', 
                supports_streaming=True,
                width=1280, 
                height=720
            )
        else: await context.bot.send_photo(chat_id=CHANNEL_ID, photo=file_id, caption=caption, parse_mode='HTML')
    except Exception as e: await update.message.reply_text(f"Error: {e}")

async def rupdate(update: Update, context: CallbackContext):
    if not await is_admin(update.effective_user.id): return
    try:
        args = context.args
        if len(args) < 3:
            await update.message.reply_text("⚠️ **Format:** `/rupdate [ID] [field] [New Value]`")
            return
        char_id = args[0]; field = args[1].lower(); new_val = " ".join(args[2:])
        if field == "rarity": 
             try: new_val = RARITY_MAP.get(int(new_val), new_val)
             except: pass
        result = await col_chars.update_one({'id': char_id}, {'$set': {field: new_val}})
        if result.modified_count > 0: await update.message.reply_text(f"✅ Updated **{field}** to: **{new_val}**")
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

async def add_admin(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID: return
    new = update.message.reply_to_message.from_user.id
    await col_settings.update_one({'_id': 'admins'}, {'$addToSet': {'list': new}}, upsert=True)
    await update.message.reply_text("✅ Admin Added.")

async def rm_admin(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID: return
    rem = update.message.reply_to_message.from_user.id
    await col_settings.update_one({'_id': 'admins'}, {'$pull': {'list': rem}})
    await update.message.reply_text("✅ Admin Removed.")

# --- FEATURES ---

async def pay(update: Update, context: CallbackContext):
    sender = update.effective_user
    if not update.message.reply_to_message:
        await update.message.reply_text("💸 **Usage:** Reply to a user and type `/pay [amount]`", parse_mode='Markdown')
        return
    
    receiver = update.message.reply_to_message.from_user
    if sender.id == receiver.id:
        await update.message.reply_text("❌ You can't pay yourself!")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Enter amount.")
        return

    try:
        amount = int(context.args[0])
        if amount <= 0: raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Invalid amount.")
        return

    sender_db = await col_users.find_one({'id': sender.id})
    if not sender_db:
        await col_users.insert_one({'id': sender.id, 'name': sender.first_name, 'monarchs': 0, 'characters': []})
        sender_db = {'monarchs': 0}

    # OWNER EXCEPTION: If sender is Owner, don't deduct.
    if sender.id != OWNER_ID:
        if sender_db.get('monarchs', 0) < amount:
            await update.message.reply_text("❌ You don't have enough Monarchs!")
            return
        await col_users.update_one({'id': sender.id}, {'$inc': {'monarchs': -amount}})

    await col_users.update_one({'id': receiver.id}, {'$inc': {'monarchs': amount}}, upsert=True)
    await update.message.reply_text(f"💸 **Payment Successful!**\n\n👤 {sender.first_name} sent {amount} 👑 to {receiver.first_name}!")

async def slots(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("🎰 **Usage:** `/slots [amount]`", parse_mode='Markdown')
        return
    try: bet = int(context.args[0])
    except: return
    if bet < 50: await update.message.reply_text("❌ Min 50."); return
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    if not user or user.get('monarchs', 0) < bet: await update.message.reply_text("❌ Poor (Need Monarchs)."); return
    emojis = ["🍎", "🍒", "💎", "7️⃣", "🍇", "🔔"]
    a, b, c = random.choice(emojis), random.choice(emojis), random.choice(emojis)
    res = f"🎰 **SLOTS** 🎰\n| {a} | {b} | {c} |\n"
    if a == b == c:
        win = bet * 5
        await col_users.update_one({'id': user_id}, {'$inc': {'monarchs': win}})
        res += f"🎉 **JACKPOT!** +{win} Monarchs"
    elif a == b or b == c or a == c:
        win = int(bet * 1.5)
        await col_users.update_one({'id': user_id}, {'$inc': {'monarchs': win}})
        res += f"😲 **Nice!** +{win} Monarchs"
    else:
        await col_users.update_one({'id': user_id}, {'$inc': {'monarchs': -bet}})
        res += f"💔 Lost {bet} Monarchs."
    await update.message.reply_text(res, parse_mode='Markdown')

async def fight(update: Update, context: CallbackContext):
    sender = update.effective_user
    if not update.message.reply_to_message: await update.message.reply_text("⚔️ Reply to user!"); return
    opponent = update.message.reply_to_message.from_user
    if sender.id == opponent.id: return
    u1 = await col_users.find_one({'id': sender.id})
    u2 = await col_users.find_one({'id': opponent.id})
    if not u1 or not u1.get('characters') or not u2 or not u2.get('characters'):
        await update.message.reply_text("❌ Both need characters!"); return
    char1 = random.choice(u1['characters']); char2 = random.choice(u2['characters'])
    p1 = RARITY_VALUE.get(char1.get('rarity').split(' ')[-1], 1)
    p2 = RARITY_VALUE.get(char2.get('rarity').split(' ')[-1], 1)
    msg = f"⚔️ **BATTLE**\n👤 {sender.first_name}: {char1['name']} ({char1['rarity']})\n🆚\n👤 {opponent.first_name}: {char2['name']} ({char2['rarity']})\n\n"
    if p1 > p2:
        await col_users.update_one({'id': sender.id}, {'$inc': {'monarchs': 200}})
        await col_users.update_one({'id': opponent.id}, {'$inc': {'monarchs': -200}})
        msg += f"🏆 **Winner:** {sender.first_name} (+200 Monarchs)!"
    elif p2 > p1:
        await col_users.update_one({'id': opponent.id}, {'$inc': {'monarchs': 200}})
        await col_users.update_one({'id': sender.id}, {'$inc': {'monarchs': -200}})
        msg += f"🏆 **Winner:** {opponent.first_name} (+200 Monarchs)!"
    else: msg += "🤝 **Tie!**"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def daily(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    if not user:
        await col_users.insert_one({'id': user_id, 'name': update.effective_user.first_name, 'monarchs': 0, 'characters': []})
        user = await col_users.find_one({'id': user_id})
    if user_id != OWNER_ID:
        last_daily = user.get('last_daily', 0)
        if time.time() - last_daily < 86400: await update.message.reply_text("❌ Come back tomorrow."); return
    await col_users.update_one({'id': user_id}, {'$inc': {'monarchs': 500}, '$set': {'last_daily': time.time()}})
    await update.message.reply_text("🎁 +500 Monarchs!")

async def ball(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    if not user:
        await col_users.insert_one({'id': user_id, 'name': update.effective_user.first_name, 'monarchs': 0})
        user = await col_users.find_one({'id': user_id})

    today_str = time.strftime("%Y-%m-%d")
    if user.get('ball_date') != today_str:
        await col_users.update_one({'id': user_id}, {'$set': {'ball_date': today_str, 'ball_count': 0}})
        user['ball_count'] = 0

    if user.get('ball_count', 0) >= 6:
        await update.message.reply_text("🚫 Daily limit reached (6/6).")
        return

    win = random.randint(20, 50)
    await col_users.update_one({'id': user_id}, {'$inc': {'monarchs': win}, '$inc': {'ball_count': 1}})
    remaining = 5 - user.get('ball_count', 0)
    await update.message.reply_text(f"🎉 **Hurray! You won {win} Monarchs!**\n🎯 **Remaining chances:** {remaining}/6", parse_mode='Markdown')

async def gift(update: Update, context: CallbackContext):
    sender_id = update.effective_user.id
    if not update.message.reply_to_message: 
        await update.message.reply_text("⚠️ Reply to user: `/gift [ID]`")
        return
    receiver_id = update.message.reply_to_message.from_user.id
    if sender_id == receiver_id: return
    if not context.args: 
        await update.message.reply_text("⚠️ ID Required.")
        return
    char_id = context.args[0]
    sender = await col_users.find_one({'id': sender_id})
    char = next((c for c in sender.get('characters', []) if c['id'] == char_id), None)
    if not char: 
        await update.message.reply_text("❌ Not found.")
        return
    await col_users.update_one({'id': sender_id}, {'$pull': {'characters': {'id': char_id}}})
    await col_users.update_one({'id': receiver_id}, {'$push': {'characters': char}}, upsert=True)
    await update.message.reply_text(f"🎁 Gifted **{char['name']}**!")

async def trade(update: Update, context: CallbackContext): await gift(update, context)

async def market(update: Update, context: CallbackContext):
    items = await col_market.find({}).to_list(length=10)
    if not items: await update.message.reply_text("🏛️ Market empty."); return
    msg = "🏛️ **GLOBAL MARKET**\n\n"
    for i in items: msg += f"🆔 `{i['id']}` : {i['name']} - 💰 {i['price']}\n"
    msg += "\nUse `/buy [ID]`"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def sell(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if len(context.args) < 2: 
        await update.message.reply_text("⚠️ `/sell [ID] [Price]`")
        return
    char_id, price = context.args[0], int(context.args[1])
    user = await col_users.find_one({'id': user_id})
    char = next((c for c in user.get('characters', []) if c['id'] == char_id), None)
    if not char: 
        await update.message.reply_text("❌ Not found."); return
    await col_users.update_one({'id': user_id}, {'$pull': {'characters': {'id': char_id}}})
    item = char.copy(); item['price'] = price; item['seller'] = user_id
    await col_market.insert_one(item)
    await update.message.reply_text(f"✅ Listed **{char['name']}** for {price}!")

async def buy(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not context.args: 
        await update.message.reply_text("⚠️ `/buy [ID]`")
        return
    char_id = context.args[0]
    item = await col_market.find_one({'id': char_id})
    if not item: await update.message.reply_text("❌ Sold/Invalid."); return
    buyer = await col_users.find_one({'id': user_id})
    if buyer.get('monarchs', 0) < item['price']: await update.message.reply_text("❌ Poor."); return
    await col_users.update_one({'id': user_id}, {'$inc': {'monarchs': -item['price']}, '$push': {'characters': item}})
    await col_users.update_one({'id': item['seller']}, {'$inc': {'monarchs': item['price']}})
    await col_market.delete_one({'id': char_id})
    await update.message.reply_text(f"✅ Bought **{item['name']}**!")

async def top(update: Update, context: CallbackContext):
    cursor = col_users.find({})
    users = sorted([{'name': u.get('name', 'Unknown'), 'count': len(u['characters'])} async for u in cursor if 'characters' in u], key=lambda x: x['count'], reverse=True)[:10]
    msg = "🏆 **LEADERBOARD**\n\n" + "\n".join([f"{i+1}. {u['name']} ➾ {u['count']}" for i, u in enumerate(users)])
    await update.message.reply_text(msg, parse_mode='Markdown')

async def balance(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    # Force Owner Max Balance on every check
    if user_id == OWNER_ID:
        await col_users.update_one({'id': user_id}, {'$set': {'monarchs': MAX_SAFE_INT}})
        
    user = await col_users.find_one({'id': user_id})
    if not user:
        await col_users.insert_one({'id': user_id, 'name': update.effective_user.first_name, 'monarchs': 0, 'characters': []})
        user = {'monarchs': 0}
    bal = user.get('monarchs', 0)
    await update.message.reply_text(f"💰 **Balance:** {bal} Monarchs")

async def rclaim(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    if not user:
        await col_users.insert_one({'id': user_id, 'name': update.effective_user.first_name, 'monarchs': 0, 'characters': []})
    if user_id != OWNER_ID:
        last_rclaim = user.get('last_rclaim', 0)
        if time.time() - last_rclaim < 86400: await update.message.reply_text("❌ Claimed already."); return
    pipeline = [{'$sample': {'size': 1}}]
    chars = await col_chars.aggregate(pipeline).to_list(length=1)
    if not chars: return
    char = chars[0]
    await col_users.update_one({'id': user_id}, {'$push': {'characters': char}, '$set': {'last_rclaim': time.time()}})
    await update.message.reply_photo(photo=char['img_url'], caption=f"🎁 Free: {char['name']}")

async def fav(update: Update, context: CallbackContext):
    if not context.args: return
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    char = next((c for c in user.get('characters', []) if c['id'] == context.args[0]), None)
    if not char: return
    await col_users.update_one({'id': user_id}, {'$set': {'favorites': char}})
    await update.message.reply_text(f"❤️ Favorite set: {char['name']}")

async def check(update: Update, context: CallbackContext):
    if not context.args: return
    char = await col_chars.find_one({'id': context.args[0]})
    if not char: return
    caption = f"🌟 **Info**\n🆔 {char['id']}\n📛 {char['name']}\n💎 {char['rarity']}"
    btn = [[InlineKeyboardButton("Who Have It", callback_data=f"who_{char['id']}")]]
    if char.get('type') == 'amv': 
        await update.message.reply_video(video=char['img_url'], caption=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(btn), supports_streaming=True, width=1280, height=720)
    else: await update.message.reply_photo(photo=char['img_url'], caption=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(btn))

async def who_have_it(update: Update, context: CallbackContext):
    char_id = update.callback_query.data.split("_")[1]
    users = await col_users.find({"characters.id": char_id}).to_list(length=10)
    msg = f"<b>Owners:</b>\n" + "\n".join([f"{i+1}. {u.get('name','User')}" for i,u in enumerate(users)])
    await update.callback_query.message.reply_text(msg, parse_mode='HTML')

# --- HAREM & SHOP (PAGINATION FIXED) ---
async def harem(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if update.message.reply_to_message: user_id = update.message.reply_to_message.from_user.id
    user = await col_users.find_one({'id': user_id})
    if not user or not user.get('characters'):
        try: await update.message.reply_text("❌ Empty.")
        except: pass
        return
    await send_harem_page(update, context, user_id, user.get('name', 'User'), 0, "img")

async def send_harem_page(update, context, user_id, user_name, page, mode):
    user = await col_users.find_one({'id': user_id})
    all_chars = user['characters']
    filtered = [c for c in all_chars if c.get('type', 'img') == mode]
    
    if not filtered and mode == 'amv':
        if update.callback_query: await update.callback_query.answer("No AMVs found!", show_alert=True)
        return

    filtered.sort(key=lambda x: x['anime'])
    CHUNK = 15
    total_pages = math.ceil(len(filtered) / CHUNK)
    if page < 0: page = 0
    if page >= total_pages: page = total_pages - 1
    
    current_batch = filtered[page * CHUNK : (page + 1) * CHUNK]
    msg = f"<b>🍃 {user_name}'s Harem</b>\nPage {page+1}/{total_pages}\n\n"
    for char in current_batch:
        msg += f"♦️ [ {char['rarity']} ] <code>{char['id']}</code> {char['name']} (Lv.{char.get('level', 1)})\n"

    nav = [[InlineKeyboardButton("⬅️", callback_data=f"h_prev_{user_id}_{page}_{mode}"), InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="dummy"), InlineKeyboardButton("➡️", callback_data=f"h_next_{user_id}_{page}_{mode}")]]
    switch = [[InlineKeyboardButton("Collection", callback_data=f"h_switch_{user_id}_0_img"), InlineKeyboardButton("❤️ AMV", callback_data=f"h_switch_{user_id}_0_amv")]]
    trash = [[InlineKeyboardButton("🗑️", callback_data="trash_help")]]
    
    markup = InlineKeyboardMarkup(nav + switch + trash)
    media_url = PHOTO_URL
    amv = False
    if user.get('favorites'):
        media_url = user['favorites']['img_url']
        if user['favorites'].get('type') == 'amv': amv = True
    elif filtered:
        media_url = filtered[-1]['img_url']
        if filtered[-1].get('type') == 'amv': amv = True

    if update.callback_query: 
        try: await update.callback_query.edit_message_caption(caption=msg, parse_mode='HTML', reply_markup=markup)
        except: pass
    else:
        if amv:
             await update.message.reply_video(video=media_url, caption=msg, parse_mode='HTML', reply_markup=markup, supports_streaming=True, width=1280, height=720)
        else:
             await update.message.reply_photo(photo=media_url, caption=msg, parse_mode='HTML', reply_markup=markup)

async def harem_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split('_')
    if query.data == "trash_help":
        await query.answer("To delete: /burn [ID]", show_alert=True)
        return
    if data[0] == "h":
        action, user_id, page, mode = data[1], int(data[2]), int(data[3]), data[4]
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

# --- OTHER FUNCTIONS ---

async def profile(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if update.message.reply_to_message: user_id = update.message.reply_to_message.from_user.id
    user = await col_users.find_one({'id': user_id})
    if not user: 
        await col_users.insert_one({'id': user_id, 'name': update.effective_user.first_name, 'monarchs': 0, 'characters': []})
        user = {'name': update.effective_user.first_name, 'monarchs': 0, 'characters': []}
    name = user.get('name', 'User')
    bal = user.get('monarchs', 0)
    count = len(user.get('characters', []))
    married = user.get('married_to', {}).get('name', 'None')
    clan = user.get('clan', 'None')
    pic = PHOTO_URL
    is_amv = False
    if user.get('favorites'):
        pic = user['favorites']['img_url']
        if user['favorites'].get('type') == 'amv': is_amv = True
    elif user.get('married_to'):
        pic = user['married_to']['img_url']
        if user['married_to'].get('type') == 'amv': is_amv = True
    msg = f"👤 <b>PROFILE</b>\n👑 Name: {name}\n💰 Monarchs: {bal}\n📚 Chars: {count}\n💍 Spouse: {married}\n🏰 Clan: {clan}"
    if is_amv:
        await update.message.reply_video(video=pic, caption=msg, parse_mode='HTML', supports_streaming=True, width=1280, height=720)
    else:
        await update.message.reply_photo(photo=pic, caption=msg, parse_mode='HTML')

async def marry(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not context.args: await update.message.reply_text("⚠️ `/marry [ID]`"); return
    char_id = context.args[0]
    user = await col_users.find_one({'id': user_id})
    if user.get('married_to'): await update.message.reply_text("❌ Already married!"); return
    char = next((c for c in user.get('characters', []) if c['id'] == char_id), None)
    if not char: await update.message.reply_text("❌ Not owned."); return
    if user.get('monarchs', 0) < 5000: await update.message.reply_text("❌ Need 5000 Monarchs."); return
    await col_users.update_one({'id': user_id}, {'$set': {'married_to': char}, '$inc': {'monarchs': -5000}})
    await update.message.reply_text(f"💍 Married **{char['name']}**!")

async def divorce(update: Update, context: CallbackContext):
    await col_users.update_one({'id': update.effective_user.id}, {'$unset': {'married_to': ""}})
    await update.message.reply_text("💔 Divorced.")

async def burn(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not context.args: return
    char_id = context.args[0]
    await col_users.update_one({'id': user_id}, {'$pull': {'characters': {'id': char_id}}, '$inc': {'monarchs': 200}})
    await update.message.reply_text("🔥 Burned for 200 Monarchs.")

async def adventure(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    if not user: return
    if user_id != OWNER_ID:
        last_adv = user.get('last_adv', 0)
        if time.time() - last_adv < 3600:
            rem = int(3600 - (time.time() - last_adv)) // 60
            await update.message.reply_text(f"⏳ Rest for {rem} mins!"); return
    await col_users.update_one({'id': user_id}, {'$set': {'last_adv': time.time()}})
    events = [("Found a chest!", 500), ("Killed a slime!", 200), ("Lost map...", 0), ("Tripped!", -50)]
    evt, coins = random.choice(events)
    await col_users.update_one({'id': user_id}, {'$inc': {'monarchs': coins}})
    await update.message.reply_text(f"⚔️ **Adventure:** {evt} ({coins} Monarchs)")

async def auction(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if len(context.args) < 2: await update.message.reply_text("⚠️ `/auction [ID] [Price]`"); return
    char_id, price = context.args[0], int(context.args[1])
    user = await col_users.find_one({'id': user_id})
    char = next((c for c in user.get('characters', []) if c['id'] == char_id), None)
    if not char: await update.message.reply_text("❌ Not found."); return
    await col_users.update_one({'id': user_id}, {'$pull': {'characters': {'id': char_id}}})
    auc_data = {'char': char, 'seller_id': user_id, 'current_bid': price, 'top_bidder': None, 'end_time': time.time() + 3600}
    await col_auctions.insert_one(auc_data)
    await update.message.reply_text(f"🔨 Auction: **{char['name']}** at {price}!")

async def bid(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if len(context.args) < 2: return
    char_id, amount = context.args[0], int(context.args[1])
    auc = await col_auctions.find_one({'char.id': char_id})
    if not auc or amount <= auc['current_bid']: return
    user = await col_users.find_one({'id': user_id})
    if user.get('monarchs', 0) < amount: return
    if auc['top_bidder']: await col_users.update_one({'id': auc['top_bidder']}, {'$inc': {'monarchs': auc['current_bid']}})
    await col_users.update_one({'id': user_id}, {'$inc': {'monarchs': -amount}})
    await col_auctions.update_one({'_id': auc['_id']}, {'$set': {'current_bid': amount, 'top_bidder': user_id}})
    await update.message.reply_text(f"✅ Bid {amount}!")

async def createclan(update: Update, context: CallbackContext):
    if not context.args: await update.message.reply_text("⚠️ `/createclan [Name]`"); return
    name = " ".join(context.args)
    if await col_clans.find_one({'name': name}): await update.message.reply_text("❌ Taken."); return
    user = await col_users.find_one({'id': update.effective_user.id})
    if user.get('monarchs', 0) < 10000: await update.message.reply_text("❌ Need 10k Monarchs."); return
    await col_users.update_one({'id': update.effective_user.id}, {'$inc': {'monarchs': -10000}, '$set': {'clan': name}})
    await col_clans.insert_one({'name': name, 'owner': update.effective_user.id, 'members': [update.effective_user.id]})
    await update.message.reply_text(f"🏰 Clan **{name}** created!")

async def joinclan(update: Update, context: CallbackContext):
    if not context.args: await update.message.reply_text("⚠️ `/joinclan [Name]`"); return
    name = " ".join(context.args)
    clan = await col_clans.find_one({'name': name})
    if not clan: await update.message.reply_text("❌ Not found."); return
    await col_clans.update_one({'_id': clan['_id']}, {'$addToSet': {'members': update.effective_user.id}})
    await col_users.update_one({'id': update.effective_user.id}, {'$set': {'clan': name}})
    await update.message.reply_text(f"✅ Joined **{name}**!")

async def feed(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not context.args: await update.message.reply_text("⚠️ `/feed [ID]`"); return
    char_id = context.args[0]
    user = await col_users.find_one({'id': user_id})
    if user.get('monarchs', 0) < 1000: await update.message.reply_text("❌ Need 1000 Monarchs."); return
    char = next((c for c in user.get('characters', []) if c['id'] == char_id), None)
    if not char: return
    new_lvl = char.get('level', 1) + 1
    await col_users.update_one({'id': user_id, 'characters.id': char_id}, {'$set': {'characters.$.level': new_lvl}, '$inc': {'monarchs': -1000}})
    await update.message.reply_text(f"🍖 Level Up! Lv.{new_lvl}")

async def coinflip(update: Update, context: CallbackContext):
    if len(context.args) < 2: 
        await update.message.reply_text("⚠️ `/coinflip [h/t] [amt]`")
        return
    choice, amount = context.args[0].lower(), int(context.args[1])
    user = await col_users.find_one({'id': update.effective_user.id})
    if user.get('monarchs', 0) < amount: await update.message.reply_text("❌ Poor."); return
    res = random.choice(['h', 't'])
    if choice[0] == res[0]:
        await col_users.update_one({'id': user['id']}, {'$inc': {'monarchs': amount}})
        await update.message.reply_text(f"🪙 Won! {res.upper()}")
    else:
        await col_users.update_one({'id': user['id']}, {'$inc': {'monarchs': -amount}})
        await update.message.reply_text(f"🪙 Lost! {res.upper()}")

async def dice(update: Update, context: CallbackContext):
    if not context.args: await update.message.reply_text("⚠️ `/dice [amt]`"); return
    try: amount = int(context.args[0])
    except: return
    user = await col_users.find_one({'id': update.effective_user.id})
    if user.get('monarchs', 0) < amount: await update.message.reply_text("❌ Poor."); return
    roll = random.randint(1, 6)
    if roll == 6:
        await col_users.update_one({'id': user['id']}, {'$inc': {'monarchs': amount*4}})
        await update.message.reply_text(f"🎲 6! 4x Win!")
    elif roll >= 4:
        await col_users.update_one({'id': user['id']}, {'$inc': {'monarchs': amount}})
        await update.message.reply_text(f"🎲 {roll}! 2x Win!")
    else:
        await col_users.update_one({'id': user['id']}, {'$inc': {'monarchs': -amount}})
        await update.message.reply_text(f"🎲 {roll}! Lost.")

async def guess(update: Update, context: CallbackContext):
    try:
        chat_id = update.effective_chat.id
        if chat_id not in last_spawn: return 
        if not context.args: return
        guess_w = " ".join(context.args).lower()
        real_n = last_spawn[chat_id]['char']['name'].lower()
        
        if guess_w == real_n or any(p == guess_w for p in real_n.split()):
            user_id = update.effective_user.id
            user = await col_users.find_one({'id': user_id})
            if not user:
                await col_users.insert_one({'id': user_id, 'name': update.effective_user.first_name, 'monarchs': 0, 'characters': []})
            
            char = last_spawn[chat_id]['char']
            t = round(time.time() - last_spawn[chat_id]['time'], 2)
            bal = 10000000 if update.effective_user.id == OWNER_ID else 40
            
            await col_users.update_one({'id': update.effective_user.id}, {'$push': {'characters': char}, '$inc': {'monarchs': bal}, '$set': {'name': update.effective_user.first_name}}, upsert=True)
            updated_user = await col_users.find_one({'id': update.effective_user.id})
            
            msg1 = (
                f"😈  <b>D E V I L ’ S   G U E S S   R E C O R D</b>  😈\n\n"
                f"🔥 Congratulations, mortal…\n"
                f"You have claimed <b>{bal}</b> cursed coins for your successful summon.\n"
                f"Your new soul-balance now falls to <b>{updated_user.get('monarchs', 0)}</b> coins… heh."
            )
            await update.message.reply_text(msg1, parse_mode='HTML')

            user_link = f"<a href='tg://user?id={user_id}'>{update.effective_user.first_name}</a>"
            caption = (
                f"⚡ {user_link}\n"
                f"You have captured a new entity from the shadows. 👁️‍🗨️\n\n"
                f"💀  <b>NAME:</b> {char['name']}\n\n"
                f"🌘 <b>ANIME:</b> {char['anime']}\n\n"
                f"🔥 <b>RARITY:</b> ● {char['rarity']}\n\n"
                f"⏳ <b>TIME TAKEN:</b> {t} seconds…\n\n"
                f"─────────────⛧─────────────"
            )
            
            btn = [[InlineKeyboardButton("👑 𝗦𝗲𝗲 𝗛𝗮𝗿𝗲𝗺", switch_inline_query_current_chat=f"collection.{user_id}")]]
            await update.message.reply_text(caption, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(btn))
            del last_spawn[chat_id]
        else: await update.message.reply_text("❌ Wrong guess!")
    except Exception as e: logger.error(f"Guess Error: {e}")

# --- SERVER ---
async def web_server():
    async def handle(request): return web.Response(text="Live")
    app = web.Application(); app.router.add_get('/', handle); runner = web.AppRunner(app); await runner.setup(); site = web.TCPSite(runner, '0.0.0.0', PORT); await site.start()
    
async def main():
    await web_server()
    app = Application.builder().token(TOKEN).build()
    app.add_error_handler(error_handler)
    
    asyncio.create_task(check_auctions(app))

    handlers = [
        CommandHandler("start", start), CommandHandler("rupload", rupload), CommandHandler("addshop", addshop),
        CommandHandler("delete", delete), CommandHandler("changetime", changetime), CommandHandler("bcast", bcast),
        CommandHandler("addadmin", add_admin), CommandHandler("rmadmin", rm_admin), CommandHandler("rupdate", rupdate),
        CommandHandler("stats", stats),
        CommandHandler("balance", balance), CommandHandler("daily", daily), CommandHandler("gift", gift),
        CommandHandler("trade", trade), CommandHandler("top", top), 
        CommandHandler("shop", shop), 
        CommandHandler("rclaim", rclaim), CommandHandler("check", check), CommandHandler("fav", fav),
        CommandHandler("harem", harem), CommandHandler("profile", profile), CommandHandler("marry", marry),
        CommandHandler("burn", burn), CommandHandler("divorce", divorce), CommandHandler("auction", auction),
        CommandHandler("bid", bid), CommandHandler("createclan", createclan), CommandHandler("joinclan", joinclan),
        CommandHandler("feed", feed), CommandHandler("coinflip", coinflip), CommandHandler("dice", dice),
        CommandHandler("guess", guess), CommandHandler("ball", ball), 
        CommandHandler("slots", slots), CommandHandler("fight", fight), CommandHandler("pay", pay), # Added /pay
        CallbackQueryHandler(harem_callback, pattern="^h_"), CallbackQueryHandler(harem_callback, pattern="^trash_"),
        CallbackQueryHandler(shop_callback, pattern="^shop_"),
        CallbackQueryHandler(shop_callback, pattern="^buy_char_"),
        CallbackQueryHandler(help_menu, pattern="help_menu"), CallbackQueryHandler(who_have_it, pattern="^who_"),
        InlineQueryHandler(inline_query), MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
    ]
    for h in handlers: app.add_handler(h)
    await app.initialize(); await app.start(); await app.updater.start_polling(); await asyncio.Event().wait()

if __name__ == "__main__": asyncio.run(main())
