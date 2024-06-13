import asyncio
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from DB_functions import *
from fsm_states import *
from bot_settings import bot,dp
from VideoToPost import VideoToPost
from translations import translate


# FNs which process callbacks
async def process_post_reaction(callback_query: CallbackQuery): # Process post reaction and send to target TG_channel
    # Acknowledge the callback query to stop the "loading" state
    await callback_query.answer(cache_time=12)

    # Edit the original message to remove the inline keyboard
    await callback_query.message.edit_reply_markup(reply_markup=None)

    action = callback_query.data.replace('post_','')
    user_name = callback_query.from_user.full_name
    if 'to' in action:
        response_text = "{user_name} approved the post."
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
        response_text = "{user_name} disapproved the post."
    
    # Reply to the user to confirm the action
    user_lang = get_user_lang(callback_query.from_user.id)
    if user_lang!='en':
        response_text = translate(response_text, user_lang)
    response_text = response_text.format(user_name=user_name)
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
    user_lang = get_user_lang(callback_query.from_user.id)
    if user_lang!='en':
        response_text = translate(response_text, user_lang)
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

    response_text = "Linking tracking of new YouTube channels to '{chosen_tg_channel_name}'"
    user_lang = get_user_lang(callback_query.from_user.id)
    if user_lang!='en':
        response_text = translate(response_text, user_lang)
    response_text = response_text.format(chosen_tg_channel_name=chosen_tg_channel_name)
    await callback_query.message.reply(response_text)
    await state.set_state(new_channels_FORM.new_YT_channels)
    response_text = "Enter the channels without @ separated by commas (no need for commas for 1 channel)\nFor example: ImanGadzhi,childishgambino"
    user_lang = get_user_lang(callback_query.from_user.id)
    if user_lang!='en':
        response_text = translate(response_text, user_lang)
    await callback_query.message.reply(response_text)
    
# State handler for new_YT_channels
@dp.message(new_channels_FORM.new_YT_channels)
async def process_name(message: Message, state: FSMContext):
    try:
        new_YT_channels = message.text.split(',')
    except:
        response_text = "Separate channels by comma! Try /new_channels again."
        user_lang = get_user_lang(message.from_user.id)
        if user_lang!='en':
            response_text = translate(response_text, user_lang)
        print(response_text)

    data = await state.get_data()
    chosen_tg_channel_name = data["chosen_tg_channel_name"]
    response = link_new_YT_channels(data['chosen_tg_channel_id'], new_YT_channels)
    if response:
        response_text = "The YT channels {new_YT_channels} have been linked to {chosen_tg_channel_name}!" 
    else:
        response_text = "The YT channels {new_YT_channels} have NOT been linked to {chosen_tg_channel_name}!"
    
    user_lang = get_user_lang(message.from_user.id)
    if user_lang!='en':
        response_text = translate(response_text, user_lang)
    response_text = response_text.format(new_YT_channels=new_YT_channels, chosen_tg_channel_name=chosen_tg_channel_name)
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

    response_text = "Linking the new config to {tg_channel_name}"
    user_lang = get_user_lang(callback.from_user.id)
    if user_lang!='en':
        response_text = translate(response_text, user_lang)
    response_text = response_text.format(tg_channel_name=tg_channel_name)
    await callback.message.reply(response_text)

    # Define keyboard for name choices
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text='Русский 🇷🇺', callback_data=f'config_lang_ru')],
                    [InlineKeyboardButton(text='English 🇺🇸', callback_data=f'config_lang_en')]])
    
    await state.update_data(tg_channel_id=tg_channel_id)
    await state.update_data(tg_channel_name=tg_channel_name)
    await state.set_state(post_config_FORM.lang)
    response_text = "Choose the language of posts"
    user_lang = get_user_lang(callback.from_user.id)
    if user_lang!='en':
        response_text = translate(response_text, user_lang)
    await callback.message.reply(response_text, reply_markup=keyboard)


@dp.message(post_config_FORM.lang)
async def choose_reference(callback:CallbackQuery, state:FSMContext):
    # Acknowledge the callback query to stop the "loading" state
    await callback.answer(cache_time=12)

    # Edit the message to remove the inline keyboard
    await callback.message.edit_reply_markup(reply_markup=None)

    # Get the data from callback
    config_lang = callback.data.replace('config_lang_','')

    user_lang = get_user_lang(callback.from_user.id)
    if user_lang=='en':
        yes_text = 'Yes'
        no_text = 'No'
    elif user_lang=='ru':
        yes_text = 'Да'
        no_text = 'Нет'

    # Define keyboard for name choices
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=yes_text, callback_data=f'config_reference_yes')],
                    [InlineKeyboardButton(text=no_text, callback_data=f'config_reference_no')]])

    await state.update_data(config_lang=config_lang)
    await state.set_state(post_config_FORM.reference)
    response_text = "Choose whether to reference the YT author"
    if user_lang!='en':
        response_text = translate(response_text, user_lang)
    await callback.message.reply(response_text, reply_markup=keyboard)


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
    
    user_lang = get_user_lang(callback.from_user.id)
    if user_lang=='en':
        yes_text = 'Yes'
        no_text = 'No'
    elif user_lang=='ru':
        yes_text = 'Да'
        no_text = 'Нет'

    # Define keyboard for name choices
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=yes_text, callback_data=f'config_img_yes')],
                    [InlineKeyboardButton(text=no_text, callback_data=f'config_img_no')]])

    await state.update_data(config_reference=config_reference)
    await state.set_state(post_config_FORM.img)
    response_text = "Include the YT banner?\nP.s. It will serve as the post's image"
    if user_lang!='en':
        response_text = translate(response_text, user_lang)
    await callback.message.reply(response_text, reply_markup=keyboard)


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

    user_lang = get_user_lang(callback.from_user.id)
    if user_lang!='en':
        response_text = translate(response_text, user_lang)
    await callback.message.reply(response_text)


