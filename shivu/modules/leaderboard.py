from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, user_collection, top_global_groups_collection

async def ctop(update: Update, context: CallbackContext) -> None:
    # Top 10 Users nikalna
    cursor = user_collection.find({})
    users = []
    async for user in cursor:
        if 'characters' in user:
            users.append({'name': user.get('first_name', 'Unknown'), 'count': len(user['characters'])})
    
    # Sort by Count
    users = sorted(users, key=lambda x: x['count'], reverse=True)[:10]

    msg = "<b>🏆 TOP 10 WAIFU COLLECTORS</b>\n\n"
    for i, user in enumerate(users, 1):
        msg += f"{i}. <b>{user['name']}</b> ➾ {user['count']} Characters\n"
    
    await update.message.reply_text(msg, parse_mode='HTML')

async def gtop(update: Update, context: CallbackContext) -> None:
    # Top 10 Groups
    cursor = top_global_groups_collection.find({})
    groups = []
    async for group in cursor:
        groups.append({'title': group.get('group_name', 'Unknown'), 'count': group.get('count', 0)})
    
    groups = sorted(groups, key=lambda x: x['count'], reverse=True)[:10]

    msg = "<b>🏆 TOP 10 GROUPS</b>\n\n"
    for i, group in enumerate(groups, 1):
        msg += f"{i}. <b>{group['title']}</b> ➾ {group['count']} Spawns\n"

    await update.message.reply_text(msg, parse_mode='HTML')

application.add_handler(CommandHandler(["ctop", "top"], ctop))
application.add_handler(CommandHandler(["gtop", "grouptop"], gtop))
