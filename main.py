import asyncio
import logging
from aiohttp import web
from telegram.ext import Application
from db import init_db_collections
from handlers import register_handlers
from utils import PORT, TOKEN

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def web_server():
    async def handle(request):
        return web.Response(text="Live")
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

async def main():
    # optional: initialize DB / indexes if needed
    await web_server()
    # create telegram application
    app = Application.builder().token(TOKEN).build()
    # ensure DB collections are available
    await init_db_collections()
    # register handlers
    register_handlers(app)
    print("Bot is starting... Press Ctrl+C to stop.")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument
from utils import MONGO_URL
import asyncio

client = AsyncIOMotorClient(MONGO_URL)
db = client['MyNewBot']
col_chars = db['characters']
col_users = db['users']
col_settings = db['settings']
col_seq = db['sequences']
col_market = db['market']

async def init_db_collections():
    # Example index creation; keep lightweight
    try:
        await col_chars.create_index('id', unique=True)
        await col_users.create_index('id', unique=True)
        await col_market.create_index('id', unique=True)
        # ensure seq doc exists
        await col_seq.find_one_and_update({'_id': 'char_id'}, {'$setOnInsert': {'seq': 0}}, upsert=True)
    except Exception as e:
        print("init_db_collections error:", e)
import random, time
# --- Configuration (paste your tokens/urls here) ---
TOKEN = "8578752843:AAGUn1AT8qAegWh6myR6aV28RHm2h0LUrXY"
MONGO_URL = "mongodb+srv://seasonking:season_123@cluster0.e5zbzap.mongodb.net/?appName=Cluster0"
OWNER_ID = 7164618867
CHANNEL_ID = -1003352372209
PHOTO_URL = "https://telegra.ph/file/b925c3985f0f325e62e17.jpg"
PORT = 10000
BOT_USERNAME = "seasonwaifuBot"
OWNER_USERNAME = "DADY_JI"

# --- RARITY CONFIG (user-provided new mapping) ---
# New rarities and the emojis requested:
# ISSME 💫 legendary
# 🎃 Halloween
# ❄️ Winter
# 💸 Luxury
# 🔸 Low
# 🔷 Medium
# ♦️ High
# 🔮 Special edition
# 💮 Elite edition
# 💝 Valentine
# 🎗royal
# 🏜 summer

# Rarity order (used for fusion progression)
RARITY_ORDER = [
    "Low", "Medium", "High", "Special Edition", "Elite Edition",
    "Legendary", "Valentine", "Halloween", "Winter", "Summer",
    "Royal", "Luxury Edition"
]

# Map integers (optional) to rarity names if you use numeric rarity on upload
RARITY_MAP = {
    0: "Low",
    1: "Medium",
    2: "High",
    3: "Special Edition",
    4: "Elite Edition",
    5: "Legendary",
    6: "Valentine",
    7: "Halloween",
    8: "Winter",
    9: "Summer",
    10: "Royal",
    11: "Luxury Edition"
}

# Prices for shop by rarity (example)
RARITY_PRICE = {
    "Low": 200,
    "Medium": 500,
    "High": 1200,
    "Special Edition": 2500,
    "Elite Edition": 5000,
    "Legendary": 15000,
    "Valentine": 3000,
    "Halloween": 3000,
    "Winter": 3000,
    "Summer": 3000,
    "Royal": 8000,
    "Luxury Edition": 20000
}

def get_rarity_emoji(rarity: str) -> str:
    if not rarity: return "✨"
    r = rarity.lower()
    # follow user's requested emoji mapping
    if "luxury" in r: return "💸"  # user mapped luxury to 💸
    if "royal" in r: return "🎗"
    if "summer" in r: return "🏜"
    if "winter" in r: return "❄️"
    if "halloween" in r: return "🎃"
    if "valentine" in r: return "💝"
    if "legendary" in r or "issme" in r: return "💫"
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
import time, random, math
from collections import defaultdict
from uuid import uuid4
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultPhoto, Update
from telegram.ext import CallbackContext
from db import col_chars, col_users, col_settings, col_market, col_seq
from utils import (BOT_USERNAME, OWNER_USERNAME, PHOTO_URL, OWNER_ID,
                   get_readable_time, get_rarity_emoji, RARITY_ORDER, RARITY_MAP, RARITY_PRICE)
