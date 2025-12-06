import logging
from telegram.ext import Application
from motor.motor_asyncio import AsyncIOMotorClient
from shivu.config import Config

# Logging Setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
LOGGER = logging.getLogger(__name__)

# Config se Data lena
TOKEN = Config.TOKEN
mongo_url = Config.mongo_url
OWNER_ID = Config.OWNER_ID
sudo_users = Config.sudo_users
CHARA_CHANNEL_ID = Config.CHARA_CHANNEL_ID
SUPPORT_CHAT = Config.SUPPORT_CHAT
UPDATE_CHAT = Config.UPDATE_CHAT
BOT_USERNAME = Config.BOT_USERNAME
GROUP_ID = Config.GROUP_ID
PHOTO_URL = Config.PHOTO_URL

# Database Connect karna
client = AsyncIOMotorClient(mongo_url)
db = client['Character_catcher']
collection = db['anime_characters']
user_collection = db["user_collection_lmao"]
group_user_collection = db["group_user_collection"]
top_global_collection = db["top_global_collection"]
pm_users = db["total_pm_users"]

# Application Create karna
application = Application.builder().token(TOKEN).build()

# NOTE: Yahan se 'from shivu.modules import *' HATA DIYA GAYA HAI.
# Ab ye __main__.py mein hoga.
