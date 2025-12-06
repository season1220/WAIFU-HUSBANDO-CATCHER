import pymongo
import requests
from pymongo import ReturnDocument
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, sudo_users, collection, db, CHARA_CHANNEL_ID, SUPPORT_CHAT

# Aapka Naya Rarity Map (Fixed)
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
    if str(user_id) not in sudo_users:
        await update.message.reply_text("❌ You are not allowed to upload characters.")
        return

    try:
        args = context.args
        reply = update.message.reply_to_message

        # --- Check agar Photo, Video ya GIF hai ---
        if reply:
            if len(args) < 3:
                await update.message.reply_text("⚠️ Wrong format! Reply with:\n`/upload Character-Name Anime-Name Rarity-Number`")
                return
            
            character_name = args[0].replace('-', ' ').title()
            anime_name = args[1].replace('-', ' ').title()
            try:
                rarity_input = int(args[2])
            except ValueError:
                await update.message.reply_text("❌ Rarity must be a number (1-12).")
                return

            if rarity_input not in rarity_map:
                await update.message.reply_text(f"❌ Invalid Rarity! Use numbers 1 to 12.")
                return
            rarity = rarity_map[rarity_input]

            # 1. PHOTO
            if reply.photo:
                file_id = reply.photo[-1].file_id
                msg = await context.bot.send_photo(
                    chat_id=CHARA_CHANNEL_ID,
                    photo=file_id,
                    caption=f"<b>Character Name:</b> {character_name}\n<b>Anime Name:</b> {anime_name}\n<b>Rarity:</b> {rarity}",
                    parse_mode='HTML'
                )
            
            # 2. VIDEO (AMV)
            elif reply.video:
                file_id = reply.video.file_id
                msg = await context.bot.send_video(
                    chat_id=CHARA_CHANNEL_ID,
                    video=file_id,
                    caption=f"<b>Character Name:</b> {character_name}\n<b>Anime Name:</b> {anime_name}\n<b>Rarity:</b> {rarity}",
                    parse_mode='HTML'
                )

            # 3. ANIMATION (GIF)
            elif reply.animation:
                file_id = reply.animation.file_id
                msg = await context.bot.send_animation(
                    chat_id=CHARA_CHANNEL_ID,
                    animation=file_id,
                    caption=f"<b>Character Name:</b> {character_name}\n<b>Anime Name:</b> {anime_name}\n<b>Rarity:</b> {rarity}",
                    parse_mode='HTML'
                )
            
            else:
                await update.message.reply_text("❌ Please reply to a Photo, Video (AMV), or GIF.")
                return
            
            final_file_id = file_id 

        # --- Agar Link diya hai ---
        else:
            if len(args) < 4:
                await update.message.reply_text("⚠️ Wrong format! Use:\n`/upload Img_url Character-Name Anime-Name Rarity-Number`")
                return
            
            img_url = args[0]
            character_name = args[1].replace('-', ' ').title()
            anime_name = args[2].replace('-', ' ').title()
            try:
                rarity_input = int(args[3])
            except ValueError:
                await update.message.reply_text("❌ Rarity must be a number (1-12).")
                return

            if rarity_input not in rarity_map:
                await update.message.reply_text(f"❌ Invalid Rarity! Use numbers 1 to 12.")
                return
            rarity = rarity_map[rarity_input]

            try:
                msg = await context.bot.send_photo(
                    chat_id=CHARA_CHANNEL_ID,
                    photo=img_url,
                    caption=f"<b>Character Name:</b> {character_name}\n<b>Anime Name:</b> {anime_name}\n<b>Rarity:</b> {rarity}",
                    parse_mode='HTML'
                )
                final_file_id = msg.photo[-1].file_id
            except:
                await update.message.reply_text("❌ Link Error. Check URL or Bot Admin perms.")
                return

        # Save to Database
        id = str(await get_next_sequence_number('character_id')).zfill(2)

        character = {
            'img_url': final_file_id,
            'name': character_name,
            'anime': anime_name,
            'rarity': rarity,
            'id': id
        }

        await collection.insert_one(character)
        await update.message.reply_text(f"✅ <b>Uploaded Successfully!</b>\n\n🆔 ID: {id}\n👤 Name: {character_name}\n🎬 Anime: {anime_name}\n💎 Rarity: {rarity}", parse_mode='HTML')

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

UPLOAD_HANDLER = CommandHandler('upload', upload, block=False)
application.add_handler(UPLOAD_HANDLER)
