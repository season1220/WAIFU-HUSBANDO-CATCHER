import logging
import asyncio
import random
import time
import math
import os
from uuid import uuid4
from collections import defaultdict
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler, InlineQueryHandler
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

# --- HELPER FUNCTIONS (UPDATED RARITY MAP) ---
RARITY_MAP = {
    1: "🔸 Low", 
    2: "🔷 Medium", 
    3: "♦️ High", 
    4: "🔮 Special Edition", 
    5: "💮 Elite Edition", 
    6: "💫 Legendary", 
    7: "💝 Valentine", 
    8: "🎃 Halloween", 
    9: "❄️ Winter", 
    10: "🏜 Summer", 
    11: "🎗 Royal", 
    12: "💸 Luxury"
}

RARITY_PRICE = {
    "Low": 200, "Medium": 500, "High": 1000, 
    "Special Edition": 2000, "Elite Edition": 3000, 
    "Legendary": 5000, "Valentine": 6000, "Halloween": 6000, 
    "Winter": 6000, "Summer": 6000, "Royal": 10000, "Luxury": 20000
}

def get_rarity_emoji(rarity):
    if not rarity: return "✨"
    r = rarity.lower()
    if "luxury" in r: return "💸"
    if "royal" in r: return "🎗"
    if "summer" in r: return "🏜"
    if "winter" in r: return "❄️"
    if "halloween" in r: return "🎃"
    if "valentine" in r: return "💝"
    if "legendary" in r: return "💫"
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

# --- BACKGROUND TASK (Dummy for keeping alive) ---
async def background_task(app):
    while True:
        await asyncio.sleep(3600)

# --- CORE COMMANDS ---

