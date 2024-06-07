from aiogram.types import CallbackQuery
from os import getenv
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from DB_functions import *
from bot_settings import bot,dp


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


# Sequential data gathering for /new_channels 
# Define states
class new_channels_FORM(StatesGroup):
    new_YT_channels = State()


async def process_new_channels(callback_query: CallbackQuery, state: FSMContext):
    # Acknowledge the callback query to stop the "loading" state
    await callback_query.answer(cache_time=12)
    
    chosen_tg_channel_id, chosen_tg_channel_name  = callback_query.data.replace('new_channels_to_','').split('_AKA_')
    # Save the chosen Telegram channel info in the state
    await state.update_data(chosen_tg_channel_name=chosen_tg_channel_name)
    await state.update_data(chosen_tg_channel_id=chosen_tg_channel_id)
    
    await state.set_state(new_channels_FORM.new_YT_channels)

    # Edit the message to remove the inline keyboard
    await callback_query.message.edit_reply_markup(reply_markup=None)

    await callback_query.message.reply(f'Linking tracking of new YouTube channels to "{chosen_tg_channel_name}"\nEnter the channels without @ separated by commas (no need for commas for 1 channel)\nFor example: ImanGadzhi,childishgambino')
    
    
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