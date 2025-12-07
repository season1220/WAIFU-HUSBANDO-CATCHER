import logging
import asyncio
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from motor.motor_asyncio import AsyncIOMotorClient

# --- 1. CONFIGURATION (Apna Data Yahan Dalein) ---
TOKEN = "8578752843:AAHNWJAKLmZ_pc9tHPgyhUtnjOKxtXD6mM8"
MONGO_URL = "mongodb+srv://seasonking:season_123@cluster0.e5zbzap.mongodb.net/?appName=Cluster0"
OWNER_ID = 7164618867
# Apne Group/Channel ki ID yahan dalein
CHANNEL_ID = -1003352372209 

# --- 2. DATABASE CONNECTION ---
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

# --- 5. COMMANDS ---

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "👋 **Namaste! Main apka Naya Bot hu.**\n"
        "Main bina kisi error ke chal raha hu! 😎"
    )

# --- UPLOAD COMMAND (Owner Only) ---
async def upload(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Sirf Owner upload kar sakta hai.")
        return

    try:
        # Format: /upload ImgUrl Name Anime Rarity
        args = context.args
        if len(args) < 4:
            await update.message.reply_text("⚠️ Format: `/upload URL Name Anime Rarity`")
            return

        img_url = args[0]
        name = args[1].replace('-', ' ').title()
        anime = args[2].replace('-', ' ').title()
        rarity = args[3].title()

        char_data = {
            'img_url': img_url,
            'name': name,
            'anime': anime,
            'rarity': rarity,
            'id': str(random.randint(1000, 9999))
        }
        await col_chars.insert_one(char_data)
        
        await context.bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=img_url,
            caption=f"✅ **New Character!**\nName: {name}\nRarity: {rarity}"
        )
        await update.message.reply_text(f"✅ Uploaded: {name}")

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

# --- SPAWNING ENGINE ---
async def message_handler(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    
    if chat_id not in message_counts: message_counts[chat_id] = 0
    message_counts[chat_id] += 1

    # Har 5 messages par character aayega (Fast Testing ke liye)
    if message_counts[chat_id] >= 5:
        message_counts[chat_id] = 0
        await spawn_character(update, context)

async def spawn_character(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    
    pipeline = [{'$sample': {'size': 1}}]
    chars = await col_chars.aggregate(pipeline).to_list(length=1)
    
    if not chars: return 

    character = chars[0]
    last_spawn[chat_id] = character 

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption=f"⚡ A wild **{character['rarity']}** character appeared!\n/guess Name to catch!",
        parse_mode='Markdown'
    )

# --- GUESSING ENGINE ---
async def guess(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if chat_id not in last_spawn: return 

    if not context.args: return
    user_guess = " ".join(context.args).lower()
    correct_name = last_spawn[chat_id]['name'].lower()

    if user_guess == correct_name:
        character = last_spawn[chat_id]
        
        await col_users.update_one(
            {'id': user_id},
            {'$push': {'characters': character}, '$set': {'name': update.effective_user.first_name}},
            upsert=True
        )

        await update.message.reply_text(
            f"🎉 **Correct!**\n"
            f"👤 **{update.effective_user.first_name}** ne pakda!\n"
            f"📛 Name: **{character['name']}**\n"
            f"✨ Rarity: **{character['rarity']}**"
        )
        
        del last_spawn[chat_id] 

# --- MAIN RUNNER ---
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("upload", upload))
    app.add_handler(CommandHandler("guess", guess))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("✅ Bot Started...")
    app.run_polling()

if __name__ == "__main__":
    main()
