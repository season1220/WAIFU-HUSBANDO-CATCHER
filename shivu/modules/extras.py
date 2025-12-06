from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, collection
import random

# --- CHECK COMMAND (Character Info) ---
async def check(update: Update, context: CallbackContext) -> None:
    if not context.args:
        await update.message.reply_text("⚠️ **Format:** `/check [Character_ID]`", parse_mode='Markdown')
        return

    char_id = context.args[0]
    character = await collection.find_one({'id': char_id})

    if not character:
        await update.message.reply_text("❌ Character nahi mila. ID check karein.")
        return

    caption = f"""
🕵️ **CHARACTER DETAILS**

🆔 **ID:** `{character['id']}`
📛 **Name:** {character['name']}
🌈 **Anime:** {character['anime']}
✨ **Rarity:** {character['rarity']}
"""
    await update.message.reply_photo(photo=character['img_url'], caption=caption, parse_mode='Markdown')

# --- RARITY COMMAND (List) ---
async def rarity(update: Update, context: CallbackContext) -> None:
    msg = """
<b>💎 RARITY LIST & VALUE</b>

1. 🥉 <b>Low</b>
2. 🥈 <b>Medium</b>
3. 🥇 <b>High</b>
4. 🔮 <b>Special Edition</b>
5. 💠 <b>Elite Edition</b>
6. 🦄 <b>Legendary</b>
7. 💌 <b>Valentine</b>
8. 🧛🏻 <b>Halloween</b>
9. 🥶 <b>Winter</b>
10. 🍹 <b>Summer</b>
11. ⚜️ <b>Royal</b>
12. 💍 <b>Luxury Edition</b>
"""
    await update.message.reply_text(msg, parse_mode='HTML')

# --- SIPS COMMAND (Fun) ---
async def sips(update: Update, context: CallbackContext) -> None:
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Kisi ko reply karke sip karein!")
        return
    
    sender = update.effective_user.first_name
    receiver = update.message.reply_to_message.from_user.first_name
    
    gifs = [
        "https://media.giphy.com/media/3o6ozvv0zsJskzOCbu/giphy.gif",
        "https://media.giphy.com/media/13CoXDiaCcCzrW/giphy.gif",
        "https://media.giphy.com/media/l0HlHJGHe3yAMhdQY/giphy.gif"
    ]
    
    await update.message.reply_animation(
        animation=random.choice(gifs),
        caption=f"🍵 **{sender}** sips tea with **{receiver}**... interesting!",
        parse_mode='Markdown'
    )

application.add_handler(CommandHandler("check", check))
application.add_handler(CommandHandler("rarity", rarity))
application.add_handler(CommandHandler("sips", sips))
