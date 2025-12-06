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

# --- 2. CONFIG SETTINGS ---
TOKEN = "8578752843:AAFDF6aGAFJegXYrWGbFBbz2Cj_86I3zdF8"
mongo_url = "mongodb+srv://seasonking:season_123@cluster0.e5zbzap.mongodb.net/?appName=Cluster0"
OWNER_ID = 7164618867
sudo_users = [7164618867]
CHARA_CHANNEL_ID = -1003352372209
SUPPORT_CHAT = "seasonwaifuBot"
UPDATE_CHAT = "seasonwaifuBot"
BOT_USERNAME = "seasonwaifuBot"
GROUP_ID = -1003352372209
PHOTO_URL = ["https://telegra.ph/file/b925c3985f0f325e62e17.jpg", "https://telegra.ph/file/4211fb191383d895dab9d.jpg"]
api_id = 34967775
api_hash = "e6e5dfae5327f90410863f93d8ced26b"

# --- 3. DATABASE CONNECTION ---
client = AsyncIOMotorClient(mongo_url)
db = client['Character_catcher']

# Saari Collections (Ab kuch missing nahi hai)
collection = db['anime_characters']
user_collection = db["user_collection_lmao"]
group_user_totals_collection = db["group_user_totals_collection"]
top_global_groups_collection = db["top_global_groups_collection"]
user_totals_collection = db["user_totals_collection"]
pm_users = db["total_pm_users"]  # <--- Ye line missing thi, ab daal di hai

# --- 4. BOT CLIENTS ---
application = Application.builder().token(TOKEN).build()
shivuu = Client("shivu_session", api_id, api_hash, bot_token=TOKEN)
