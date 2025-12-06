class Config(object):
    LOGGER = True

    # Owner aur Sudo
    OWNER_ID = "7164618867"
    sudo_users = "7164618867"

    # Aapka Bot Token
    TOKEN = "8578752843:AAHNWJAKLmZ_pc9tHPgyhUtnjOKxtXD6mM8"
    
    # Aapka Database Link (Ab ye bilkul sahi hai)
    mongo_url = "mongodb+srv://seasonking:season_123@cluster0.e5zbzap.mongodb.net/?appName=Cluster0"

    # Channel IDs
    CHARA_CHANNEL_ID = "-1003337112485"
    GROUP_ID = -1003337112485
    
    # Bot Username
    BOT_USERNAME = "seasonwaifuBot"

    # API Details
    api_id = 34967775
    api_hash = "e6e5dfae5327f90410863f93d8ced26b"

    # Extra Settings
    PHOTO_URL = ["https://telegra.ph/file/b925c3985f0f325e62e17.jpg", "https://telegra.ph/file/4211fb191383d895dab9d.jpg"]
    SUPPORT_CHAT = "seasonwaifuBot"
    UPDATE_CHAT = "seasonwaifuBot"

class Production(Config):
    LOGGER = True

class Development(Config):
    LOGGER = True
