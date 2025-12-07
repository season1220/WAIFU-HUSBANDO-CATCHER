import logging
import asyncio
import random
import time
import math
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
VIDEO_URL = "https://graph.org/file/9b0d2432bd337372295a6.mp4"
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

# --- ERROR HANDLER (FIX FOR YOUR ERROR) ---
async def error_handler(update: object, context: CallbackContext) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

# --- 5. COMMANDS ---

async def start(update: Update, context: CallbackContext):
    try:
        uptime = get_readable_time(int(time.time() - START_TIME))
        ping = f"{random.choice([12, 19, 25, 31])} ms"
        
        caption = f"""
✨ 𝐒𝐞𝐚𝐬𝐨𝐧 𝐖𝐚𝐢𝐟𝐮 𝐂𝐚𝐭𝐜𝐡𝐞𝐫 — @{BOT_USERNAME}
𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐭𝐨 𝐭𝐡𝐞 𝐄𝐥𝐢𝐭𝐞 𝐖𝐚𝐢𝐟𝐮 𝐒𝐲𝐬𝐭𝐞𝐦.

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
        
        await update.message.reply_video(video=VIDEO_URL, caption=caption, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Start Error: {e}")

async def help_menu(update: Update, context: CallbackContext):
    msg = """
<b>⚙️ COMMAND LIST</b>
/guess - Catch character
/harem - View collection
/shop - Cosmic Bazaar
/market - Global Market
/trade - Trade characters
/gift - Gift character
/daily - Free coins
/top - Leaderboard
/check - Check Info
"""
    if update.callback_query: await update.callback_query.message.reply_text(msg, parse_mode='HTML')
    else: await update.message.reply_text(msg, parse_mode='HTML')

# --- ADMIN COMMANDS ---

async def rupload(update: Update, context: CallbackContext):
    if not await is_admin(update.effective_user.id): return
    msg = update.message.reply_to_message
    if not msg: return

    file_id = None
    c_type = "img"
    if msg.photo: file_id = msg.photo[-1].file_id
    elif msg.video: file_id = msg.video.file_id; c_type = "amv"
    elif msg.animation: file_id = msg.animation.file_id; c_type = "amv"
    
    if not file_id: return

    try:
        args = context.args
        if len(args) < 3:
            await update.message.reply_text("⚠️ `/rupload Name Anime Number`")
            return

        name = args[0].replace('-', ' ').title()
        anime = args[1].replace('-', ' ').title()
        try: rarity = RARITY_MAP.get(int(args[2]), "✨ Special")
        except: rarity = "✨ Special"

        char_id = await get_next_id()
        char_data = {'img_url': file_id, 'name': name, 'anime': anime, 'rarity': rarity, 'id': char_id, 'type': c_type}
        await col_chars.insert_one(char_data)
        
        await col_users.update_one({'id': update.effective_user.id}, {'$push': {'characters': char_data}}, upsert=True)

        await update.message.reply_text(f"✅ **Uploaded!**\n🆔 `{char_id}`")
        caption = f"Character Name: {name}\nAnime Name: {anime}\nRarity: {rarity}\nID: {char_id}"
        
        if c_type == "amv": await context.bot.send_video(chat_id=CHANNEL_ID, video=file_id, caption=caption)
        else: await context.bot.send_photo(chat_id=CHANNEL_ID, photo=file_id, caption=caption)

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
    if res.deleted_count: await update.message.reply_text("✅ Deleted.")
    else: await update.message.reply_text("❌ Not found.")

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
    if not update.message.reply_to_message: return
    new_admin = update.message.reply_to_message.from_user.id
    await col_settings.update_one({'_id': 'admins'}, {'$addToSet': {'list': new_admin}}, upsert=True)
    await update.message.reply_text("✅ Admin Added.")

async def rm_admin(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID: return
    if not update.message.reply_to_message: return
    rem_admin = update.message.reply_to_message.from_user.id
    await col_settings.update_one({'_id': 'admins'}, {'$pull': {'list': rem_admin}})
    await update.message.reply_text("✅ Admin Removed.")

# --- FEATURES ---

async def daily(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    if not user: return
    last_daily = user.get('last_daily', 0)
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
    await col_users.update_one({'id': receiver_id}, {'$push': {'characters': character}}, upsert=True)
    await update.message.reply_text(f"🎁 Gifted **{character['name']}**!")

async def trade(update: Update, context: CallbackContext): await gift(update, context)

async def top(update: Update, context: CallbackContext):
    cursor = col_users.find({})
    users = []
    async for user in cursor:
        if 'characters' in user: users.append({'name': user.get('name', 'User'), 'count': len(user['characters'])})
    users = sorted(users, key=lambda x: x['count'], reverse=True)[:10]
    msg = "🏆 **LEADERBOARD**\n\n"
    for i, user in enumerate(users, 1): msg += f"{i}. {user['name']} ➾ {user['count']}\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def balance(update: Update, context: CallbackContext):
    user = await col_users.find_one({'id': update.effective_user.id})
    bal = user.get('balance', 0) if user else 0
    await update.message.reply_text(f"💰 **Balance:** {bal} coins")

async def rclaim(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    if not user: return
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
        for r, p in RARITY_PRICE.items(): 
            if r in char['rarity']: price = p; break
    else: char = chars[0]; price = char['price']
    caption = f"🌟 **COSMIC BAZAAR** 🌟\nHero: {char['name']}\nTier: {char['rarity']}\nCost: {price}\nID: {char['id']}"
    keyboard = [[InlineKeyboardButton("Claim", callback_data=f"buy_{char['id']}_{price}")],[InlineKeyboardButton("Next", callback_data="shop_next")]]
    if update.callback_query: await update.callback_query.message.delete(); await context.bot.send_photo(chat_id=update.effective_chat.id, photo=char['img_url'], caption=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else: await update.message.reply_photo(photo=char['img_url'], caption=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def shop_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split('_')
    user_id = query.from_user.id
    if data[0] == "shop": await send_shop_item(update, context); return
    if data[0] == "buy":
        char_id, price = data[1], int(data[2])
        user = await col_users.find_one({'id': user_id})
        if user.get('balance', 0) < price: await query.answer("No Money!", show_alert=True); return
        char = await col_chars.find_one({'id': char_id})
        if not char: return
        await col_users.update_one({'id': user_id}, {'$inc': {'balance': -price}, '$push': {'characters': char}})
        await query.answer("Purchased!", show_alert=True)

# --- HAREM ---
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
        if update.callback_query: await update.callback_query.answer("No AMVs", show_alert=True)
        return

    anime_map = defaultdict(list)
    for char in filtered: anime_map[char['anime']].append(char)
    sorted_animes = sorted(anime_map.keys())

    CHUNK = 4
    total_pages = math.ceil(len(sorted_animes) / CHUNK)
    if page < 0: page = 0
    if page >= total_pages: page = total_pages - 1
    
    current_animes = sorted_animes[page * CHUNK : (page + 1) * CHUNK]
    
    title = "—͟͞𝕊𝔼𝔸𝕊𝕆ℕ 𝕂𝕀ℕ𝔾✠'s Harem"
    msg = f"<b>{title} - Page {page+1}/{total_pages}</b>\n\n"
    
    for anime in current_animes:
        chars = anime_map[anime]
        msg += f"<b>{anime} {len(chars)}</b>\n"
        for char in chars:
            emoji = get_rarity_emoji(char['rarity'])
            msg += f"♦️ [ {emoji} ] <code>{char['id']}</code> {char['name']} ×1\n"
        msg += "\n"

    nav = []
    if page > 0: nav.append(InlineKeyboardButton("⬅️", callback_data=f"h_prev_{user_id}_{page}_{mode}"))
    if page < total_pages - 1: nav.append(InlineKeyboardButton("➡️", callback_data=f"h_next_{user_id}_{page}_{mode}"))
    
    switch = [
        InlineKeyboardButton("Collection", callback_data=f"h_switch_{user_id}_0_img"),
        InlineKeyboardButton("❤️ AMV", callback_data=f"h_switch_{user_id}_0_amv")
    ]
    
    markup = InlineKeyboardMarkup([nav, switch]) if nav else InlineKeyboardMarkup([switch])
    
    photo = VIDEO_URL # Default
    if user.get('favorites'): photo = user['favorites']['img_url']
    elif filtered: photo = filtered[-1]['img_url']

    if update.callback_query:
        await update.callback_query.edit_message_caption(caption=msg, parse_mode='HTML', reply_markup=markup)
    else:
        if mode == 'amv' and filtered and filtered[-1]['type'] == 'amv':
             await update.message.reply_video(video=photo, caption=msg, parse_mode='HTML', reply_markup=markup)
        else:
             await update.message.reply_photo(photo=photo, caption=msg, parse_mode='HTML', reply_markup=markup)

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
    except: pass

async def guess(update: Update, context: CallbackContext):
    try:
        chat_id = update.effective_chat.id
        if chat_id not in last_spawn: await update.message.reply_text("❌ No character spawned!"); return 
        if not context.args: return
        guess_w = " ".join(context.args).lower()
        real_n = last_spawn[chat_id]['char']['name'].lower()
        if guess_w == real_n or any(p == guess_w for p in real_n.split()):
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

# --- WEB SERVER & MAIN ---
async def web_server():
    async def handle(request): return web.Response(text="Bot is Live!")
    app = web.Application(); app.router.add_get('/', handle); runner = web.AppRunner(app); await runner.setup(); site = web.TCPSite(runner, '0.0.0.0', PORT); await site.start()

async def main():
    await web_server()
    app = Application.builder().token(TOKEN).build()
    
    app.add_error_handler(error_handler) # ERROR HANDLER ADDED HERE

    handlers = [
        CommandHandler("start", start), CommandHandler("rupload", rupload), CommandHandler("addshop", addshop),
        CommandHandler("delete", delete), CommandHandler("changetime", changetime), CommandHandler("ctime", changetime),
        CommandHandler("addadmin", add_admin), CommandHandler("rmadmin", rm_admin), CommandHandler("bcast", bcast),
        CommandHandler("balance", balance), CommandHandler("daily", daily), CommandHandler("gift", gift),
        CommandHandler("trade", trade), CommandHandler("top", top), CommandHandler("shop", shop),
        CommandHandler("rclaim", rclaim), CommandHandler("check", check), CommandHandler("fav", fav),
        CommandHandler("harem", harem), CommandHandler("guess", guess),
        CallbackQueryHandler(harem_callback, pattern="^h_"), CallbackQueryHandler(shop_callback, pattern="^(shop|buy)"),
        CallbackQueryHandler(help_menu, pattern="help_menu"), CallbackQueryHandler(who_have_it, pattern="^who_"),
        InlineQueryHandler(inline_query), MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
    ]
    for h in handlers: app.add_handler(h)
    
    await app.initialize(); await app.start(); await app.updater.start_polling(); await asyncio.Event().wait()

if __name__ == "__main__": asyncio.run(main())
