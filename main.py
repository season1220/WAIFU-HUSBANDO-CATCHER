import logging
import asyncio
import random
import time
import math
from datetime import datetime
from collections import defaultdict
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
PHOTO_URL = "https://telegra.ph/file/b925c3985f0f325e62e17.jpg"
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
col_market = db['market'] # User Market

# --- 3. LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 4. VARIABLES ---
message_counts = {}
last_spawn = {} 
START_TIME = time.time()

# --- 5. HELPER FUNCTIONS ---
RARITY_ORDER = [
    "Low", "Medium", "High", "Special Edition", "Elite Edition", 
    "Legendary", "Valentine", "Halloween", "Winter", "Summer", 
    "Royal", "Luxury Edition"
]

def get_rarity_emoji(rarity):
    if not rarity: return "✨"
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

# --- 6. CORE COMMANDS ---

async def start(update: Update, context: CallbackContext):
    uptime = get_readable_time(int(time.time() - START_TIME))
    ping = f"{random.choice([1.2, 0.9, 1.5, 2.1])} ms"
    caption = f"""
🌿 <b>GREETINGS, I’M ︙ SEASON WAIFU CATCHER ︙ @{BOT_USERNAME}</b>
°○°, NICE TO MEET YOU!

───────────𖤐𖤐𖤐───────────
◎ <b>WHAT I DO:</b> I SPAWN WAIFUS IN YOUR CHAT.
◎ <b>TO USE ME:</b> ADD ME TO YOUR GROUP.
───────────𖤐𖤐𖤐───────────

📶 <b>PING:</b> {ping}
⏱️ <b>UPTIME:</b> {uptime}
"""
    keyboard = [
        [InlineKeyboardButton("👥 ADD ME TO YOUR GROUP", url=f"http://t.me/{BOT_USERNAME}?startgroup=new")],
        [InlineKeyboardButton("🔧 SUPPORT", url=f"https://t.me/{BOT_USERNAME}"), InlineKeyboardButton("📣 CHANNEL", url=f"https://t.me/{BOT_USERNAME}")],
        [InlineKeyboardButton("❓ HELP", callback_data="help_menu")],
        [InlineKeyboardButton("🔎 SEARCH (INLINE)", switch_inline_query_current_chat="")],
        [InlineKeyboardButton(f"👑 OWNER — @{OWNER_USERNAME}", url=f"https://t.me/{OWNER_USERNAME}")]
    ]
    await update.message.reply_photo(photo=PHOTO_URL, caption=caption, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def help_menu(update: Update, context: CallbackContext):
    msg = """
<b>⚙️ GOD MODE COMMANDS</b>
/guess - Catch character
/harem - Collection
/fuse - Evolution (3 Low -> 1 Medium)
/market - Global User Market
/sell - Sell character to users
/buy - Buy from users
/adventure - Go on mission
/marry - Marry character
/burn - Sell to system
/shop - Admin Shop
/daily - Free coins
/rclaim - Free character
"""
    if update.callback_query: await update.callback_query.message.reply_text(msg, parse_mode='HTML')
    else: await update.message.reply_text(msg, parse_mode='HTML')

# --- 7. FUSION / EVOLUTION SYSTEM ---
async def fuse(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("🧬 **Fusion:** `/fuse [Character Name]`\n(Need 3 same characters of same rarity)")
        return
    
    char_name = " ".join(context.args).title()
    user = await col_users.find_one({'id': user_id})
    if not user: return

    # Find duplicates
    duplicates = [c for c in user.get('characters', []) if c['name'].lower() == char_name.lower()]
    
    if len(duplicates) < 3:
        await update.message.reply_text(f"❌ Not enough duplicates! You have {len(duplicates)}/3 of **{char_name}**.")
        return

    # Check Rarity
    base_rarity = duplicates[0]['rarity']
    # Ensure all 3 are same rarity (simplified)
    to_fuse = duplicates[:3]
    
    # Find Next Rarity
    try:
        current_index = -1
        for i, r in enumerate(RARITY_ORDER):
            if r in base_rarity:
                current_index = i
                break
        
        if current_index == -1 or current_index >= len(RARITY_ORDER) - 1:
            await update.message.reply_text("❌ This character is already at MAX Level!")
            return
            
        next_rarity = RARITY_ORDER[current_index + 1]
    except:
        await update.message.reply_text("❌ Error in evolution.")
        return

    # Remove 3 old chars
    for char in to_fuse:
        await col_users.update_one({'id': user_id}, {'$pull': {'characters': {'id': char['id']}}})
    
    # Add 1 new char (Same details, new rarity, new ID)
    new_char = to_fuse[0].copy()
    new_char['rarity'] = next_rarity
    new_char['id'] = str(random.randint(100000, 999999)) # Temp ID for fused
    
    await col_users.update_one({'id': user_id}, {'$push': {'characters': new_char}})
    
    await update.message.reply_text(f"🧬 **FUSION SUCCESS!**\n\n3x {base_rarity} **{char_name}** fused into...\n✨ **{next_rarity} {char_name}!** 🎉")

# --- 8. GLOBAL MARKET (USER TO USER) ---
async def sell(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ **Format:** `/sell [ID] [Price]`")
        return
    
    char_id, price = context.args[0], int(context.args[1])
    if price < 1: return

    user = await col_users.find_one({'id': user_id})
    char = next((c for c in user.get('characters', []) if c['id'] == char_id), None)
    
    if not char:
        await update.message.reply_text("❌ You don't own this character.")
        return

    # Remove from user, Add to Market
    await col_users.update_one({'id': user_id}, {'$pull': {'characters': {'id': char_id}}})
    market_item = char.copy()
    market_item['price'] = price
    market_item['seller_id'] = user_id
    market_item['seller_name'] = update.effective_user.first_name
    
    await col_market.insert_one(market_item)
    await update.message.reply_text(f"🏛️ **Listed on Market!**\n{char['name']} for {price} coins.")

async def market(update: Update, context: CallbackContext):
    items = await col_market.find({}).to_list(length=10) # Show first 10
    if not items:
        await update.message.reply_text("🏛️ Market is empty.")
        return
    
    msg = "🏛️ **GLOBAL MARKET**\n\n"
    for item in items:
        msg += f"🆔 `{item['id']}` : {item['name']} - 💰 {item['price']} (Seller: {item['seller_name']})\n"
    
    msg += "\nUse `/buy [ID]` to purchase."
    await update.message.reply_text(msg, parse_mode='Markdown')

async def buy(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("⚠️ `/buy [ID]`")
        return
    
    char_id = context.args[0]
    item = await col_market.find_one({'id': char_id})
    if not item:
        await update.message.reply_text("❌ Item sold or invalid.")
        return
    
    buyer = await col_users.find_one({'id': user_id})
    if buyer.get('balance', 0) < item['price']:
        await update.message.reply_text("❌ Not enough coins.")
        return

    # Transact
    await col_users.update_one({'id': user_id}, {'$inc': {'balance': -item['price']}, '$push': {'characters': item}})
    await col_users.update_one({'id': item['seller_id']}, {'$inc': {'balance': item['price']}})
    await col_market.delete_one({'id': char_id})
    
    await update.message.reply_text(f"✅ **Purchase Successful!**\nYou bought **{item['name']}** for {item['price']} coins.")

# --- 9. ADVENTURE SYSTEM (RPG) ---
async def adventure(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    if not user: return

    # Cooldown (1 Hour)
    last_adv = user.get('last_adventure', 0)
    if time.time() - last_adv < 3600:
        rem = int(3600 - (time.time() - last_adv)) // 60
        await update.message.reply_text(f"⏳ Your heroes are resting! Try again in {rem} minutes.")
        return

    await col_users.update_one({'id': user_id}, {'$set': {'last_adventure': time.time()}})
    
    # Outcome
    events = [
        ("found a treasure chest!", 500),
        ("defeated a goblin!", 300),
        ("helped a villager!", 200),
        ("found nothing but fresh air.", 0),
        ("tripped and lost some coins.", -50)
    ]
    event, coins = random.choice(events)
    
    await col_users.update_one({'id': user_id}, {'$inc': {'balance': coins}})
    
    msg = f"⚔️ **Adventure Report**\nYou went on a journey and... **{event}**"
    if coins > 0: msg += f"\n💰 Earned: {coins} coins."
    elif coins < 0: msg += f"\n💸 Lost: {abs(coins)} coins."
    
    await update.message.reply_text(msg, parse_mode='Markdown')

# --- EXISTING COMMANDS (Kept Intact) ---
# ... (All previous commands like Upload, Harem, etc. are below) ...

async def rupload(update: Update, context: CallbackContext):
    if not await is_admin(update.effective_user.id): return
    if not update.message.reply_to_message or not update.message.reply_to_message.photo: return
    try:
        args = context.args
        if len(args) < 3: return
        name = args[0].replace('-', ' ').title()
        anime = args[1].replace('-', ' ').title()
        try: rarity = RARITY_MAP.get(int(args[2]), "✨ Special")
        except: rarity = "✨ Special"
        file_id = update.message.reply_to_message.photo[-1].file_id
        char_id = await get_next_id()
        uploader_name = update.effective_user.first_name
        char_data = {'img_url': file_id, 'name': name, 'anime': anime, 'rarity': rarity, 'id': char_id}
        await col_chars.insert_one(char_data)
        await col_users.update_one({'id': update.effective_user.id}, {'$push': {'characters': char_data}, '$set': {'name': uploader_name}}, upsert=True)
        await update.message.reply_text(f"✅ **Uploaded!**\n🆔 ID: `{char_id}`")
        caption = (f"Character Name: {name}\nAnime Name: {anime}\nRarity: {rarity}\nID: {char_id}\nAdded by <a href='tg://user?id={update.effective_user.id}'>{uploader_name}</a>")
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=file_id, caption=caption, parse_mode='HTML')
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
    if user_id != OWNER_ID and (freq < 80 or freq > 300):
        await update.message.reply_text("❌ Limit: 80 - 300.")
        return
    await col_settings.update_one({'_id': str(update.effective_chat.id)}, {'$set': {'freq': freq}}, upsert=True)
    await update.message.reply_text(f"✅ Frequency: {freq}")

async def bcast(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID: return
    if not update.message.reply_to_message: return
    msg = update.message.reply_to_message
    users = await col_users.find({}).to_list(length=None)
    sent = 0
    await update.message.reply_text(f"📢 Broadcasting...")
    for u in users:
        try: await msg.copy(chat_id=u['id']); sent += 1; await asyncio.sleep(0.1)
        except: pass
    await update.message.reply_text(f"✅ Sent to {sent} users.")

async def add_admin(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID: return
    if not update.message.reply_to_message: return
    new_admin = update.message.reply_to_message.from_user.id
    await col_settings.update_one({'_id': 'admins'}, {'$addToSet': {'list': new_admin}}, upsert=True)
    await update.message.reply_text(f"✅ Added Admin.")

async def rm_admin(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID: return
    if not update.message.reply_to_message: return
    rem_admin = update.message.reply_to_message.from_user.id
    await col_settings.update_one({'_id': 'admins'}, {'$pull': {'list': rem_admin}})
    await update.message.reply_text(f"✅ Removed Admin.")

async def daily(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    if not user: await update.message.reply_text("Play first!"); return
    last_daily = user.get('last_daily', 0)
    if time.time() - last_daily < 86400: await update.message.reply_text("❌ Kal aana!"); return
    await col_users.update_one({'id': user_id}, {'$inc': {'balance': 500}, '$set': {'last_daily': time.time()}})
    await update.message.reply_text("🎁 **Daily Reward!** +500 coins!")

async def gift(update: Update, context: CallbackContext):
    sender_id = update.effective_user.id
    if not update.message.reply_to_message: return
    receiver_id = update.message.reply_to_message.from_user.id
    if sender_id == receiver_id: return
    if not context.args: return
    char_id = context.args[0]
    sender = await col_users.find_one({'id': sender_id})
    character = next((c for c in sender.get('characters', []) if c['id'] == char_id), None)
    if not character: await update.message.reply_text("❌ Not found."); return
    await col_users.update_one({'id': sender_id}, {'$pull': {'characters': {'id': char_id}}})
    await col_users.update_one({'id': receiver_id}, {'$push': {'characters': character}}, upsert=True)
    await update.message.reply_text(f"🎁 Gifted **{character['name']}**!")

async def trade(update: Update, context: CallbackContext): await gift(update, context)

async def top(update: Update, context: CallbackContext):
    cursor = col_users.find({})
    users = []
    async for user in cursor:
        if 'characters' in user: users.append({'name': user.get('name', 'Unknown'), 'count': len(user['characters'])})
    users = sorted(users, key=lambda x: x['count'], reverse=True)[:10]
    msg = "🏆 **LEADERBOARD**\n\n"
    for i, user in enumerate(users, 1): msg += f"{i}. {user['name']} ➾ {user['count']}\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def balance(update: Update, context: CallbackContext):
    user = await col_users.find_one({'id': update.effective_user.id})
    await update.message.reply_text(f"💰 **Balance:** {user.get('balance', 0) if user else 0} coins")

async def rclaim(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    if not user: return
    last_rclaim = user.get('last_rclaim', 0)
    if time.time() - last_rclaim < 86400: await update.message.reply_text("❌ Kal aana."); return
    pipeline = [{'$sample': {'size': 1}}]
    chars = await col_chars.aggregate(pipeline).to_list(length=1)
    if not chars: return
    char = chars[0]
    await col_users.update_one({'id': user_id}, {'$push': {'characters': char}, '$set': {'last_rclaim': time.time()}})
    await update.message.reply_photo(photo=char['img_url'], caption=f"🎁 **FREE CHARACTER!**\n📛 {char['name']}")

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
    characters = user['characters']
    anime_map = defaultdict(list)
    for char in characters: anime_map[char['anime']].append(char)
    await send_harem_page(update, context, sorted(anime_map.keys()), anime_map, 0, user_id, user.get('name', 'User'), "img")

async def send_harem_page(update, context, sorted_animes, anime_map, page, user_id, user_name, mode):
    CHUNK_SIZE = 5
    total_pages = math.ceil(len(sorted_animes) / CHUNK_SIZE)
    if page < 0: page = 0
    if page >= total_pages: page = total_pages - 1
    current_animes = sorted_animes[page * CHUNK_SIZE : (page + 1) * CHUNK_SIZE]
    msg = f"<b>🍃 {user_name}'s Harem</b>\n\n"
    for anime in current_animes:
        chars = anime_map[anime]
        msg += f"<b>{anime}</b> {len(chars)}\n"
        for char in chars: msg += f"♦️ {get_rarity_emoji(char['rarity'])} <code>{char['id']}</code> {char['name']} ×1\n"
        msg += "\n"
    buttons = [[InlineKeyboardButton("⬅️", callback_data=f"h_prev_{user_id}_{page}"), InlineKeyboardButton("➡️", callback_data=f"h_next_{user_id}_{page}")]]
    reply_markup = InlineKeyboardMarkup(buttons)
    if update.callback_query: await update.callback_query.edit_message_caption(caption=msg, parse_mode='HTML', reply_markup=reply_markup)
    else: await update.message.reply_text(msg, parse_mode='HTML', reply_markup=reply_markup)

async def harem_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split('_')
    if data[0] == "h":
        action, user_id, page = data[1], int(data[2]), int(data[3])
        if query.from_user.id != user_id: await query.answer("❌ Not yours!", show_alert=True); return
        user = await col_users.find_one({'id': user_id})
        anime_map = defaultdict(list)
        for char in user['characters']: anime_map[char['anime']].append(char)
        new_page = page - 1 if action == "prev" else page + 1
        await send_harem_page(update, context, sorted(anime_map.keys()), anime_map, new_page, user_id, user.get('name', 'User'), "img")
    if query.data == "help_menu": await help_menu(update, context)
    if data[0] == "who": await who_have_it(update, context)

async def inline_query(update: Update, context: CallbackContext):
    query = update.inline_query.query
    user_id = update.effective_user.id
    results = []
    if query.lower().startswith("collection") or query.lower().startswith("harem"):
        user = await col_users.find_one({'id': user_id})
        if user and 'characters' in user:
            for char in user['characters'][::-1][:50]:
                caption = f"<b>Name:</b> {char['name']}\n<b>Rarity:</b> {char['rarity']}\n<b>ID:</b> {char['id']}"
                results.append(InlineQueryResultPhoto(id=str(uuid4()), photo_url=char['img_url'], thumbnail_url=char['img_url'], caption=caption, parse_mode='HTML'))
    else:
        cursor = col_chars.find({}).limit(50) if not query else col_chars.find({"name": {"$regex": query, "$options": "i"}}).limit(50)
        async for char in cursor:
            caption = f"<b>Name:</b> {char['name']}\n<b>Rarity:</b> {char['rarity']}\n<b>ID:</b> {char['id']}"
            results.append(InlineQueryResultPhoto(id=str(uuid4()), photo_url=char['img_url'], thumbnail_url=char['img_url'], caption=caption, parse_mode='HTML'))
    await update.inline_query.answer(results, cache_time=5, is_personal=True)

# --- CORE ---
async def check(update: Update, context: CallbackContext):
    if not context.args: return
    char = await col_chars.find_one({'id': context.args[0]})
    if not char: await update.message.reply_text("❌ Not found."); return
    caption = f"🌟 **Info**\n🆔 {char['id']}\n📛 {char['name']}\n📺 {char['anime']}\n💎 {char['rarity']}"
    btn = [[InlineKeyboardButton("Who Have It", callback_data=f"who_{char['id']}")]]
    await update.message.reply_photo(photo=char['img_url'], caption=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(btn))

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
        pipeline = [{'$sample': {'size': 1}}]
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

async def main():
    await web_server()
    app = Application.builder().token(TOKEN).build()
    
    # Handlers
    handlers = [
        CommandHandler("start", start), CommandHandler("rupload", rupload), CommandHandler("addshop", addshop),
        CommandHandler("delete", delete), CommandHandler("changetime", changetime), CommandHandler("ctime", changetime),
        CommandHandler("addadmin", add_admin), CommandHandler("rmadmin", rm_admin), CommandHandler("bcast", bcast),
        CommandHandler("balance", balance), CommandHandler("daily", daily), CommandHandler("gift", gift),
        CommandHandler("trade", trade), CommandHandler("top", top), CommandHandler("shop", shop),
        CommandHandler("rclaim", rclaim), CommandHandler("check", check), CommandHandler("fav", fav),
        CommandHandler("harem", harem), CommandHandler("profile", profile), CommandHandler("marry", marry),
        CommandHandler("burn", burn), CommandHandler("divorce", divorce), CommandHandler("fuse", fuse),
        CommandHandler("sell", sell), CommandHandler("market", market), CommandHandler("buy", buy),
        CommandHandler("adventure", adventure), CommandHandler("guess", guess),
        CallbackQueryHandler(harem_callback, pattern="^h_"), CallbackQueryHandler(shop_callback, pattern="^(shop|buy)"),
        CallbackQueryHandler(help_menu, pattern="help_menu"), CallbackQueryHandler(who_have_it, pattern="^who_"),
        InlineQueryHandler(inline_query), MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
    ]
    for h in handlers: app.add_handler(h)
    
    await app.initialize(); await app.start(); await app.updater.start_polling(); await asyncio.Event().wait()

if __name__ == "__main__": asyncio.run(main())
