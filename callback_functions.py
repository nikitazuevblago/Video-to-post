from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from DB_functions import *
from bot_settings import bot,dp
from VideoToPost import VideoToPost


# FNs which process callbacks
async def process_post_reaction(callback_query: CallbackQuery): # Process post reaction and send to target TG_channel
    # Acknowledge the callback query to stop the "loading" state
    await callback_query.answer(cache_time=12)

    # Edit the original message to remove the inline keyboard
    await callback_query.message.edit_reply_markup(reply_markup=None)

    action = callback_query.data.replace('post_','')
    user_name = callback_query.from_user.full_name
    if 'to' in action:
        response_text = f"{user_name} approved the post."
        # Send the post from admin group to telegram channel
        tg_channel_id = action.split('_to_')[-1]
        if callback_query.message.photo:
            await bot.send_photo(
                tg_channel_id, # WARNING - change to target TG_channel
                photo=callback_query.message.photo[-1].file_id,  # Send the highest resolution photo
                caption=callback_query.message.caption
            )
        else:
            await bot.send_message(
                tg_channel_id, # WARNING - change to target TG_channel
                text=callback_query.message.text
            )
    elif action == 'disapprove':
        response_text = f"{user_name} disapproved the post."
    
    # Reply to the user to confirm the action
    await callback_query.message.reply(response_text)


async def process_lang(callback_query: CallbackQuery):
    # Acknowledge the callback query to stop the "loading" state
    await callback_query.answer(cache_time=12)

    # Edit the message to remove the inline keyboard
    await callback_query.message.edit_reply_markup(reply_markup=None)

    # Set the default language for user in DB
    chosen_lang = callback_query.data
    user_id = callback_query.from_user.id # Use it for setting default language for user

    if chosen_lang=='ru':
        response_text = "Выбраный язык: Русский"
    elif chosen_lang=='en': 
        response_text = "Chosen language: English"

    # Changes in DB
    create_or_update_user(user_id, lang=chosen_lang)

    # Reply to the user to confirm the action
    await callback_query.message.reply(response_text)


# Sequential data gathering for /new_channels 
# Define states
class new_channels_FORM(StatesGroup):
    new_YT_channels = State()


async def process_new_channels(callback_query: CallbackQuery, state: FSMContext):
    # Acknowledge the callback query to stop the "loading" state
    await callback_query.answer(cache_time=12)
    
    # Save the chosen Telegram channel info in the state
    chosen_tg_channel_id, chosen_tg_channel_name  = callback_query.data.replace('new_channels_to_','').split('_AKA_')
    await state.update_data(chosen_tg_channel_name=chosen_tg_channel_name)
    await state.update_data(chosen_tg_channel_id=chosen_tg_channel_id)

    # Edit the message to remove the inline keyboard
    await callback_query.message.edit_reply_markup(reply_markup=None)

    await callback_query.message.reply(f'Linking tracking of new YouTube channels to "{chosen_tg_channel_name}"')
    await state.set_state(new_channels_FORM.new_YT_channels)
    await callback_query.message.reply(f'Enter the channels without @ separated by commas (no need for commas for 1 channel)\nFor example: ImanGadzhi,childishgambino')
    
# State handler for new_YT_channels
@dp.message(new_channels_FORM.new_YT_channels)
async def process_name(message: Message, state: FSMContext):
    try:
        new_YT_channels = message.text.split(',')
    except:
        print('Separate channels by comma! Try /new_channels again.')

    data = await state.get_data()
    response = link_new_YT_channels(data['chosen_tg_channel_id'], new_YT_channels)
    if response:
        response_text = f'The YT channels {new_YT_channels} have been linked to {data['chosen_tg_channel_name']}!'
    else:
        response_text = f'The YT channels {new_YT_channels} have NOT been linked to {data['chosen_tg_channel_name']}!'
        
    await message.reply(response_text)

    # Finish conversation
    await state.clear()


async def process_config(callback:CallbackQuery):
    # Acknowledge the callback query to stop the "loading" state
    await callback.answer(cache_time=12)

    # Get the data from callback
    tg_channel_id, tg_channel_name = callback.data.replace('config_to_','').split('_AKA_')

    # Edit the message to remove the inline keyboard
    await callback.message.edit_reply_markup(reply_markup=None)

    
    callback.message.reply(f'Linking the new config to {tg_channel_name}')

    # Define keyboard for name choices
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text='Русский 🇷🇺', callback_data=f'config_lang_ru_{tg_channel_id}')],
                    [InlineKeyboardButton(text='English 🇺🇸', callback_data=f'config_lang_en_{tg_channel_id}')]])
    
    await callback.message.reply("Choose the language of posts", reply_markup=keyboard)


async def process_config_lang(callback:CallbackQuery):
    # Acknowledge the callback query to stop the "loading" state
    await callback.answer(cache_time=12)

    # Edit the message to remove the inline keyboard
    await callback.message.edit_reply_markup(reply_markup=None)

    # Get the data from callback
    config_lang, tg_channel_id = callback.data.replace('config_lang_','').split('_')

    # Define keyboard for name choices
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text='Yes', callback_data=f'full_config_{config_lang}_yes_{tg_channel_id}')],
                    [InlineKeyboardButton(text='No', callback_data=f'full_config_{config_lang}_no_{tg_channel_id}')]])

    await callback.message.reply("Choose whether to reference the YT author", reply_markup=keyboard)


async def process_full_config(callback:CallbackQuery):
    # Acknowledge the callback query to stop the "loading" state
    await callback.answer(cache_time=12)

    # Edit the message to remove the inline keyboard
    await callback.message.edit_reply_markup(reply_markup=None)

    # Get the data from callback
    config_lang, config_reference, tg_channel_id = callback.data.replace('full_config_','').split('_')

    # Interaction with DB
    response = create_or_update_config(tg_channel_id, lang=config_lang, reference=config_reference)

    if response:
        response_text = "Config has been changed!"
    else:
        response_text = "Config has NOT been changed!"

    await callback.message.reply(response_text)