from pymongo import ReturnDocument

message_counts = {}
last_spawn = {}
START_TIME = time.time()

# --- START / HELP ---
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
        [InlineKeyboardButton("🔗 PINTEREST", url="https://in.pinterest.com/")],
        [InlineKeyboardButton(f"👑 OWNER — @{OWNER_USERNAME}", url=f"https://t.me/{OWNER_USERNAME}")]
    ]
    if update.message:
        await update.message.reply_photo(photo=PHOTO_URL, caption=caption, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    elif update.callback_query:
        await update.callback_query.message.reply_photo(photo=PHOTO_URL, caption=caption, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def help_menu(update: Update, context: CallbackContext):
    msg = """
<b>⚙️ GOD MODE COMMANDS</b>
/guess - Catch character
/harem - Collection
/fuse - Evolution (3 same -> next rarity)
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
    if update.callback_query:
        await update.callback_query.message.reply_text(msg, parse_mode='HTML')
    else:
        await update.message.reply_text(msg, parse_mode='HTML')

# --- FUSE (keeps logic similar to original) ---
async def fuse(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("🧬 **Fusion:** `/fuse [Character Name]`\n(Need 3 same characters of same rarity)")
        return
    char_name = " ".join(context.args).title()
    user = await col_users.find_one({'id': user_id})
    if not user:
        await update.message.reply_text("❌ Start playing first.")
        return
    duplicates = [c for c in user.get('characters', []) if c['name'].lower() == char_name.lower()]
    if len(duplicates) < 3:
        await update.message.reply_text(f"❌ Not enough duplicates! You have {len(duplicates)}/3 of **{char_name}**.")
        return
    base_rarity = duplicates[0]['rarity']
    to_fuse = duplicates[:3]
    # find index
    current_index = -1
    for i, r in enumerate(RARITY_ORDER):
        if r.lower() in base_rarity.lower():
            current_index = i
            break
    if current_index == -1 or current_index >= len(RARITY_ORDER) - 1:
        await update.message.reply_text("❌ This character is already at MAX Level!")
        return
    next_rarity = RARITY_ORDER[current_index + 1]
    for char in to_fuse:
        await col_users.update_one({'id': user_id}, {'$pull': {'characters': {'id': char['id']}}})
    new_char = to_fuse[0].copy()
    new_char['rarity'] = next_rarity
    new_char['id'] = str(random.randint(100000, 999999))
    await col_users.update_one({'id': user_id}, {'$push': {'characters': new_char}})
    await update.message.reply_text(f"🧬 **FUSION SUCCESS!**\n\n3x {base_rarity} **{char_name}** fused into...\n✨ **{next_rarity} {char_name}!** 🎉")

# --- MARKET ---
async def sell(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ **Format:** `/sell [ID] [Price]`")
        return
    char_id, price = context.args[0], int(context.args[1])
    if price < 1:
        await update.message.reply_text("❌ Price must be positive.")
        return
    user = await col_users.find_one({'id': user_id})
    char = next((c for c in user.get('characters', []) if c['id'] == char_id), None)
    if not char:
        await update.message.reply_text("❌ You don't own this character.")
        return
    await col_users.update_one({'id': user_id}, {'$pull': {'characters': {'id': char_id}}})
    market_item = char.copy()
    market_item['price'] = price
    market_item['seller_id'] = user_id
    market_item['seller_name'] = update.effective_user.first_name
    await col_market.insert_one(market_item)
    await update.message.reply_text(f"🏛️ **Listed on Market!**\n{char['name']} for {price} coins.")

async def market(update: Update, context: CallbackContext):
    items = await col_market.find({}).to_list(length=10)
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
    await col_users.update_one({'id': user_id}, {'$inc': {'balance': -item['price']}, '$push': {'characters': item}}, upsert=True)
    await col_users.update_one({'id': item['seller_id']}, {'$inc': {'balance': item['price']}})
    await col_market.delete_one({'id': char_id})
    await update.message.reply_text(f"✅ **Purchase Successful!**\nYou bought **{item['name']}** for {item['price']} coins.")

# --- ADVENTURE ---
async def adventure(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    if not user:
        await update.message.reply_text("❌ Start playing first.")
        return
    last_adv = user.get('last_adventure', 0)
    if time.time() - last_adv < 3600:
        rem = int(3600 - (time.time() - last_adv)) // 60
        await update.message.reply_text(f"⏳ Your heroes are resting! Try again in {rem} minutes.")
        return
    await col_users.update_one({'id': user_id}, {'$set': {'last_adventure': time.time()}})
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

# --- RUPlOAD / ADMIN ---
async def rupload(update: Update, context: CallbackContext):
    # Only admin
    user = update.effective_user
    settings = await col_settings.find_one({'_id': 'admins'})
    admin_list = settings.get('list', []) if settings else []
    if user.id != OWNER_ID and user.id not in admin_list:
        return
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        return
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("⚠️ Usage: reply photo with `/rupload name anime rarity_index` (rarity_index optional)")
        return
    name = args[0].replace('-', ' ').title()
    anime = args[1].replace('-', ' ').title()
    try:
        rarity = RARITY_MAP.get(int(args[2]), "Special Edition")
    except:
        rarity = "Special Edition"
    file_id = update.message.reply_to_message.photo[-1].file_id
    # generate id
    seq = await col_seq.find_one_and_update({'_id': 'char_id'}, {'$inc': {'seq': 1}}, return_document=ReturnDocument.AFTER, upsert=True)
    char_id = str(seq['seq']).zfill(4)
    char_data = {'img_url': file_id, 'name': name, 'anime': anime, 'rarity': rarity, 'id': char_id}
    await col_chars.insert_one(char_data)
    await update.message.reply_text(f"✅ Uploaded! ID: `{char_id}`", parse_mode='Markdown')
    caption = (f"Character Name: {name}\nAnime Name: {anime}\nRarity: {rarity}\nID: {char_id}\nAdded by {user.first_name}")
    try:
        from utils import CHANNEL_ID
        await update.message.reply_photo(photo=file_id, caption=caption, parse_mode='HTML')
    except:
        pass

# --- HAREM ---
async def harem(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
    user = await col_users.find_one({'id': user_id})
    if not user or not user.get('characters'):
        await update.message.reply_text("❌ Empty.")
        return
    characters = user['characters']
    anime_map = defaultdict(list)
    for char in characters:
        anime_map[char['anime']].append(char)
    await send_harem_page(update, context, sorted(anime_map.keys()), anime_map, 0, user_id, user.get('name', 'User'))

async def send_harem_page(update, context, sorted_animes, anime_map, page, user_id, user_name):
    CHUNK_SIZE = 5
    total_pages = max(1, math.ceil(len(sorted_animes) / CHUNK_SIZE))
    if page < 0: page = 0
    if page >= total_pages: page = total_pages - 1
    current_animes = sorted_animes[page * CHUNK_SIZE : (page + 1) * CHUNK_SIZE]
    msg = f"<b>🍃 {user_name}'s Harem</b>\n\n"
    for anime in current_animes:
        chars = anime_map[anime]
        msg += f"<b>{anime}</b> {len(chars)}\n"
        for char in chars:
            msg += f"{get_rarity_emoji(char.get('rarity'))} <code>{char['id']}</code> {char['name']} ×1\n"
        msg += "\n"
    buttons = [[InlineKeyboardButton("⬅️", callback_data=f"h_prev_{user_id}_{page}"), InlineKeyboardButton("➡️", callback_data=f"h_next_{user_id}_{page}")]]
    reply_markup = InlineKeyboardMarkup(buttons)
    if update.callback_query:
        await update.callback_query.edit_message_caption(caption=msg, parse_mode='HTML', reply_markup=reply_markup)
    else:
        await update.message.reply_text(msg, parse_mode='HTML', reply_markup=reply_markup)

# --- MESSAGE SPAWN / GUESS ---
async def message_handler(update: Update, context: CallbackContext):
    try:
        chat_id = str(update.effective_chat.id)
        if chat_id not in message_counts:
            message_counts[chat_id] = 0
        message_counts[chat_id] += 1
        settings = await col_settings.find_one({'_id': chat_id})
        freq = settings.get('freq', 100) if settings else 100
        if message_counts[chat_id] >= freq:
            message_counts[chat_id] = 0
            await spawn_character(update, context)
    except Exception as e:
        print('message_handler error', e)

async def spawn_character(update: Update, context: CallbackContext):
    try:
        pipeline = [{'$sample': {'size': 1}}]
        chars = await col_chars.aggregate(pipeline).to_list(length=1)
        if not chars:
            return
        char = chars[0]
        last_spawn[update.effective_chat.id] = {'char': char, 'time': time.time()}
        caption = f"✨ A {get_rarity_emoji(char.get('rarity'))} <b>{char.get('rarity')}</b> Character Appears! ✨\n🔎 Use /guess to claim!\n💫 Hurry!"
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=char['img_url'], caption=caption, parse_mode='HTML')
    except Exception as e:
        print('spawn error', e)

async def guess(update: Update, context: CallbackContext):
    try:
        chat_id = update.effective_chat.id
        if chat_id not in last_spawn:
            await update.message.reply_text('No characters to guess right now!')
            return
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
        else:
            await update.message.reply_text("❌ Wrong guess!")
    except Exception as e:
        print('guess error', e)

# --- WHO HAVE IT / CHECK / FAV ---
async def check(update: Update, context: CallbackContext):
    if not context.args:
        return
    char = await col_chars.find_one({'id': context.args[0]})
    if not char:
        await update.message.reply_text("❌ Not found.")
        return
    caption = f"🌟 **Info**\n🆔 {char['id']}\n📛 {char['name']}\n📺 {char['anime']}\n💎 {char['rarity']}"
    btn = [[InlineKeyboardButton("Who Have It", callback_data=f"who_{char['id']}")]]
    await update.message.reply_photo(photo=char['img_url'], caption=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(btn))

async def who_have_it(update: Update, context: CallbackContext):
    char_id = update.callback_query.data.split("_")[1]
    users = await col_users.find({"characters.id": char_id}).to_list(length=50)
    msg = f"<b>Owners:</b>\n" + "\n".join([f"{i+1}. {u.get('name','User')}" for i,u in enumerate(users)])
    await update.callback_query.message.reply_text(msg, parse_mode='HTML')

async def fav(update: Update, context: CallbackContext):
    if not context.args:
        return
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    char = next((c for c in user.get('characters', []) if c['id'] == context.args[0]), None)
    if not char:
        return
    await col_users.update_one({'id': user_id}, {'$set': {'favorites': char}})
    await update.message.reply_text(f"❤️ Favorite set: {char['name']}")
    
# --- REGISTER HANDLERS ---
def register_handlers(app):
    from telegram.ext import CommandHandler, MessageHandler, filters, CallbackQueryHandler, InlineQueryHandler
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_menu))
    app.add_handler(CommandHandler("fuse", fuse))
    app.add_handler(CommandHandler("sell", sell))
    app.add_handler(CommandHandler("market", market))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("adventure", adventure))
    app.add_handler(CommandHandler("rupload", rupload))
    app.add_handler(CommandHandler("harem", harem))
    app.add_handler(CommandHandler("rclaim", lambda u,c: c.application.create_task(rclaim(u,c))))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(CommandHandler("fav", fav))
    app.add_handler(CommandHandler("guess", guess))
    app.add_handler(CommandHandler("profile", lambda u,c: c.application.create_task(profile(u,c))))
    app.add_handler(CallbackQueryHandler(harem, pattern="help_menu"))
    app.add_handler(CallbackQueryHandler(who_have_it, pattern="^who_"))
    app.add_handler(CallbackQueryHandler(lambda u,c: c.application.create_task(help_menu(u,c)), pattern="help_menu"))
    app.add_handler(InlineQueryHandler(lambda u,c: c.application.create_task(inline_query(u,c))))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
python-telegram-bot==20.4
motor==3.1.1
pymongo==4.3.3
aiohttp==3.8.4
# Season Waifu Bot - Multi-file Project

This repository contains a multi-file version of your Telegram bot, modularized into:
- `main.py` - entrypoint
- `db.py` - database collections + init
- `utils.py` - config, rarity maps and helper functions
- `handlers.py` - command & callback handlers
- `requirements.txt` - Python dependencies

## Notes
- The bot includes your requested new rarity mapping and emoji mapping.
- The /start message includes a Pinterest link in the buttons as requested.
- Replace tokens/URLs in `utils.py` if you need to change them.
- To run:
  1. Create a virtualenv and install requirements.
  2. `python main.py`
