import random
from html import escape 

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, ContextTypes

from shivu import application, PHOTO_URL, SUPPORT_CHAT, UPDATE_CHAT, BOT_USERNAME

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Video Link
    video_url = "https://telegra.ph/file/ca6f8e285d0d82d46e27a.mp4" 

    # Message Text (Updated Name)
    caption = f"""
🍃 𝗚𝗥𝗘𝗘𝗧𝗜𝗡𝗚𝗦, 𝗜'𝗠 𝗦𝗘𝗔𝗦𝗢𝗡 𝗪𝗔𝗜𝗙𝗨 🫧, 𝗡𝗜𝗖𝗘 𝗧𝗢 𝗠𝗘𝗘𝗧 𝗬𝗢𝗨!
━━━━━━━━━━━━━━━━━━━━━
◎ 𝗪𝗛𝗔𝗧 𝗜 𝗗𝗢: I SPAWN WAIFUS IN YOUR CHAT FOR 
  USERS TO GRAB.
◎ 𝗧𝗢 𝗨𝗦𝗘 𝗠𝗘: ADD ME TO YOUR GROUP AND TAP THE HELP 
  BUTTON FOR DETAILS.
━━━━━━━━━━━━━━━━━━━━━
➻ 𝗣𝗜𝗡𝗚: 0.7 ms
➻ 𝗢𝗪𝗡𝗘𝗥: <a href="https://t.me/DADY_JI">DADY JI</a>
"""
    
    keyboard = [
        [InlineKeyboardButton("ADD ME TO YOUR GROUP", url=f"http://t.me/{BOT_USERNAME}?startgroup=new")],

        [InlineKeyboardButton("OWNER", url=f"https://t.me/DADY_JI")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message.chat.type == "private":
        await context.bot.send_video(chat_id=update.effective_chat.id, video=video_url, caption=caption, parse_mode='HTML', reply_markup=reply_markup)
    else:
        await update.message.reply_video(video=video_url, caption="<b>I am alive! Check PM for more details.</b>", parse_mode='HTML', reply_markup=reply_markup)

application.add_handler(CommandHandler("start", start))