@dp.message(video_to_post_FORM.tg_channel_id)
async def process_manual_VTP(callback:CallbackQuery, state:FSMContext, yt_api=False):
    # Acknowledge the callback query to stop the "loading" state
    await callback.answer(cache_time=12)

    TG_channel_id = callback.data.replace('vtp_','')

    # Edit the message to remove the inline keyboard
    await callback.message.edit_reply_markup(reply_markup=None)

    data = await state.get_data()
    yt_link = data['yt_link']
    admin_group_id = data['admin_group_id']
    await state.clear()

    config_lang, config_reference, config_img = get_post_config(TG_channel_id)
    try:
        post_name, post_dict = VideoToPost(yt_link, post_lang=config_lang, reference=config_reference, post_img=config_img) 
    except ValueError as e:
        raise ValueError(e)
    except Exception as e:
        response_text = "ERROR: video url did not pass VideoToPost '{yt_link}'. Details - {e}"
        user_lang = get_user_lang(callback.from_user.id)
        if user_lang!='en':
            response_text = translate(response_text, user_lang)
        response_text = response_text.format(yt_link=yt_link, e=e)
        await bot.send_message(admin_group_id, response_text)
        return False
    
    user_lang = get_user_lang(callback.from_user.id)
    if user_lang=='en':
        approve_button_text = 'Approve'
        disapprove_button_text = 'Disapprove'
    elif user_lang=='ru':
        approve_button_text = 'Принять'
        disapprove_button_text = 'Отклонить'
    
    # Create inline keyboard with approve and disapprove buttons
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=approve_button_text, callback_data=f'post_approve_to_{TG_channel_id}')],
        [InlineKeyboardButton(text=disapprove_button_text, callback_data=f'post_disapprove')]])

    if 'post_img' in post_dict.keys():
        # Send image with a caption
        await bot.send_photo(
                admin_group_id, 
                BufferedInputFile(post_dict['post_img'], filename=f"{post_name}.jpeg"),
                caption=post_dict['post_txt'], reply_markup=keyboard)
    else:
        await bot.send_message(admin_group_id, post_dict['post_txt'], reply_markup=keyboard)


async def process_auto_VPT(callback:CallbackQuery):
    # Acknowledge the callback query to stop the "loading" state
    await callback.answer(cache_time=12)

    # Edit the message to remove the inline keyboard
    await callback.message.edit_reply_markup(reply_markup=None)

    # Extract the callback data
    _, action, timestamp_str = callback.data.split('_')

    try:
        if action == 'approve':
            # Get the pending work details
            timestamp_str, video_url, post_cost, admin_group_id, tg_channel_id = get_pendind_work_details(timestamp_str)

            user_id = callback.from_user.id
            user_balance = get_user_balance(user_id)
            if post_cost>user_balance:
                response_text = "[ERROR] - You don't have enough tokens! Your balance is {user_balance}"
                user_lang = get_user_lang(user_id)
                if user_lang!='en':
                    response_text = translate(response_text, user_lang)
                response_text = response_text.format(user_balance=user_balance)
                await bot.send_message(admin_group_id, response_text)
                return False

            config_lang, config_reference, config_img = get_post_config(tg_channel_id)

            try:
                post_name, post_dict = VideoToPost(video_url, post_lang=config_lang, reference=config_reference, post_img=config_img) 
            except ValueError as e:
                raise ValueError(e)
            except:
                response_text = '[ERROR]: video url did not pass VideoToPost \n"{video_url}"'
                user_lang = get_user_lang(await get_chat_owner_id(admin_group_id))
                if user_lang!='en':
                    response_text = translate(response_text, user_lang)
                response_text = response_text.format(video_url=video_url)
                await bot.send_message(admin_group_id,response_text)
                return False

            user_lang = get_user_lang(await get_chat_owner_id(admin_group_id))
            if user_lang=='en':
                approve_button_text = 'Approve'
                disapprove_button_text = 'Disapprove'
            elif user_lang=='ru':
                approve_button_text = 'Принять'
                disapprove_button_text = 'Отклонить'
            # Create inline keyboard with approve and disapprove buttons
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=approve_button_text, callback_data=f'post_approve_to_{tg_channel_id}')],
                [InlineKeyboardButton(text=disapprove_button_text, callback_data=f'post_disapprove')]])

            if 'post_img' in post_dict.keys():
                # Send image with a caption
                await bot.send_photo(
                        admin_group_id, 
                        BufferedInputFile(post_dict['post_img'], filename=f"{post_name}.jpeg"),
                        caption=post_dict['post_txt'], reply_markup=keyboard)

            else:
                await bot.send_message(admin_group_id, post_dict['post_txt'], reply_markup=keyboard)
            
            # Interaction with DB
            add_new_transaction(user_id, sum=post_cost)
            create_or_update_user(user_id, balance=user_balance-post_cost)

            await asyncio.sleep(13) # EdenAI request limit ("start" - billing plan)
    finally:
        delete_pending_work(timestamp_str)
        