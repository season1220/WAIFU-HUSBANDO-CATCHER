import random
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, user_collection, collection

# Roll ki keemat (Price)
ROLL_PRICE = 500 

async def roll(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    user = await user_collection.find_one({'id': user_id})
    
    current_bal = user.get('balance', 0) if user else 0
    
    if current_bal < ROLL_PRICE:
        await update.message.reply_text(f"❌ **Not enough money!**\nRoll ke liye {ROLL_PRICE} coins chahiye.\nAapke paas {current_bal} hain.")
        return

    # Paise Kato
    await user_collection.update_one({'id': user_id}, {'$inc': {'balance': -ROLL_PRICE}})

    # Character Do
    all_chars = list(await collection.find({}).to_list(length=None))
    if not all_chars:
        await update.message.reply_text("Database khali hai!")
        return

    character = random.choice(all_chars)
    
    # User ke harem me add karein
    await user_collection.update_one({'id': user_id}, {'$push': {'characters': character}})

    await update.message.reply_photo(
        photo=character['img_url'],
        caption=f"🎲 **You Rolled!**\n\n📛 **{character['name']}**\n✨ **{character['rarity']}**\n\n💰 {ROLL_PRICE} coins deducted."
    )

application.add_handler(CommandHandler(["roll", "gacha"], roll))
