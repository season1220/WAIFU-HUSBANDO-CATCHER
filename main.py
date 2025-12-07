import logging
import asyncio
import random
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from motor.motor_asyncio import AsyncIOMotorClient

# --- 1. CONFIGURATION ---
TOKEN = "8578752843:AAHNWJAKLmZ_pc9tHPgyhUtnjOKxtXD6mM8"
MONGO_URL = "mongodb+srv://seasonking:season_123@cluster0.e5zbzap.mongodb.net/?appName=Cluster0"
OWNER_ID = 7164618867
CHANNEL_ID = -1003352372209 
PHOTO_URL = "https://telegra.ph/file/b925c3985f0f325e62e17.jpg"

# --- 2. DATABASE ---
client = AsyncIOMotorClient(MONGO_URL)
db = client['MyNewBot']
col_chars = db['characters']
col_users = db['users']

# --- 3. LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 4. VARIABLES ---
message_counts = {}
last_spawn = {} 

# --- RARITY MAPPING (Number to Name) ---
RARITY_MAP = {
    1: "🥉 Low",
    2: "🥈 Medium",
    3: "🥇 High",
    4: "🔮 Special Edition",
    5: "💠 Elite Edition",
    6: "🦄 Legendary",
    7: "💌 Valentine",
    8: "🧛🏻 Halloween",
    9: "🥶 Winter",
    10: "🍹 Summer",
    11: "⚜️ Royal",
    12: "💍 Luxury Edition"
}

def get_rarity_emoji(rarity_str):
    # Emojis for display logic
    if "Low" in rarity_str: return "⚪" # Display style change kar sakte ho
    for r in RARITY_MAP.values():
        if r == rarity_str:
            return r.split()[0] # Pehla emoji utha lo
    return "✨"

# --- 5. COMMANDS ---

async def start(update: Update, context: CallbackContext):
    caption = (
        "👋 **Namaste! Main Season Waifu hu!**\n\n"
        "Same to Same Nobita Style!\n"
        "Add me to your group to start."
    )
    keyboard = [[InlineKeyboardButton("➕ Add Me to Group", url="http://t.me/seasonwaifuBot?startgroup=new")]]
    await update.message.reply_photo(photo=PHOTO_URL, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))

# --- RUPLOAD COMMAND (Photo Reply + Number) ---
async def rupload(update: Update, context: CallbackContext):
    # Sirf Owner
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Sirf Owner upload kar sakta hai.")
        return

    # Check Reply
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.message.reply_text("⚠️ Kisi Photo par reply karein.")
        return

    try:
        args = context.args
        # Expected: /rupload Name Anime Number
        if len(args) < 3:
            await update.message.reply_text("⚠️ Format: `/rupload Name Anime Number`\nExample: `/rupload nami one-piece 5`")
            return

        # Data Extraction
        name = args[0].replace('-', ' ').title()
        anime = args[1].replace('-', ' ').title()
        
        try:
            rarity_num = int(args[2])
        except ValueError:
            await update.message.reply_text("❌ Last mein Rarity ka Number (1-12) likhein.")
            return

        # Map Number to Rarity Name
        rarity = RARITY_MAP.get(rarity_num)
        if not rarity:
            await update.message.reply_text("❌ Invalid Number! 1 se 12 ke beech hona chahiye.")
            return

        # Get File ID from Reply
        file_id = update.message.reply_to_message.photo[-1].file_id

        # Save to DB
        char_data = {
            'img_url': file_id, # Photo ID save hogi
            'name': name,
            'anime': anime,
            'rarity': rarity,
            'id': str(random.randint(10000, 99999))
        }
        await col_chars.insert_one(char_data)
        
        # Confirmation
        await update.message.reply_text(f"✅ **Uploaded Successfully!**\n📛 {name}\n✨ {rarity}")
        
        # Channel Log
        await context.bot.send_photo(
            chat_id=CHANNEL_ID, 
            photo=file_id, 
            caption=f"🆕 **New Character Added!**\n\n📛 **Name:** {name}\n🌈 **Anime:** {anime}\n✨ **Rarity:** {rarity}"
        )

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

