import pymongo
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from pymongo import ReturnDocument
from shivu import application, collection, db

# --- SETTINGS ---
CHARA_CHANNEL_ID = -1003352372209 
OWNER_ID = 7164618867
sudo_collection = db["sudo_users_list"]
# ----------------

rarity_map = {
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

async def get_next_sequence_number(sequence_name):
    sequence_collection = db.sequences
    sequence_document = await sequence_collection.find_one_and_update(
        {'_id': sequence_name}, 
        {'$inc': {'sequence_value': 1}}, 
        return_document=ReturnDocument.AFTER
    )
    if not sequence_document:
        await sequence_collection.insert_one({'_id': sequence_name, 'sequence_value': 0})
        return 0
    return sequence_document['sequence_value']

async def upload(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    
    # --- NEW PERMISSION CHECK (Database + Owner) ---
    is_sudo = await sudo_collection.find_one({'user_id': user_id})
    
    if user_id != OWNER_ID and not is_sudo:
        await update.message.reply_text("❌ Aapke paas Upload karne ki power nahi hai.\nOwner se sampark karein.")
        return
    # -----------------------------------------------

    try:
        args = context.args
        reply = update.message.reply_to_message

        if reply:
            if len(args) < 3:
                await update.message.reply_text("⚠️ Reply Format: `/upload Name Anime Rarity(1-12)`", parse_mode='Markdown')
                return
            
            character_name = args[0].replace('-', ' ').title()
            anime_name = args[1].replace('-', ' ').title()
            try:
                rarity_input = int(args[2])
                if rarity_input not in rarity_map:
                    await update.message.reply_text("❌ Invalid Rarity! Use 1-12.")
                    return
                rarity = rarity_map[rarity_input]
            except ValueError:
                await update.message.reply_text("❌ Rarity number honi chahiye.")
                return

            if reply.photo:
                file_id = reply.photo[-1].file_id
                msg = await context.bot.send_photo(chat_id=CHARA_CHANNEL_ID, photo=file_id, caption=f"<b>Name:</b> {character_name}\n<b>Anime:</b> {anime_name}\n<b>Rarity:</b> {rarity}", parse_mode='HTML')
            elif reply.video:
                file_id = reply.video.file_id
                msg = await context.bot.send_video(chat_id=CHARA_CHANNEL_ID, video=file_id, caption=f"<b>Name:</b> {character_name}\n<b>Anime:</b> {anime_name}\n<b>Rarity:</b> {rarity}", parse_mode='HTML')
            elif reply.animation:
                file_id = reply.animation.file_id
                msg = await context.bot.send_animation(chat_id=CHARA_CHANNEL_ID, animation=file_id, caption=f"<b>Name:</b> {character_name}\n<b>Anime:</b> {anime_name}\n<b>Rarity:</b> {rarity}", parse_mode='HTML')
            else:
                await update.message.reply_text("❌ Photo/Video par reply karein.")
                return
            
            final_file_id = file_id 

        else:
            if len(args) < 4:
                await update.message.reply_text("⚠️ URL Format: `/upload URL Name Anime Rarity`")
                return
            img_url = args[0]
            character_name = args[1].replace('-', ' ').title()
            anime_name = args[2].replace('-', ' ').title()
            try:
                rarity_input = int(args[3])
                rarity = rarity_map[rarity_input]
                msg = await context.bot.send_photo(chat_id=CHARA_CHANNEL_ID, photo=img_url, caption=f"<b>Name:</b> {character_name}\n<b>Anime:</b> {anime_name}\n<b>Rarity:</b> {rarity}", parse_mode='HTML')
                final_file_id = msg.photo[-1].file_id
            except:
                await update.message.reply_text("❌ Link Error.")
                return

        id = str(await get_next_sequence_number('character_id')).zfill(2)
        character = {'img_url': final_file_id, 'name': character_name, 'anime': anime_name, 'rarity': rarity, 'id': id}
        await collection.insert_one(character)
        await update.message.reply_text(f"✅ **Uploaded!** ID: `{id}`", parse_mode='Markdown')

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

UPLOAD_HANDLER = CommandHandler('upload', upload, block=False)
application.add_handler(UPLOAD_HANDLER)
