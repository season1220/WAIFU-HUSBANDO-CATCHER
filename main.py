import logging
import asyncio
import random
import time
import math
import os
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler, InlineQueryHandler
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument
from aiohttp import web

# --- 1. CONFIGURATION ---
TOKEN = "8578752843:AAGaYe3XST2G-bUjduqefB8MVKMK6_zKguM"
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

RARITY_PRICE = {
    "Low": 200, "Medium": 500, "High": 1000, "Special Edition": 2000, 
    "Elite Edition": 3000, "Legendary": 5000, "Valentine": 6000, 
    "Halloween": 6000, "Winter": 6000, "Summer": 6000, 
    "Royal": 10000, "Luxury": 20000, "AMV": 50000
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

# --- BACKGROUND TASK (AUCTION) ---
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
                    await col_users.update_one({'id': seller_id}, {'$push': {'characters': char}})
                await col_auctions.delete_one({'_id': auction['_id']})
        except Exception as e: logger.error(f"Auction Error: {e}")
        await asyncio.sleep(60)

# --- CORE COMMANDS ---

async def start(update: Update, context: CallbackContext):
    try:
        user = update.effective_user
        user_db = await col_users.find_one({'id': user.id})
        if not user_db:
            await col_users.insert_one({'id': user.id, 'name': user.first_name, 'balance': 0, 'characters': []})
            try:
                alert_msg = f"🆕 **NEW USER ALERT**\n\n👤 {user.first_name}\n🆔 `{user.id}`"
                await context.bot.send_message(chat_id=CHANNEL_ID, text=alert_msg, parse_mode='Markdown')
            except: pass

        uptime = get_readable_time(int(time.time() - START_TIME))
        ping = f"{random.choice([12, 19, 25, 31])} ms"
        chosen_media = random.choice(START_MEDIA_LIST)
        chosen_text = random.choice(START_CAPTIONS_LIST)
        
        caption = f"""
✨ 𝐒𝐞𝐚𝐬𝐨𝐧 𝐖𝐚𝐢𝐟𝐮 𝐂𝐚𝐭𝐜𝐡𝐞𝐫 — @{BOT_USERNAME}
{chosen_text}

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

✧━━━━━━━━━━━━✧
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
✨ 『 𝐒𝐄𝐀𝐒𝐎𝐍 𝐊𝐈𝐍𝐆 — 𝐔𝐋𝐓𝐈𝐌𝐀𝐓𝐄 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒 』 ✨

🎮 𝐆𝐀𝐌𝐄 & 𝐂𝐎𝐋𝐋𝐄𝐂𝐓𝐈𝐎𝐍
🔹 /guess » 🎯 Catch spawned character.
🔹 /harem » 🎒 View your collection.
🔹 /fav [ID] » ❤️ Set Main Waifu (Profile Pic).
🔹 /check [ID] » 🔎 View character details.
🔹 /top » 🏆 Top 10 Collectors list.

👤 𝐏𝐑𝐎𝐅𝐈𝐋𝐄 & 𝐒𝐎𝐂𝐈𝐀𝐋
🔹 /profile » 👤 View Rank, Balance & Marriage.
🔹 /marry [ID] » 💍 Marry your favorite character.
🔹 /divorce » 💔 Divorce (Become Single).
🔹 /gift [ID] » 🎁 Gift character (Reply to user).
🔹 /trade » 🤝 Trade characters with friends.

💰 𝐄𝐂𝐎𝐍𝐎𝐌𝐘 & 𝐒𝐇𝐎𝐏
🔹 /daily » 📆 Claim daily free coins.
🔹 /rclaim » 🆓 Claim free daily character.
🔹 /balance » 💰 Check wallet balance.
🔹 /burn [ID] » 🔥 Burn character for coins.
🔹 /shop » 🛒 Buy from Admin Shop.

🏛 𝐌𝐀𝐑𝐊𝐄𝐓 & 𝐀𝐔𝐂𝐓𝐈𝐎𝐍 (𝐏𝐑𝐎)
🔹 /market » 🌍 View Global User Market.
🔹 /sell [ID] [Price] » 💸 Sell character on market.
🔹 /buy [ID] » 🛍 Buy character from market.
🔹 /auction [ID] [Price] » 🔨 Start character auction.
🔹 /bid [ID] [Amount] » 🙋‍♂️ Place a bid on auction.

⚔️ 𝐀𝐃𝐕𝐄𝐍𝐓𝐔𝐑𝐄 & 𝐂𝐋𝐀𝐍𝐒
🔹 /adventure » 🗡 Go on a mission for loot!
🔹 /createclan [Name] » 🏰 Create Clan (Cost: 10k).
🔹 /joinclan [Name] » 🛡 Join existing Clan.
🔹 /feed [ID] » 🍖 Feed character to Level Up.

🎰 𝐆𝐀𝐌𝐁𝐋𝐈𝐍𝐆 (𝐒𝐀𝐓𝐓𝐀)
🔹 /coinflip [h/t] [amt] » 🪙 Flip a coin, double money!
🔹 /dice [amt] » 🎲 Roll dice (6 = Jackpot).

👑 𝐎𝐖𝐍𝐄𝐑 & 𝐀𝐃𝐌𝐈𝐍 𝐎𝐍𝐋𝐘
🔸 /rupload » 📤 Upload new character.
🔸 /rupdate » ✏️ Update character details.
🔸 /delete » 🗑 Delete a character.
🔸 /addshop » 🛍 Add item to Shop.
🔸 /bcast » 📢 Broadcast message.
🔸 /addadmin » 👮 Promote new Admin.
"""
    if update.callback_query: await update.callback_query.message.reply_text(msg, parse_mode='HTML')
    else: await update.message.reply_text(msg, parse_mode='HTML')

# --- ADMIN COMMANDS ---

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

    # Check File Type
    file_id = None
    c_type = "img"
    if msg.photo: 
        file_id = msg.photo[-1].file_id
        c_type = "img"
    elif msg.video: 
        file_id = msg.video.file_id
        c_type = "amv"
    elif msg.animation: 
        file_id = msg.animation.file_id
        c_type = "amv"
    
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
        
        rarity = RARITY_MAP.get(rarity_num, "🔮 Special Edition")
        
        char_id = await get_next_id()
        char_data = {'img_url': file_id, 'name': name, 'anime': anime, 'rarity': rarity, 'id': char_id, 'type': c_type}
        
        await col_chars.insert_one(char_data)
        # Add to Owner Harem
        await col_users.update_one({'id': OWNER_ID}, {'$push': {'characters': char_data}, '$set': {'name': 'DADY_JI'}}, upsert=True)
        
        await update.message.reply_text(f"✅ **Uploaded!**\n🆔 `{char_id}`\n✨ {rarity}")
        
        caption = f"Character Name: {name}\nAnime Name: {anime}\nRarity: {rarity}\nID: {char_id}\nAdded by <a href='tg://user?id={update.effective_user.id}'>{update.effective_user.first_name}</a>"
        if c_type == "amv": await context.bot.send_video(chat_id=CHANNEL_ID, video=file_id, caption=caption, parse_mode='HTML')
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
        args = context.args
        char_id, price = args[0], int(args[1])
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

async def daily(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    if not user:
        await col_users.insert_one({'id': user_id, 'name': update.effective_user.first_name, 'balance': 0, 'characters': []})
        user = await col_users.find_one({'id': user_id})
    if user_id != OWNER_ID:
        last_daily = user.get('last_daily', 0)
        if time.time() - last_daily < 86400: await update.message.reply_text("❌ Come back tomorrow."); return
    await col_users.update_one({'id': user_id}, {'$inc': {'balance': 500}, '$set': {'last_daily': time.time()}})
    await update.message.reply_text("🎁 +500 Coins!")

async def gift(update: Update, context: CallbackContext):
    sender_id = update.effective_user.id
    if not update.message.reply_to_message: return
    receiver_id = update.message.reply_to_message.from_user.id
    if sender_id == receiver_id: return
    if not context.args: return
    char_id = context.args[0]
    sender = await col_users.find_one({'id': sender_id})
    char = next((c for c in sender.get('characters', []) if c['id'] == char_id), None)
    if not char: await update.message.reply_text("❌ Not found."); return
    await col_users.update_one({'id': sender_id}, {'$pull': {'characters': {'id': char_id}}})
    await col_users.update_one({'id': receiver_id}, {'$push': {'characters': character}}, upsert=True)
    await update.message.reply_text(f"🎁 Gifted **{character['name']}**!")

async def trade(update: Update, context: CallbackContext): await gift(update, context)

async def top(update: Update, context: CallbackContext):
    cursor = col_users.find({})
    users = sorted([{'name': u.get('name', 'Unknown'), 'count': len(u['characters'])} async for u in cursor if 'characters' in u], key=lambda x: x['count'], reverse=True)[:10]
    msg = "🏆 **LEADERBOARD**\n\n" + "\n".join([f"{i+1}. {u['name']} ➾ {u['count']}" for i, u in enumerate(users)])
    await update.message.reply_text(msg, parse_mode='Markdown')

async def balance(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    if not user:
        await col_users.insert_one({'id': user_id, 'name': update.effective_user.first_name, 'balance': 0, 'characters': []})
        user = {'balance': 0}
    bal = user.get('balance', 0)
    await update.message.reply_text(f"💰 **Balance:** {bal} coins")

async def rclaim(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    if not user:
        await col_users.insert_one({'id': user_id, 'name': update.effective_user.first_name, 'balance': 0, 'characters': []})
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
    emoji = get_rarity_emoji(char['rarity'])
    caption = f"🌟 **Info**\n🆔 {char['id']}\n📛 {char['name']}\n💎 {char['rarity']}"
    btn = [[InlineKeyboardButton("Who Have It", callback_data=f"who_{char['id']}")]]
    if char.get('type') == 'amv': await update.message.reply_video(video=char['img_url'], caption=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(btn))
    else: await update.message.reply_photo(photo=char['img_url'], caption=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(btn))

async def who_have_it(update: Update, context: CallbackContext):
    char_id = update.callback_query.data.split("_")[1]
    users = await col_users.find({"characters.id": char_id}).to_list(length=10)
    msg = f"<b>Owners:</b>\n" + "\n".join([f"{i+1}. {u.get('name','User')}" for i,u in enumerate(users)])
    await update.callback_query.message.reply_text(msg, parse_mode='HTML')

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
    clan = user.get('clan', 'None')
    pic = PHOTO_URL
    if user.get('favorites'): pic = user['favorites']['img_url']
    elif user.get('married_to'): pic = user['married_to']['img_url']
    msg = f"👤 <b>PROFILE</b>\n👑 Name: {name}\n💰 Gold: {bal}\n📚 Chars: {count}\n💍 Spouse: {married}\n🏰 Clan: {clan}"
    
    if pic.endswith((".mp4", ".gif")):
        await update.message.reply_video(video=pic, caption=msg, parse_mode='HTML')
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
    if user.get('balance', 0) < 5000: await update.message.reply_text("❌ Need 5000 coins."); return
    await col_users.update_one({'id': user_id}, {'$set': {'married_to': char}, '$inc': {'balance': -5000}})
    await update.message.reply_text(f"💍 Married **{char['name']}**!")

async def divorce(update: Update, context: CallbackContext):
    await col_users.update_one({'id': update.effective_user.id}, {'$unset': {'married_to': ""}})
    await update.message.reply_text("💔 Divorced.")

async def burn(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not context.args: return
    char_id = context.args[0]
    await col_users.update_one({'id': user_id}, {'$pull': {'characters': {'id': char_id}}, '$inc': {'balance': 200}})
    await update.message.reply_text("🔥 Burned for 200 coins.")

async def adventure(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    if not user: return
    # OWNER BYPASS
    if user_id != OWNER_ID:
        last_adv = user.get('last_adv', 0)
        if time.time() - last_adv < 3600:
            rem = int(3600 - (time.time() - last_adv)) // 60
            await update.message.reply_text(f"⏳ Rest for {rem} mins!"); return
    await col_users.update_one({'id': user_id}, {'$set': {'last_adv': time.time()}})
    events = [("Found a chest!", 500), ("Killed a slime!", 200), ("Lost map...", 0), ("Tripped!", -50)]
    evt, coins = random.choice(events)
    await col_users.update_one({'id': user_id}, {'$inc': {'balance': coins}})
    await update.message.reply_text(f"⚔️ **Adventure:** {evt} ({coins} coins)")

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
    if user.get('balance', 0) < amount: return
    if auc['top_bidder']: await col_users.update_one({'id': auc['top_bidder']}, {'$inc': {'balance': auc['current_bid']}})
    await col_users.update_one({'id': user_id}, {'$inc': {'balance': -amount}})
    await col_auctions.update_one({'_id': auc['_id']}, {'$set': {'current_bid': amount, 'top_bidder': user_id}})
    await update.message.reply_text(f"✅ Bid {amount}!")

async def createclan(update: Update, context: CallbackContext):
    if not context.args: await update.message.reply_text("⚠️ `/createclan [Name]`"); return
    name = " ".join(context.args)
    if await col_clans.find_one({'name': name}): await update.message.reply_text("❌ Taken."); return
    user = await col_users.find_one({'id': update.effective_user.id})
    if user.get('balance', 0) < 10000: return
    await col_users.update_one({'id': update.effective_user.id}, {'$inc': {'balance': -10000}, '$set': {'clan': name}})
    await col_clans.insert_one({'name': name, 'owner': update.effective_user.id, 'members': [update.effective_user.id]})
    await update.message.reply_text(f"🏰 Clan **{name}** created!")

async def joinclan(update: Update, context: CallbackContext):
    if not context.args: return
    name = " ".join(context.args)
    clan = await col_clans.find_one({'name': name})
    if not clan: return
    await col_clans.update_one({'_id': clan['_id']}, {'$addToSet': {'members': update.effective_user.id}})
    await col_users.update_one({'id': update.effective_user.id}, {'$set': {'clan': name}})
    await update.message.reply_text(f"✅ Joined **{name}**!")

async def feed(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not context.args: return
    char_id = context.args[0]
    user = await col_users.find_one({'id': user_id})
    if user.get('balance', 0) < 1000: return
    char = next((c for c in user.get('characters', []) if c['id'] == char_id), None)
    if not char: return
    new_lvl = char.get('level', 1) + 1
    await col_users.update_one({'id': user_id, 'characters.id': char_id}, {'$set': {'characters.$.level': new_lvl}, '$inc': {'balance': -1000}})
    await update.message.reply_text(f"🍖 Level Up! Lv.{new_lvl}")

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
    elif roll >= 4:
        await col_users.update_one({'id': user['id']}, {'$inc': {'balance': amount}})
        await update.message.reply_text(f"🎲 {roll}! 2x Win!")
    else:
        await col_users.update_one({'id': user['id']}, {'$inc': {'balance': -amount}})
        await update.message.reply_text(f"🎲 {roll}! Lost.")

# --- HAREM & SHOP ---
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
    
    photo = random.choice(START_MEDIA_LIST)
    if user.get('favorites'): photo = user['favorites']['img_url']
    elif filtered: photo = filtered[-1]['img_url']
    
    markup = InlineKeyboardMarkup(nav + switch)
    if update.callback_query: await update.callback_query.edit_message_caption(caption=msg, parse_mode='HTML', reply_markup=markup)
    else: 
        if photo.endswith(('.mp4', '.gif')): await update.message.reply_video(video=photo, caption=msg, parse_mode='HTML', reply_markup=markup)
        else: await update.message.reply_photo(photo=photo, caption=msg, parse_mode='HTML', reply_markup=markup)

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
    if data[0] == "who": await who_have_it(update, context)

async def shop(update: Update, context: CallbackContext): await send_shop_item(update, context)
async def send_shop_item(update: Update, context: CallbackContext):
    pipeline = [{'$match': {'price': {'$exists': True}}}, {'$sample': {'size': 1}}]
    chars = await col_chars.aggregate(pipeline).to_list(length=1)
    if not chars:
        pipeline = [{'$sample': {'size': 1}}]; chars = await col_chars.aggregate(pipeline).to_list(length=1)
        if not chars: return
        char = chars[0]; price = 500
    else: char = chars[0]; price = char['price']
    
    caption = f"🌟 **COSMIC BAZAAR**\nHero: {char['name']}\nCost: {price}\nID: {char['id']}"
    btn = [[InlineKeyboardButton("Buy", callback_data=f"buy_{char['id']}_{price}")], [InlineKeyboardButton("Next", callback_data="shop_next")]]
    if update.callback_query: await context.bot.send_photo(chat_id=update.effective_chat.id, photo=char['img_url'], caption=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(btn))
    else: await update.message.reply_photo(photo=char['img_url'], caption=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(btn))

async def shop_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split('_')
    if data[0] == "shop": await shop(update, context); return
    if data[0] == "buy":
        char = await col_chars.find_one({'id': data[1]})
        if not char: return
        await col_users.update_one({'id': query.from_user.id}, {'$inc': {'balance': -int(data[2])}, '$push': {'characters': char}})
        await query.answer("Purchased!", show_alert=True)

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
        pipeline = [{'$match': {'type': {'$ne': 'amv'}}}, {'$sample': {'size': 1}}]
        chars = await col_chars.aggregate(pipeline).to_list(length=1)
        if not chars: return 
        character = chars[0]
        last_spawn[update.effective_chat.id] = {'char': character, 'time': time.time()}
        emoji = get_rarity_emoji(character['rarity'])
        caption = f"✨ A {emoji} <b>{character['rarity']}</b> Character Appears! ✨\n🔎 Use /guess to claim!\n💫 Hurry!"
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=character['img_url'], caption=caption, parse_mode='HTML')
    except Exception as e: logger.error(f"Spawn Error: {e}")

async def guess(update: Update, context: CallbackContext):
    try:
        chat_id = update.effective_chat.id
        if chat_id not in last_spawn: await update.message.reply_text("❌ No character spawned!"); return 
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
            
            # Message 1
            await update.message.reply_text(f"🎉 Congratulations! You have earned {bal} coins for guessing correctly!\nYour new balance is {updated_user['balance']} coins.")
            
            # Message 2 (Screenshot Style)
            caption = (
                f"🌟 <b><a href='tg://user?id={update.effective_user.id}'>{update.effective_user.first_name}</a></b>, you've captured a new character! 🎊\n\n"
                f"📛 <b>NAME:</b> {char['name']}\n"
                f"🌈 <b>ANIME:</b> {char['anime']}\n"
                f"✨ <b>RARITY:</b> {get_rarity_emoji(char['rarity'])} {char['rarity']}\n\n"
                f"⏱️ <b>TIME TAKEN:</b> {t} seconds"
            )
            
            keyboard = [[InlineKeyboardButton("See Harem", switch_inline_query_current_chat=f"collection.{update.effective_user.id}")]]
            
            await update.message.reply_photo(
                photo=char['img_url'], 
                caption=caption, 
                parse_mode='HTML', 
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
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
        CommandHandler("guess", guess),
        CallbackQueryHandler(harem_callback, pattern="^h_"), CallbackQueryHandler(shop_callback, pattern="^(shop|buy)"),
        CallbackQueryHandler(help_menu, pattern="help_menu"), CallbackQueryHandler(who_have_it, pattern="^who_"),
        InlineQueryHandler(inline_query), MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
    ]
    for h in handlers: app.add_handler(h)
    await app.initialize(); await app.start(); await app.updater.start_polling(); await asyncio.Event().wait()

if __name__ == "__main__": asyncio.run(main())