# --- COMMANDS: HAREM, BALANCE ETC ---
async def balance(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    bal = user.get('balance', 0) if user else 0
    await update.message.reply_text(f"💰 **Your Balance:** {bal} coins.")

async def harem(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = await col_users.find_one({'id': user_id})
    if not user or not user.get('characters'):
        await update.message.reply_text("❌ Aapke paas koi character nahi hai.")
        return
    msg = f"📚 **{update.effective_user.first_name}'s Collection:**\n\n"
    for char in user['characters']:
        # Simple display
        msg += f"{char['rarity'][0]} {char['name']} ({char['rarity']})\n"
    if len(msg) > 4000: msg = msg[:4000] + "..."
    await update.message.reply_text(msg)

# --- GAME ENGINE ---
async def message_handler(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    if chat_id not in message_counts: message_counts[chat_id] = 0
    message_counts[chat_id] += 1

    if message_counts[chat_id] >= 5: # Testing ke liye fast
        message_counts[chat_id] = 0
        await spawn_character(update, context)

async def spawn_character(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    pipeline = [{'$sample': {'size': 1}}]
    chars = await col_chars.aggregate(pipeline).to_list(length=1)
    if not chars: return 

    character = chars[0]
    last_spawn[chat_id] = {'char': character, 'time': time.time()}

    # Emoji from string
    emoji = character['rarity'].split()[0] # Pehla akshar emoji hai

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption=f"⚡ A wild **{emoji} {character['rarity']}** character appeared!\n/guess Name to catch!",
        parse_mode='Markdown'
    )

async def guess(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if chat_id not in last_spawn: return 

    if not context.args: return
    user_guess = " ".join(context.args).lower()
    correct_name = last_spawn[chat_id]['char']['name'].lower()

    if user_guess == correct_name:
        char_data = last_spawn[chat_id]['char']
        time_taken = round(time.time() - last_spawn[chat_id]['time'], 2)
        
        COIN_REWARD = 40

        await col_users.update_one(
            {'id': user_id},
            {
                '$push': {'characters': char_data}, 
                '$inc': {'balance': COIN_REWARD}, 
                '$set': {'name': update.effective_user.first_name}
            },
            upsert=True
        )

        updated_user = await col_users.find_one({'id': user_id})
        new_balance = updated_user['balance']
        
        rarity_display = char_data['rarity'] # Pura string jaise "💠 Elite Edition"

        # Message 1
        await update.message.reply_text(
            f"🎉 Congratulations! You have earned {COIN_REWARD} coins for guessing correctly!\n"
            f"Your new balance is {new_balance} coins."
        )

        # Message 2
        user_link = f"<a href='tg://user?id={user_id}'>{update.effective_user.first_name}</a>"
        
        caption = (
            f"🌟 <b>{user_link}</b>, you've captured a new character! 🎊\n\n"
            f"📛 <b>NAME:</b> {char_data['name']}\n"
            f"🌈 <b>ANIME:</b> {char_data['anime']}\n"
            f"✨ <b>RARITY:</b> {rarity_display}\n\n"
            f"⏱️ <b>TIME TAKEN:</b> {time_taken} seconds"
        )
        
        keyboard = [[InlineKeyboardButton("See Harem", switch_inline_query_current_chat=f"collection.{user_id}")]]

        await update.message.reply_text(
            caption,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        del last_spawn[chat_id]

# --- RUN ---
def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    # Nayi command: /rupload
    app.add_handler(CommandHandler("rupload", rupload))
    
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("harem", harem))
    app.add_handler(CommandHandler("guess", guess))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("✅ Bot Started with /rupload...")
    app.run_polling()

if __name__ == "__main__":
    main()
