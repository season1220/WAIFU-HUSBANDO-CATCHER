import logging
import os
from telegram.ext import Application
from motor.motor_asyncio import AsyncIOMotorClient
from shivu.config import Config

# 1. Logging Setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
LOGGER = logging.getLogger(__name__)

# 2. Config se Data lena
TOKEN = Config.TOKEN
api_id = Config.api_id
api_hash = Config.api_hash
mongo_url = Config.mongo_url
OWNER_ID = Config.OWNER_ID
sudo_users = Config.sudo_users
CHARA_CHANNEL_ID = Config.CHARA_CHANNEL_ID
SUPPORT_CHAT = Config.SUPPORT_CHAT
UPDATE_CHAT = Config.UPDATE_CHAT
BOT_USERNAME = Config.BOT_USERNAME
GROUP_ID = Config.GROUP_ID
PHOTO_URL = Config.PHOTO_URL

# 3. Application Create karna (Ye sabse pehle hona chahiye)
application = Application.builder().token(TOKEN).build()

# 4. Database Connect karna
client = AsyncIOMotorClient(mongo_url)
db = client['Character_catcher']
collection = db['anime_characters']
user_collection = db["user_collection_lmao"]
group_user_collection = db["group_user_collection"]
top_global_collection = db["top_global_collection"]
pm_users = db["total_pm_users"]

# 5. Modules Load karna (Ye SABSE END mein hona chahiye)
# Agar ye upar chala gaya toh Circular Import Error aata hai
from shivu.modules import *
