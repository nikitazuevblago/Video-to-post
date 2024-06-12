from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from DB_functions import *
from fsm_states import *
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


@dp.message(post_config_FORM.tg_channel_id)
async def choose_lang(callback:CallbackQuery, state:FSMContext):
    # Acknowledge the callback query to stop the "loading" state
    await callback.answer(cache_time=12)

    # Edit the message to remove the inline keyboard
    await callback.message.edit_reply_markup(reply_markup=None)

    # Get data from callback
    tg_channel_id, tg_channel_name = callback.data.replace('config_to_','').split('_AKA_')

    await callback.message.reply(f'Linking the new config to {tg_channel_name}')

    # Define keyboard for name choices
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text='Русский 🇷🇺', callback_data=f'config_lang_ru')],
                    [InlineKeyboardButton(text='English 🇺🇸', callback_data=f'config_lang_en')]])
    
    await state.update_data(tg_channel_id=tg_channel_id)
    await state.update_data(tg_channel_name=tg_channel_name)
    await state.set_state(post_config_FORM.lang)
    await callback.message.reply("Choose the language of posts", reply_markup=keyboard)


@dp.message(post_config_FORM.lang)
async def choose_reference(callback:CallbackQuery, state:FSMContext):
    # Acknowledge the callback query to stop the "loading" state
    await callback.answer(cache_time=12)

    # Edit the message to remove the inline keyboard
    await callback.message.edit_reply_markup(reply_markup=None)

    # Get the data from callback
    config_lang = callback.data.replace('config_lang_','')

    # Define keyboard for name choices
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text='Yes', callback_data=f'config_reference_yes')],
                    [InlineKeyboardButton(text='No', callback_data=f'config_reference_no')]])

    await state.update_data(config_lang=config_lang)
    await state.set_state(post_config_FORM.reference)
    await callback.message.reply("Choose whether to reference the YT author", reply_markup=keyboard)


@dp.message(post_config_FORM.reference)
async def choose_img(callback:CallbackQuery, state:FSMContext):
    # Acknowledge the callback query to stop the "loading" state
    await callback.answer(cache_time=12)

    # Edit the message to remove the inline keyboard
    await callback.message.edit_reply_markup(reply_markup=None)

    # Get the data from callback
    config_reference = callback.data.replace('config_reference_','')
    if config_reference=='yes':
        config_reference = True
    elif config_reference=='no':
        config_reference = False
    else:
        raise ValueError(f'Config reference parameter "{config_reference}" is wrong!')

    # Define keyboard for name choices
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text='Yes', callback_data=f'config_img_yes')],
                    [InlineKeyboardButton(text='No', callback_data=f'config_img_no')]])

    await state.update_data(config_reference=config_reference)
    await state.set_state(post_config_FORM.img)
    await callback.message.reply("Include the YT banner?\nP.s. It will serve as the post's image", reply_markup=keyboard)


@dp.message(post_config_FORM.img)
async def process_full_config(callback:CallbackQuery, state:FSMContext):
    # Acknowledge the callback query to stop the "loading" state
    await callback.answer(cache_time=12)

    # Edit the message to remove the inline keyboard
    await callback.message.edit_reply_markup(reply_markup=None)

    # Get the data from callback
    config_img = callback.data.replace('config_img_','')
    if config_img=='yes':
        config_img = True
    elif config_img=='no':
        config_img = False
    else:
        raise ValueError(f'Config img parameter "{config_img}" is wrong!')
    
    await state.update_data(config_img=config_img)

    # Get data from FSM state
    data = await state.get_data()
    tg_channel_id = data['tg_channel_id']
    config_lang = data['config_lang']
    config_reference = data['config_reference']
    config_img = data['config_img']
    await state.clear()


    # Interaction with DB
    response = create_or_update_config(tg_channel_id, lang=config_lang, reference=config_reference, img=config_img)

    if response:
        response_text = "Config has been changed!"
    else:
        response_text = "Config has NOT been changed!"

    await callback.message.reply(response_text)


@dp.message(video_to_post_FORM.tg_channel_id)
async def process_manual_VTP(callback:CallbackQuery, state:FSMContext):
    TG_channel_id = callback.data.replace('vtp_','')

    # Edit the message to remove the inline keyboard
    await callback.message.edit_reply_markup(reply_markup=None)

    data = await state.get_data()
    yt_link = data['yt_link']
    admin_group_id = data['admin_group_id']
    await state.clear()

    config_lang, config_reference, config_img = get_post_config(TG_channel_id)
    try:
        post_name, post_dict = VideoToPost(yt_link, img=True, post_lang=config_lang, reference=config_reference, post_img=config_img) 
    except ValueError as e:
        raise ValueError(e)
    except Exception as e:
        await bot.send_message(admin_group_id, f'ERROR: video url did not pass VideoToPost "{yt_link}". Details - {e}')
        return False
    
    # Create inline keyboard with approve and disapprove buttons
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Approve', callback_data=f'post_approve_to_{TG_channel_id}')],
        [InlineKeyboardButton(text='Disapprove', callback_data=f'post_disapprove')]])

    if 'post_img' in post_dict.keys():
        # Send image with a caption
        await bot.send_photo(
                admin_group_id, 
                BufferedInputFile(post_dict['post_img'], filename=f"{post_name}.jpeg"),
                caption=post_dict['post_txt'], reply_markup=keyboard)
    else:
        await bot.send_message(admin_group_id, post_dict['post_txt'], reply_markup=keyboard)
        