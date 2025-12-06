class Config(object):
    LOGGER = True


    OWNER_ID = "7164618867"
    sudo_users = "7164618867"

    TOKEN = "8578752843:AAHNWJAKLmZ_pc9tHPgyhUtnjOKxtXD6mM8"
    

    mongo_url = "mongodb+srv://seasonking:admin123@cluster0.e5zbzap.mongodb.net/?appName=Cluster0"

    CHARA_CHANNEL_ID = "-1003337112485"
    GROUP_ID = -1003337112485
    
    
    BOT_USERNAME = "seasonwaifuBot"

    api_id = 34967775
    api_hash = "e6e5dfae5327f90410863f93d8ced26b"

 
    PHOTO_URL = ["https://telegra.ph/file/b925c3985f0f325e62e17.jpg", "https://telegra.ph/file/4211fb191383d895dab9d.jpg"]
    SUPPORT_CHAT = "seasonwaifuBot"
    UPDATE_CHAT = "seasonwaifuBot"

class Production(Config):
    LOGGER = True

class Development(Config):
    LOGGER = True