async def start(update: Update, context: CallbackContext):
    try:
        user = update.effective_user
        user_db = await col_users.find_one({'id': user.id})
        if not user_db:
            await col_users.insert_one({'id': user.id, 'name': user.first_name, 'balance': 0, 'characters': []})
            try: await context.bot.send_message(chat_id=CHANNEL_ID, text=f"🆕 **NEW USER ALERT**\n\n👤 {user.first_name}\n🆔 `{user.id}`", parse_mode='Markdown')
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
<b>⚙️ GOD MODE COMMANDS</b>
/guess - Catch character
/harem - Collection
/profile - Your Stats
/auction - List for auction
/bid - Bid on auction
/createclan - Create Clan (10k coins)
/joinclan - Join Clan
/feed - Level up character
/coinflip - Double or Nothing
/dice - Roll dice
/shop - Buy characters
/trade - Trade
/gift - Gift
/daily - Free coins
"""
    if update.callback_query: await update.callback_query.message.reply_text(msg, parse_mode='HTML')
    else: await update.message.reply_text(msg, parse_mode='HTML')

# --- FEATURES ---

async def auction(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if len(context.args) < 2: await update.message.reply_text("⚠️ `/auction [Char ID] [Start Price]`"); return
    char_id, price = context.args[0], int(context.args[1])
    
    user = await col_users.find_one({'id': user_id})
    char = next((c for c in user.get('characters', []) if c['id'] == char_id), None)
    if not char: await update.message.reply_text("❌ Character not found."); return
    
    await col_users.update_one({'id': user_id}, {'$pull': {'characters': {'id': char_id}}})
    
    auction_data = {
        'char': char, 'seller_id': user_id, 'current_bid': price, 'top_bidder': None,
        'end_time': time.time() + 3600
    }
    await col_auctions.insert_one(auction_data)
    await update.message.reply_text(f"🔨 **Auction Started!**\n{char['name']} for {price} coins.\nUse `/bid {char['id']} [Amount]`")

async def bid(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if len(context.args) < 2: await update.message.reply_text("⚠️ `/bid [Char ID] [Amount]`"); return
    char_id_target, amount = context.args[0], int(context.args[1])
    
    auc = await col_auctions.find_one({'char.id': char_id_target}) 
    if not auc: await update.message.reply_text("❌ Auction not found."); return
    
    if amount <= auc['current_bid']: await update.message.reply_text("❌ Bid higher!"); return
    
    user = await col_users.find_one({'id': user_id})
    if user.get('balance', 0) < amount: await update.message.reply_text("❌ No money."); return
    
    if auc['top_bidder']:
        await col_users.update_one({'id': auc['top_bidder']}, {'$inc': {'balance': auc['current_bid']}})
    
    await col_users.update_one({'id': user_id}, {'$inc': {'balance': -amount}})
    await col_auctions.update_one({'_id': auc['_id']}, {'$set': {'current_bid': amount, 'top_bidder': user_id}})
    await update.message.reply_text(f"✅ **Bid Accepted!** Top bid: {amount}")

async def createclan(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not context.args: await update.message.reply_text("⚠️ `/createclan [Name]`"); return
    clan_name = " ".join(context.args)
    if await col_clans.find_one({'name': clan_name}): await update.message.reply_text("❌ Name taken."); return
    user = await col_users.find_one({'id': user_id})
    if user.get('balance', 0) < 10000: await update.message.reply_text("❌ Need 10k coins."); return
    await col_users.update_one({'id': user_id}, {'$inc': {'balance': -10000}})
    await col_clans.insert_one({'name': clan_name, 'owner': user_id, 'members': [user_id], 'bank': 0})
    await update.message.reply_text(f"🏰 **Clan Created:** {clan_name}")

async def joinclan(update: Update, context: CallbackContext):
    if not context.args: await update.message.reply_text("⚠️ `/joinclan [Name]`"); return
    clan_name = " ".join(context.args)
    clan = await col_clans.find_one({'name': clan_name})
    if not clan: await update.message.reply_text("❌ Clan not found."); return
    await col_clans.update_one({'_id': clan['_id']}, {'$addToSet': {'members': update.effective_user.id}})
    await update.message.reply_text(f"✅ Joined **{clan_name}**!")

async def feed(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not context.args: await update.message.reply_text("⚠️ `/feed [ID]` (Cost: 1000)"); return
    char_id = context.args[0]
    user = await col_users.find_one({'id': user_id})
    if user.get('balance', 0) < 1000: await update.message.reply_text("❌ Need 1000 coins."); return
    char = next((c for c in user['characters'] if c['id'] == char_id), None)
    if not char: await update.message.reply_text("❌ Not found."); return
    new_level = char.get('level', 1) + 1
    await col_users.update_one({'id': user_id, 'characters.id': char_id}, {'$set': {'characters.$.level': new_level}, '$inc': {'balance': -1000}})
    await update.message.reply_text(f"🍖 **Leveled Up!**\n{char['name']} is now Level {new_level}!")

async def coinflip(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if len(context.args) < 2: await update.message.reply_text("⚠️ `/coinflip [h/t] [amt]`"); return
    choice = context.args[0].lower()
    try: amount = int(context.args[1])
    except: return
    user = await col_users.find_one({'id': user_id})
    if user.get('balance', 0) < amount: await update.message.reply_text("❌ Poor."); return
    outcome = random.choice(['heads', 'tails'])
    if choice[0] == outcome[0]:
        win = amount
        await col_users.update_one({'id': user_id}, {'$inc': {'balance': win}})
        await update.message.reply_text(f"🪙 **YOU WON!** Result: {outcome.upper()}. +{win}")
    else:
        await col_users.update_one({'id': user_id}, {'$inc': {'balance': -amount}})
        await update.message.reply_text(f"🪙 **YOU LOST!** Result: {outcome.upper()}. -{amount}")

async def dice(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not context.args: return
    try: amount = int(context.args[0])
    except: return
    user = await col_users.find_one({'id': user_id})
    if user.get('balance', 0) < amount: await update.message.reply_text("❌ Poor."); return
    roll = random.randint(1, 6)
    if roll == 6:
        win = amount * 4
        await col_users.update_one({'id': user_id}, {'$inc': {'balance': win}})
        await update.message.reply_text(f"🎲 **SIX!** You won {win} coins!")
    elif roll >= 4:
        win = amount
        await col_users.update_one({'id': user_id}, {'$inc': {'balance': win}})
        await update.message.reply_text(f"🎲 **{roll}!** You doubled your bet!")
    else:
        await col_users.update_one({'id': user_id}, {'$inc': {'balance': -amount}})
        await update.message.reply_text(f"🎲 **{roll}!** You lost.")

# --- ADMIN & STANDARD COMMANDS ---
async def stats(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID: return
    count = await col_users.count_documents({})
    await update.message.reply_text(f"📊 Users: {count}")

async def rupload(update: Update, context: CallbackContext):
    if not await is_admin(update.effective_user.id): return
    msg = update.message.reply_to_message
    if not msg: await update.message.reply_text("⚠️ Reply!"); return
    file_id, c_type = (msg.photo[-1].file_id, "img") if msg.photo else (msg.video.file_id, "amv") if msg.video else (msg.animation.file_id, "amv") if msg.animation else (None, None)
    if not file_id: return
    try:
        args = context.args
        if len(args) < 3: await update.message.reply_text("⚠️ `/rupload Name Anime Num`"); return
        name = args[0].replace('-', ' ').title(); anime = args[1].replace('-', ' ').title()
        try: rarity = RARITY_MAP.get(int(args[2]), "🔮 Special Edition")
        except: rarity = "🔮 Special Edition"
        char_id = await get_next_id()
        char_data = {'img_url': file_id, 'name': name, 'anime': anime, 'rarity': rarity, 'id': char_id, 'type': c_type}
        await col_chars.insert_one(char_data)
        # OWNER FIX: Always add to Owner
        await col_users.update_one({'id': OWNER_ID}, {'$push': {'characters': char_data}, '$set': {'name': 'DADY_JI'}}, upsert=True)
        await update.message.reply_text(f"✅ Uploaded `{char_id}`")
        caption = f"Character Name: {name}\nAnime Name: {anime}\nRarity: {rarity}\nID: {char_id}\nAdded by <a href='tg://user?id={update.effective_user.id}'>{update.effective_user.first_name}</a>"
        if c_type == "amv": await context.bot.send_video(chat_id=CHANNEL_ID, video=file_id, caption=caption, parse_mode='HTML')
        else: await context.bot.send_photo(chat_id=CHANNEL_ID, photo=file_id, caption=caption, parse_mode='HTML')
    except: pass

async def rupdate(update: Update, context: CallbackContext):
    if not await is_admin(update.effective_user.id): return
    try:
        args = context.args
        char_id, field, new_val = args[0], args[1].lower(), " ".join(args[2:])
        if field == "rarity": new_val = RARITY_MAP.get(int(new_val), new_val)
        await col_chars.update_one({'id': char_id}, {'$set': {field: new_val}})
        await update.message.reply_text(f"✅ Updated {field}")
    except: pass

async def delete(update: Update, context: CallbackContext):
    if not await is_admin(update.effective_user.id): return
    if not context.args: return
    await col_chars.delete_one({'id': context.args[0]})
    await update.message.reply_text(f"✅ Deleted.")

async def bcast(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID: return
    if not update.message.reply_to_message: return
    users = await col_users.find({}).to_list(length=None)
    for u in users:
        try: await update.message.reply_to_message.copy(chat_id=u['id'])
        except: pass
    await update.message.reply_text("✅ Done.")

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

async def daily(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    if not user: await update.message.reply_text("Play first!"); return
    if user_id != OWNER_ID and time.time() - user.get('last_daily', 0) < 86400: await update.message.reply_text("❌ Tomorrow."); return
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
    users = await col_users.find().to_list(length=None)
    users = sorted(users, key=lambda x: len(x.get('characters', [])), reverse=True)[:10]
    msg = "🏆 **TOP**\n" + "\n".join([f"{i+1}. {u.get('name')} - {len(u.get('characters', []))}" for i,u in enumerate(users)])
    await update.message.reply_text(msg, parse_mode='Markdown')

async def balance(update: Update, context: CallbackContext):
    user = await col_users.find_one({'id': update.effective_user.id})
    await update.message.reply_text(f"💰 {user.get('balance', 0)}")

async def rclaim(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    if not user: return
    if user_id != OWNER_ID and time.time() - user.get('last_rclaim', 0) < 86400: await update.message.reply_text("❌ Tomorrow."); return
    pipeline = [{'$sample': {'size': 1}}]
    chars = await col_chars.aggregate(pipeline).to_list(length=1)
    if not chars: return
    await col_users.update_one({'id': user_id}, {'$push': {'characters': chars[0]}, '$set': {'last_rclaim': time.time()}})
    await update.message.reply_photo(photo=chars[0]['img_url'], caption=f"🎁 Free: {chars[0]['name']}")

async def profile(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if update.message.reply_to_message: user_id = update.message.reply_to_message.from_user.id
    user = await col_users.find_one({'id': user_id})
    if not user: await update.message.reply_text("Not started."); return
    name = user.get('name', update.effective_user.first_name)
    bal = user.get('balance', 0)
    count = len(user.get('characters', []))
    married_char = user.get('married_to')
    married_text = f"{married_char['name']} (💍)" if married_char else "None"
    pic = married_char['img_url'] if married_char else (user.get('favorites', {}).get('img_url') or PHOTO_URL)
    msg = f"👤 **USER PROFILE**\n👑 Name: {name}\n💰 Balance: {bal}\n📚 Chars: {count}\n💍 Spouse: {married_text}"
    await update.message.reply_photo(photo=pic, caption=msg, parse_mode='Markdown')

async def marry(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not context.args: return
    char_id = context.args[0]
    user = await col_users.find_one({'id': user_id})
    if user.get('married_to'): await update.message.reply_text("❌ Already married!"); return
    char = next((c for c in user.get('characters', []) if c['id'] == char_id), None)
    if not char: await update.message.reply_text("❌ Not owned."); return
    COST = 5000
    if user.get('balance', 0) < COST: await update.message.reply_text(f"❌ Need {COST} coins."); return
    await col_users.update_one({'id': user_id}, {'$set': {'married_to': char}, '$inc': {'balance': -COST}})
    await update.message.reply_text(f"💍 Married **{char['name']}**!")

async def divorce(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    await col_users.update_one({'id': user_id}, {'$unset': {'married_to': ""}})
    await update.message.reply_text("💔 Divorced.")

async def burn(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not context.args: return
    char_id = context.args[0]
    user = await col_users.find_one({'id': user_id})
    char = next((c for c in user.get('characters', []) if c['id'] == char_id), None)
    if not char: await update.message.reply_text("❌ Not found."); return
    if user.get('married_to') and user['married_to']['id'] == char_id: await update.message.reply_text("❌ Cannot burn spouse!"); return
    refund = 200
    await col_users.update_one({'id': user_id}, {'$pull': {'characters': {'id': char_id}}, '$inc': {'balance': refund}})
    await update.message.reply_text(f"🔥 Burned **{char['name']}** for {refund} coins.")

async def addshop(update: Update, context: CallbackContext):
    if not await is_admin(update.effective_user.id): return
    try:
        args = context.args
        char_id, price = args[0], int(args[1])
        await col_chars.update_one({'id': char_id}, {'$set': {'price': price}})
        await update.message.reply_text(f"✅ Added to Shop.")
    except: pass

async def shop(update: Update, context: CallbackContext): await send_shop_item(update, context)

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
    else: char = chars[0]; price = char['price']
    caption = f"🌟 **COSMIC BAZAAR** 🌟\nHero: {char['name']}\nTier: {char['rarity']}\nCost: {price}\nID: {char['id']}"
    keyboard = [[InlineKeyboardButton("Claim Hero!", callback_data=f"buy_{char['id']}_{price}")],[InlineKeyboardButton("Next Hero", callback_data="shop_next")]]
    if update.callback_query: await update.callback_query.message.delete(); await context.bot.send_photo(chat_id=update.effective_chat.id, photo=char['img_url'], caption=caption, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    else: await update.message.reply_photo(photo=char['img_url'], caption=caption, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def shop_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split('_')
    user_id = query.from_user.id
    if data[0] == "shop": await send_shop_item(update, context); return
    if data[0] == "buy":
        char_id, price = data[1], int(data[2])
        user = await col_users.find_one({'id': user_id})
        if user.get('balance', 0) < price: await query.answer("❌ Not enough coins!", show_alert=True); return
        char = await col_chars.find_one({'id': char_id})
        if not char: return
        await col_users.update_one({'id': user_id}, {'$inc': {'balance': -price}, '$push': {'characters': char}})
        await query.answer("✅ Purchased!", show_alert=True)
        await query.message.edit_caption(caption=f"✅ **SOLD!**\n{char['name']} is yours!")

# --- HAREM & INLINE ---
async def harem(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if update.message.reply_to_message: user_id = update.message.reply_to_message.from_user.id
    user = await col_users.find_one({'id': user_id})
    if not user or not user.get('characters'): await update.message.reply_text("❌ Empty."); return
    await send_harem_page(update, context, sorted(anime_map.keys()), anime_map, 0, user_id, user.get('name', 'User'), "img")

async def send_harem_page(update, context, sorted_animes, anime_map, page, user_id, user_name, mode):
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
    
    title = "🍃 Harem" if mode == "img" else "🎬 AMV Collection"
    msg = f"<b>{title} - {user_name}</b>\nPage {page+1}/{total_pages}\n\n"
    for anime in current_animes:
        chars = anime_map[anime]
        msg += f"<b>{anime}</b> {len(chars)}\n"
        for char in chars:
            msg += f"♦️ {get_rarity_emoji(char['rarity'])} <code>{char['id']}</code> {char['name']} ×1\n"
        msg += "\n"

    nav = []
    if page > 0: nav.append(InlineKeyboardButton("⬅️", callback_data=f"h_prev_{user_id}_{page}_{mode}"))
    if page < total_pages - 1: nav.append(InlineKeyboardButton("➡️", callback_data=f"h_next_{user_id}_{page}_{mode}"))
    switch = [[InlineKeyboardButton("Collection", callback_data=f"h_switch_{user_id}_0_img"), InlineKeyboardButton("❤️ AMV", callback_data=f"h_switch_{user_id}_0_amv")]]
    
    markup = InlineKeyboardMarkup(nav + switch) if nav else InlineKeyboardMarkup(switch)
    photo = PHOTO_URL
    if user.get('favorites'): photo = user['favorites']['img_url']
    elif filtered: photo = filtered[-1]['img_url']
    
    if update.callback_query: await update.callback_query.edit_message_caption(caption=msg, parse_mode='HTML', reply_markup=markup)
    else: 
        if mode == 'amv' and filtered and filtered[-1]['type'] == 'amv': await update.message.reply_video(video=photo, caption=msg, parse_mode='HTML', reply_markup=markup)
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
        
        # Re-fetch for page turn
        all_chars = user['characters']
        filtered = [c for c in all_chars if c.get('type', 'img') == mode]
        anime_map = defaultdict(list)
        for char in filtered: anime_map[char['anime']].append(char)
        await send_harem_page(update, context, sorted(anime_map.keys()), anime_map, new_page, user_id, user.get('name', 'User'), mode)
        
    if query.data == "help_menu": await help_menu(update, context)
    if data[0] == "who": await who_have_it(update, context)

# --- CORE ---
async def check(update: Update, context: CallbackContext):
    if not context.args: return
    char = await col_chars.find_one({'id': context.args[0]})
    if not char: await update.message.reply_text("❌ Not found."); return
    caption = f"🌟 **Info**\n🆔 {char['id']}\n📛 {char['name']}\n📺 {char['anime']}\n💎 {char['rarity']}"
    btn = [[InlineKeyboardButton("Who Have It", callback_data=f"who_{char['id']}")]]
    if char.get('type') == 'amv': await update.message.reply_video(video=char['img_url'], caption=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(btn))
    else: await update.message.reply_photo(photo=char['img_url'], caption=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(btn))

async def who_have_it(update: Update, context: CallbackContext):
    char_id = update.callback_query.data.split("_")[1]
    users = await col_users.find({"characters.id": char_id}).to_list(length=10)
    msg = f"<b>Owners:</b>\n" + "\n".join([f"{i+1}. {u.get('name','User')}" for i,u in enumerate(users)])
    await update.callback_query.message.reply_text(msg, parse_mode='HTML')

async def fav(update: Update, context: CallbackContext):
    if not context.args: return
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    char = next((c for c in user.get('characters', []) if c['id'] == context.args[0]), None)
    if not char: return
    await col_users.update_one({'id': user_id}, {'$set': {'favorites': char}})
    await update.message.reply_text(f"❤️ Favorite set: {char['name']}")

# --- GAME ---
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
        char = chars[0]
        last_spawn[update.effective_chat.id] = {'char': char, 'time': time.time()}
        caption = f"✨ A {get_rarity_emoji(char['rarity'])} <b>{char['rarity']}</b> Character Appears! ✨\n🔎 Use /guess to claim!\n💫 Hurry!"
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=char['img_url'], caption=caption, parse_mode='HTML')
    except: pass

async def guess(update: Update, context: CallbackContext):
    try:
        chat_id = update.effective_chat.id
        if chat_id not in last_spawn: return
        guess_w = " ".join(context.args).lower()
        real_n = last_spawn[chat_id]['char']['name'].lower()
        if guess_w == real_n or any(p == guess_w for p in real_n.split()):
            char = last_spawn[chat_id]['char']
            t = round(time.time() - last_spawn[chat_id]['time'], 2)
            bal = 10000000 if update.effective_user.id == OWNER_ID else 40
            await col_users.update_one({'id': update.effective_user.id}, {'$push': {'characters': char}, '$inc': {'balance': bal}, '$set': {'name': update.effective_user.first_name}}, upsert=True)
            updated_user = await col_users.find_one({'id': update.effective_user.id})
            await update.message.reply_text(f"🎉 Correct! +{bal} coins.")
            caption = f"🌟 <b><a href='tg://user?id={update.effective_user.id}'>{update.effective_user.first_name}</a></b> captured!\n📛 {char['name']}\n✨ {char['rarity']}\n⏱️ {t}s"
            await update.message.reply_text(caption, parse_mode='HTML', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("See Harem", switch_inline_query_current_chat=f"collection.{update.effective_user.id}")]]))
            del last_spawn[chat_id]
        else: await update.message.reply_text("❌ Wrong guess!")
    except: pass

# --- MAIN ---
async def web_server():
    async def handle(request): return web.Response(text="Live")
    app = web.Application(); app.router.add_get('/', handle); runner = web.AppRunner(app); await runner.setup(); site = web.TCPSite(runner, '0.0.0.0', PORT); await site.start()
    while True:
        await check_auctions(CallbackContext(app))
        await asyncio.sleep(60)

async def main():
    await web_server()
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rupload", rupload))
    app.add_handler(CommandHandler("addshop", addshop))
    app.add_handler(CommandHandler("delete", delete))
    app.add_handler(CommandHandler("changetime", changetime))
    app.add_handler(CommandHandler("ctime", changetime)) 
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("rmadmin", rm_admin))
    app.add_handler(CommandHandler("bcast", bcast))
    
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("gift", gift))
    app.add_handler(CommandHandler("trade", trade)) 
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(CommandHandler("rclaim", rclaim))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(CommandHandler("fav", fav))
    app.add_handler(CommandHandler("rupdate", rupdate))
    
    app.add_handler(CommandHandler("harem", harem))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("marry", marry))
    app.add_handler(CommandHandler("burn", burn))
    app.add_handler(CommandHandler("slots", slots))
    app.add_handler(CommandHandler("divorce", divorce))
    app.add_handler(CommandHandler("guess", guess))
    app.add_handler(CommandHandler("auction", auction))
    app.add_handler(CommandHandler("bid", bid))
    app.add_handler(CommandHandler("createclan", createclan))
    app.add_handler(CommandHandler("joinclan", joinclan))
    app.add_handler(CommandHandler("feed", feed))
    app.add_handler(CommandHandler("coinflip", coinflip))
    app.add_handler(CommandHandler("dice", dice))
    
    app.add_handler(CallbackQueryHandler(harem_callback, pattern="^h_"))
    app.add_handler(CallbackQueryHandler(shop_callback, pattern="^(shop|buy)"))
    app.add_handler(CallbackQueryHandler(help_menu, pattern="help_menu"))
    app.add_handler(CallbackQueryHandler(who_have_it, pattern="^who_"))
    
    app.add_handler(InlineQueryHandler(inline_query))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    print("✅ Bot Started Successfully...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
