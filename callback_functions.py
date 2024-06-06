from aiogram.types import CallbackQuery
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram import Bot
from os import getenv
try:
    from secret_key import BOT_TOKEN
except:
    BOT_TOKEN = getenv('BOT_TOKEN')


bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# FNs which process callbacks
async def process_post_reaction(tg_channel_id, callback_query: CallbackQuery):
    # Acknowledge the callback query to stop the "loading" state
    await callback_query.answer(cache_time=12)

    # Edit the original message to remove the inline keyboard
    await callback_query.message.edit_reply_markup(reply_markup=None)

    action = callback_query.data
    user_name = callback_query.from_user.full_name
    if action == 'approve':
        response_text = f"{user_name} approved the post."
        # Send the post from admin group to telegram channel
        if callback_query.message.photo:
            await bot.send_photo(
                tg_channel_id,
                photo=callback_query.message.photo[-1].file_id,  # Send the highest resolution photo
                caption=callback_query.message.caption
            )
        else:
            await bot.send_message(
                tg_channel_id,
                text=callback_query.message.text
            )
    elif action == 'disapprove':
        response_text = f"{user_name} disapproved the post."
    
    # Reply to the user to confirm the action
    await callback_query.message.reply(response_text)


async def process_lang(callback_query: CallbackQuery):
    # Acknowledge the callback query to stop the "loading" state
    await callback_query.answer(cache_time=12)

    # Set the default language for user in DB
    chosen_lang = callback_query.data
    user_id = callback_query.from_user.id # Use it for setting default language for user

    if chosen_lang=='ru':
        response_text = "Выбраный язык: Русский"
    elif chosen_lang=='en': 
        response_text = "Chosen language: English"

    # Logic which interacts with DB....
    #...

    # Reply to the user to confirm the action
    await callback_query.message.reply(response_text)