import logging
from telegram.ext import Application
from motor.motor_asyncio import AsyncIOMotorClient
from pyrogram import Client

# 1. Logging Setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
LOGGER = logging.getLogger(__name__)

# --- 2. DIRECT SETTINGS (No Config File Needed) ---
# Maine aapki saari details yahan bhar di hain
TOKEN = "8578752843:AAHNWJAKLmZ_pc9tHPgyhUtnjOKxtXD6mM8"
mongo_url = "mongodb+srv://seasonking:season_123@cluster0.e5zbzap.mongodb.net/?appName=Cluster0"
OWNER_ID = 7164618867
sudo_users = [7164618867]
CHARA_CHANNEL_ID = -1003352372209
SUPPORT_CHAT = "seasonwaifuBot"
UPDATE_CHAT = "seasonwaifuBot"
BOT_USERNAME = "seasonwaifuBot"
GROUP_ID = -1003352372209
PHOTO_URL = ["https://telegra.ph/file/b925c3985f0f325e62e17.jpg", "https://telegra.ph/file/4211fb191383d895dab9d.jpg"]

# API Details
api_id = 34967775
api_hash = "e6e5dfae5327f90410863f93d8ced26b"

# --- 3. DATABASE CONNECTION ---
client = AsyncIOMotorClient(mongo_url)
db = client['Character_catcher']
collection = db['anime_characters']
user_collection = db["user_collection_lmao"]
group_user_collection = db["group_user_collection"]
top_global_collection = db["top_global_collection"]
pm_users = db["total_pm_users"]

# --- 4. BOT CREATION (PTB + PYROGRAM) ---
# Ye Application hai (Commands ke liye)
application = Application.builder().token(TOKEN).build()

# Ye Shivuu Client hai (User checks ke liye)
shivuu = Client("shivu_session", api_id, api_hash, bot_token=TOKEN)

# NOTE: Modules yahan load NAHI honge. Wo __main__.py me honge.
