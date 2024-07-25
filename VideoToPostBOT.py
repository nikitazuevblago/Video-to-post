import asyncio
import logging
import requests
import sys
import re
import time
from os import getenv

from aiogram.fsm.context import FSMContext
from aiogram import F
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton, Message, BotCommand, LabeledPrice, PreCheckoutQuery, ContentType
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums.parse_mode import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.enums.chat_member_status import ChatMemberStatus
import aiotube
from pytube import Channel
from VideoToPost import VideoToPost, get_post_cost
from DB_functions import *
from callback_functions import *
from fsm_states import *
from bot_settings import bot,dp
from translations import translate

try:
    from secret_key import YT_API_KEY, TEST_MODE, CREATOR_ID, TESTER_ID
    TEST_MODE = int(TEST_MODE)
    CREATOR_ID = int(CREATOR_ID)
    TESTER_ID = int(TESTER_ID)
except:
    YT_API_KEY = getenv('YT_API_KEY')
    TEST_MODE = int(getenv('TEST_MODE'))
    CREATOR_ID = int(getenv('CREATOR_ID'))
    TESTER_ID = int(getenv('TESTER_ID'))

if TEST_MODE==1:
    try:
        from secret_key import UKassa_TEST
    except:
        UKassa_TEST = getenv('UKassa_TEST')
    payment_provider_TOKEN = UKassa_TEST
else:
    try:
        from secret_key import UKassa
    except:
        UKassa = getenv('UKassa')
    payment_provider_TOKEN = UKassa


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    user_id = message.from_user.id
    create_or_update_user(user_id, default=True)    
    response_text = "Hello! I am a bot created for converting YouTube videos to Telegram posts!"
    user_lang = get_user_lang(message.from_user.id)
    if user_lang!='en':
        response_text = translate(response_text, user_lang)
    await message.answer(response_text)


@dp.message(Command('support'))
async def command_start_handler(message: Message) -> None:
    response_text = "Hello, I'm @blago7daren! Please contact me if something bad happens."
    user_lang = get_user_lang(message.from_user.id)
    if user_lang!='en':
        response_text = translate(response_text, user_lang)
    await message.answer(response_text)


# FN to convert "ISO 8601" format to seconds
def parse_duration(duration):
    pattern = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?')
    matches = pattern.match(duration)
    if not matches:
        return 0
    hours = int(matches.group(1) or 0)
    minutes = int(matches.group(2) or 0)
    seconds = int(matches.group(3) or 0)
    total_seconds = hours * 3600 + minutes * 60 + seconds
    return total_seconds


async def check_new_videos(tg_channel_id, admin_group_id, yt_channel_urls, tracked_yt_channels, yt_api=False, min_duration=60, max_duration=5000):
    new_latest_videos = set() # creator:video_url
    bad_creators = set()

    for i, channel_url  in enumerate(yt_channel_urls):
        yt_author = tracked_yt_channels[i]

        if yt_api:
            yt_channel_id = Channel(channel_url).channel_id
            url = f'https://www.googleapis.com/youtube/v3/search?key={YT_API_KEY}&channelId={yt_channel_id}&part=snippet,id&order=date&maxResults=5&type=video'#&videoDefinition=any'
            response = requests.get(url).json()
            try: # Some creator's videos can't be accessed, create a logger which notifies about such youtube creator
                latest_video = response['items'][0]
                video_id = latest_video['id']['videoId']
                video_details_url = f'https://www.googleapis.com/youtube/v3/videos?key={YT_API_KEY}&id={video_id}&part=contentDetails'
                video_details_response = requests.get(video_details_url).json()

                # Duration of the video in ISO 8601 format
                video_duration = video_details_response['items'][0]['contentDetails']['duration']

                # Convert it to seconds
                video_duration = parse_duration(video_duration)

                # Check if it's a shorts or regular youtube video
                if video_duration>min_duration and video_duration<max_duration:
                    new_video_url = f"https://www.youtube.com/watch?v={video_id}"
                    new_latest_videos.add(new_video_url)
                elif video_duration<min_duration:
                    response_text = "[INFO] The last video of {yt_author} was SHORTS(too short)"
                    user_lang = get_user_lang(await get_chat_owner_id(admin_group_id))
                    if user_lang!='en':
                        response_text = translate(response_text, user_lang)
                    response_text = response_text.format(yt_author=yt_author)
                    await bot.send_message(admin_group_id, response_text)
                else:
                    response_text = "[INFO] The last video of {yt_author} was PODCAST(too long)"
                    user_lang = get_user_lang(await get_chat_owner_id(admin_group_id))
                    if user_lang!='en':
                        response_text = translate(response_text, user_lang)
                    response_text = response_text.format(yt_author=yt_author)
                    await bot.send_message(admin_group_id, response_text)
                    
            except:
                response_text = "[INFO] Trouble with the creator {yt_author};\nRequests.get(url) response -> {response}"
                user_lang = get_user_lang(await get_chat_owner_id(admin_group_id))
                if user_lang!='en':
                    response_text = translate(response_text, user_lang)
                response_text = response_text.format(yt_author=yt_author, response=response)
                await bot.send_message(admin_group_id, response_text)
                bad_creators.add(yt_author)
        
        # Using aiotube library
        else:
            try:
                channel_url = yt_channel_urls[i].replace('/c/','@')
                at_index = channel_url.index('@')
                channel_with_at =  channel_url[at_index:]# smth like @Lololoshka
                video_id = aiotube.Channel(channel_with_at).last_uploaded()
                video_duration = int(aiotube.Video(video_id).metadata['duration'])
                # Check if it's a shorts or regular youtube video
                if video_duration>min_duration and video_duration<max_duration:
                    new_video_url = f"https://www.youtube.com/watch?v={video_id}"
                    new_latest_videos.add(new_video_url)
                elif video_duration<min_duration:
                    response_text = '[INFO] The last video of {yt_author} was SHORTS(too short)'
                    user_lang = get_user_lang(await get_chat_owner_id(admin_group_id))
                    if user_lang!='en':
                        response_text = translate(response_text, user_lang)
                    response_text = response_text.format(yt_author=yt_author)
                    await bot.send_message(admin_group_id, response_text)
                else:
                    response_text = '[INFO] The last video of {yt_author} was PODCAST(too long)'
                    user_lang = get_user_lang(await get_chat_owner_id(admin_group_id))
                    if user_lang!='en':
                        response_text = translate(response_text, user_lang)
                    response_text = response_text.format(yt_author=yt_author)
                    await bot.send_message(admin_group_id, response_text)
                    
            except Exception as e:
                response_text = '[INFO] Trouble with the creator {yt_author}; Exception: {e} (AIOTUBE)'
                user_lang = get_user_lang(await get_chat_owner_id(admin_group_id))
                if user_lang!='en':
                    response_text = translate(response_text, user_lang)
                response_text = response_text.format(yt_author=yt_author, e=e)
                await bot.send_message(admin_group_id, response_text)
                bad_creators.add(yt_author)

    used_video_urls = get_used_video_urls(tg_channel_id)
    new_latest_video_urls = new_latest_videos - used_video_urls
    return new_latest_video_urls, bad_creators


# Main logic   ## WARNING: manual_check - the user can choose whether to check the new videos of YouTube creators auto or manually
async def suggest_new_posts(delete_bad_creators=True, manual_check=False, test_sleep=9000, production_sleep=18000): # delete_bad_creators behaviour should be checked on the same yt_authors (maybe they're bad only sometimes)
    while True:
        all_projects = get_projects_details()
        if len(all_projects)>0:
            for tg_channel_id, admin_group_id in all_projects:
                tracked_yt_channels = get_tracked_channels(tg_channel_id)
                if len(tracked_yt_channels)>0:
                    yt_channel_urls = [f'https://www.youtube.com/c/{channel}' for channel in tracked_yt_channels]
                    print(f"\n{'-'*15}New check cycle{'-'*15}")
                    new_latest_video_urls, bad_creators = await check_new_videos(tg_channel_id, admin_group_id, yt_channel_urls, tracked_yt_channels) # channel:video_url
                    
                    if len(new_latest_video_urls)>0:
                        for video_url in new_latest_video_urls:
                            post_cost = get_post_cost(video_url)

                            user_lang = get_user_lang(await get_chat_owner_id(admin_group_id))
                            if user_lang=='en':
                                approve_button_text = 'Accept'
                                disapprove_button_text = 'Cancel'
                            elif user_lang=='ru':
                                approve_button_text = 'Принять'
                                disapprove_button_text = 'Отклонить'

                            current_timestamp_str = str(time.time())

                            # Create inline keyboard with Accept and Cancel buttons
                            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text=approve_button_text, callback_data=f'cost_approve_{current_timestamp_str}')],
                                [InlineKeyboardButton(text=disapprove_button_text, callback_data=f'cost_disapprove_{current_timestamp_str}')]])
                            
                            response_text = "[INFO] Converting this video {video_url} into a Telegram post will cost {post_cost} tokens. Do you agree?"
                            user_lang = get_user_lang(await get_chat_owner_id(admin_group_id))
                            if user_lang!='en':
                                response_text = translate(response_text, user_lang)
                            response_text = response_text.format(video_url=video_url, post_cost=post_cost)

                            new_pending_work(current_timestamp_str,video_url,post_cost,admin_group_id,tg_channel_id)
                            await bot.send_message(admin_group_id, response_text, reply_markup=keyboard)

                        insert_new_video_urls(new_latest_video_urls, tg_channel_id)

                    if delete_bad_creators:
                        if len(bad_creators)>0:
                            response_text = "\n{'*'*15}Removing creators from which we couldn't retreive the video{'*'*15}"
                            user_lang = get_user_lang(await get_chat_owner_id(admin_group_id))
                            if user_lang!='en':
                                response_text = translate(response_text, user_lang)
                            print(response_text)
                            remove_yt_creators(bad_creators)

                    if TEST_MODE==1:                
                        await asyncio.sleep(test_sleep)  
                    else:
                        await asyncio.sleep(production_sleep)
                else:
                    response_text = "[INFO] There are 0 tracked YouTube channels! Auto post suggesting doesn't work..."
                    user_lang = get_user_lang(await get_chat_owner_id(admin_group_id))
                    if user_lang!='en':
                        response_text = translate(response_text, user_lang)
                    await bot.send_message(admin_group_id, response_text)
                    if TEST_MODE==1:                
                        await asyncio.sleep(test_sleep)  
                    else:
                        await asyncio.sleep(production_sleep)
        else:
            response_text = "[INFO] There are 0 projects! Auto post sugessting doesn't work..."
            user_lang = get_user_lang(await get_chat_owner_id(admin_group_id))
            if user_lang!='en':
                response_text = translate(response_text, user_lang)
            await bot.send_message(CREATOR_ID, response_text)
            if TEST_MODE==1:                
                await asyncio.sleep(test_sleep)  
            else:
                await asyncio.sleep(production_sleep)


# List of bot commands in menu
async def set_help_menu():
    commands = [
        BotCommand(command="/set_language", description="Choose the language"),
        BotCommand(command="/help", description="Get instructions on how to use the bot"),
        BotCommand(command="/new_channels", description="Track new YouTube channels to get posts automatically"),
        BotCommand(command="/post_config", description="Post settings aimed on certain TG channel"),
        BotCommand(command="/top_up", description="Top up your balance"),
        BotCommand(command="/balance", description="Check balance"),
        BotCommand(command="/check_transactions", description="Get the table with your previous transactions"),
        BotCommand(command="/check_projects", description="Get linked to admin group TG channels"),
        BotCommand(command="/support", description="Contact the creator"),
        BotCommand(command="/create_project", description="Project is a combo of admin group and target TG channel)"),
        BotCommand(command="/get_group_id", description="Add bot to admin/destination tg channel and get id"),
        BotCommand(command="/video_to_post", description="Manually get the tg post from YT video")
    ]
    await bot.set_my_commands(commands)


@dp.message(Command('help'))
async def help(message:Message):
    response_text = "\n*Welcome to VideoToPostBOT\\!* 🤖\n\n*Intro*\nThis bot is created to automatically convert videos from YouTube to Telegram posts\nFirst, you need to create the project with /create\\_project\\. By itself the project it's a combination of the admin group and target telegram channel\\.\nSecond, you need to add the bot to admin group and telegram channel\\. Make the bot admin\\.\n\n• Admin group \\- telegram group with admins where they can accept or decline posts created by AI\\.\n• Target telegram channel \\- telegram channel with all accepted posts\\.\n• One admin group can have many linked telegram channels\\!\n\n\nHere are the commands you can use:\n\n*General Commands:*\n/set\\_language \\- Choose the language\\.\n/help \\- Get instructions on how to use the bot\\.\n\n*Channel Management:*\n/new\\_channels \\- Track new YouTube channels to get posts automatically\\.\n/post\\_config \\- Post settings aimed at a certain Telegram channel\\.\n/create\\_project \\- Project is a combo of admin group and target Telegram channel\\.\n/get\\_group\\_id \\- Add bot to the group to get its ID\\.\n/video\\_to\\_post \\- Manually get the Telegram post from a YouTube video\\.\n\n*Financial Commands:*\n/top\\_up \\- Top up your balance\\.\n/balance \\- Check your balance\\.\n/check\\_transactions \\- Get a table with your previous transactions\\.\n\n*Project and Group Management:*\n/check\\_projects \\- Get linked to admin group Telegram channels\\.\n\n*Support:*\n/support \\- Contact the creator\\.\n\nFor any further assistance, feel free to reach out to our support team\\. Enjoy using VideoToPostBOT\\! 😊\n"
    user_lang = get_user_lang(message.from_user.id)
    if user_lang!='en':
        response_text = translate(response_text, user_lang)

    await message.reply(response_text, parse_mode=ParseMode.MARKDOWN_V2)


@dp.message(Command('video_to_post'))
async def video_to_post(message:Message, state:FSMContext):
    try:
        message_parts = message.text.strip().split()
        assert len(message_parts)==2
        yt_link = message_parts[1]
    except:
        response_text = "Enter the command with link without nothing else!\nExample: /video_to_post https://youtu.be/eH_TOrddnZ0?si=pwpELPdAcO5XOzG5"
        user_lang = get_user_lang(message.from_user.id)
        if user_lang!='en':
            response_text = translate(response_text, user_lang)
        await message.reply(response_text)
        return False
    chat_id = message.chat.id
    if chat_id in get_admin_group_ids():
        chat_member = await bot.get_chat_member(chat_id=message.chat.id, user_id=message.from_user.id) 
        if chat_member.status in {ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR}:
            related_tg_channels_ids = get_related_tg_channels(chat_id)
            if len(related_tg_channels_ids)>0:
                builder = InlineKeyboardBuilder()
                for related_tg_channel_id in related_tg_channels_ids:
                    channel_info = await bot.get_chat(related_tg_channel_id)
                    channel_name = channel_info.title
                    builder.button(text=channel_name, callback_data=f'vtp_{related_tg_channel_id}')
                
                await state.update_data(admin_group_id=chat_id)
                await state.update_data(yt_link=yt_link)
                await state.set_state(video_to_post_FORM.tg_channel_id)
                response_text = 'Select the Telegram channel where you want to send the post'
                user_lang = get_user_lang(message.from_user.id)
                if user_lang!='en':
                    response_text = translate(response_text, user_lang)
                await message.reply(response_text, reply_markup=builder.as_markup())
            else:
                response_text = '[ERROR] First create the project with /create_project!'
                user_lang = get_user_lang(message.from_user.id)
                if user_lang!='en':
                    response_text = translate(response_text, user_lang)
                await bot.send_message(message.chat.id, response_text)
        else:
            response_text = '[ERROR] You are NOT the admin of this group!'
            user_lang = get_user_lang(message.from_user.id)
            if user_lang!='en':
                response_text = translate(response_text, user_lang)
            await bot.send_message(message.chat.id, )
    else:
        response_text = '[ERROR] This command executes only in admin group!'
        user_lang = get_user_lang(message.from_user.id)
        if user_lang!='en':
            response_text = translate(response_text, user_lang)
        await bot.send_message(message.chat.id, response_text)  


@dp.message(Command('post_config'))
async def post_config(message: Message, state:FSMContext):
    chat_id = message.chat.id
    if chat_id in get_admin_group_ids():
        chat_member = await bot.get_chat_member(chat_id=message.chat.id, user_id=message.from_user.id) 
        if chat_member.status in {ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR}:
            related_tg_channels_ids = get_related_tg_channels(admin_group_id=message.chat.id)
            builder = InlineKeyboardBuilder()
            for related_tg_channel_id in related_tg_channels_ids:
                channel_info = await bot.get_chat(related_tg_channel_id)
                channel_name = channel_info.title
                builder.button(text=channel_name, callback_data=f'config_to_{related_tg_channel_id}_AKA_{channel_name}')

            state.set_state(post_config_FORM.tg_channel_id)
            response_text = "Pick which channel's config to change"
            user_lang = get_user_lang(message.from_user.id)
            if user_lang!='en':
                response_text = translate(response_text, user_lang)
            await bot.send_message(message.chat.id, response_text, reply_markup=builder.as_markup())
        else:
            response_text = '[ERROR] You are NOT the admin of this group!'
            user_lang = get_user_lang(message.from_user.id)
            if user_lang!='en':
                response_text = translate(response_text, user_lang)
            await bot.send_message(message.chat.id, response_text)
    else:
        response_text = '[ERROR] This command executes only in admin group!'
        user_lang = get_user_lang(message.from_user.id)
        if user_lang!='en':
            response_text = translate(response_text, user_lang)
        await bot.send_message(message.chat.id, response_text)


@dp.message(Command('create_project'))
async def create_project(message: Message, state: FSMContext):
    await state.set_state(create_project_FORM.admin_group_id)
    response_text = "Admin group id\nP.s. Can be accessed with /get_group_id, using bot in created tg group ONLY FOR ADMINS"
    user_lang = get_user_lang(message.from_user.id)
    if user_lang!='en':
        response_text = translate(response_text, user_lang)
    await message.reply(response_text)


# State handler
@dp.message(create_project_FORM.admin_group_id)
async def process_admin_group(message: Message, state: FSMContext):
    await state.update_data(admin_group_id=message.text)
    await state.set_state(create_project_FORM.tg_channel_id)
    response_text = "TG channel id (posts destination)\nP.s. Can be accessed with /get_group_id, using bot in created tg channel for viewers"
    user_lang = get_user_lang(message.from_user.id)
    if user_lang!='en':
        response_text = translate(response_text, user_lang)
    await message.reply(response_text)


# State handler
@dp.message(create_project_FORM.tg_channel_id)
async def process_tg_channel(message: Message, state: FSMContext):
    await state.update_data(tg_channel_id=message.text)
    data = await state.get_data()

    # Changes in DB
    try:
        channel_info = await bot.get_chat(int(data['tg_channel_id']))
        channel_name = channel_info.title
        response = insert_new_project(channel_name, int(data['admin_group_id']), int(data['tg_channel_id']))
    except:
        response = False

    chat_id = message.chat.id
    if response:
        response_text = "[INFO] The project {channel_name} has been created!..."
        user_lang = get_user_lang(message.from_user.id)
        if user_lang!='en':
            response_text = translate(response_text, user_lang)
        response_text = response_text.format(channel_name=channel_name)
        create_or_update_config(data['tg_channel_id'], default=True)
    else:
        response_text = "The new project HASN'T been created!\nP.s. Frequent errors - 1. Project already exists (/check_projects) 2. Letters in 'Admin group id' or 'TG channel id'"
        user_lang = get_user_lang(message.from_user.id)
        if user_lang!='en':
            response_text = translate(response_text, user_lang)

    await bot.send_message(chat_id, response_text)

    # Finish conversation
    await state.clear()

    
@dp.message(Command('get_group_id'))
async def get_group_id(message: Message):
    if message.chat.type in ['group', 'supergroup']:
        chat_id = message.chat.id
        response_text = "ID of this group: {chat_id}"
        user_lang = get_user_lang(message.from_user.id)
        if user_lang!='en':
            response_text = translate(response_text, user_lang)
        response_text = response_text.format(chat_id=chat_id)
    else:
        response_text = "This command can only be used in a group or supergroup."
        user_lang = get_user_lang(message.from_user.id)
        if user_lang!='en':
            response_text = translate(response_text, user_lang)

    await message.reply(response_text)


@dp.message(Command('balance'))
async def get_balance(message: Message):
    user_id = message.from_user.id
    create_or_update_user(user_id, default=True)
    balance = get_user_balance(user_id)
    response_text = "You have {balance} tokens"
    user_lang = get_user_lang(message.from_user.id)
    if user_lang!='en':
        response_text = translate(response_text, user_lang)
    response_text = response_text.format(balance=balance)
    await message.reply(response_text)


@dp.message(Command('top_up'))
async def top_up_balance(message: Message):
    user_id = message.from_user.id
    create_or_update_user(user_id, default=True)

    try:
        message_parts = message.text.strip().split()
        assert len(message_parts)==2
        amount = int(message_parts[1])
        assert amount>=100 and amount<=1000
    except:
        response_text = "Enter the amount of tokens after /top_up, no letters, no spaces! Range of allowed sum from 100 to 1000 rub\nExample: /top_up 100"
        user_lang = get_user_lang(message.from_user.id)
        if user_lang!='en':
            response_text = translate(response_text, user_lang)
        await message.reply(response_text)
        return False
    
    # Real payment request
    response_text = "Top up the balance"
    user_lang = get_user_lang(message.from_user.id)
    if user_lang!='en':
        response_text = translate(response_text, user_lang)
    
    label_text = "{amount} tokens"
    if user_lang!='en':
        label_text = translate(label_text, user_lang)
    label_text = label_text.format(amount=amount)

    if user_lang=='en':
        cancel_button = 'cancel'
        pay_button = 'top up'
    elif user_lang=='ru':
        cancel_button = 'отмена'
        pay_button = 'оплатить'

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=pay_button, pay=True)],
                [InlineKeyboardButton(text=cancel_button, callback_data=f'cancel')]]
                )
    
    invoice = await bot.send_invoice(
        chat_id=message.chat.id,
        title=response_text,
        description='1 token = 1 rub',
        payload=str(message.chat.id),
        provider_token=payment_provider_TOKEN,
        currency='rub',
        prices=[
            LabeledPrice(
                label=label_text,
                # Multiplying on 100 because the amount starts with cents (копейки)
                amount=amount*100
            )
        ],
        #start_parameter='@blago7daren',
        reply_markup=keyboard,
        request_timeout=15,
    )
    # Store message ID to edit it later
    dp['payment_message_id'] = invoice.message_id


async def precheckout(precheckout:PreCheckoutQuery):
    await bot.answer_pre_checkout_query(precheckout.id, ok=True)


@dp.message(F.content_type == ContentType.SUCCESSFUL_PAYMENT)
async def process_successful_payment(message:Message):
    user_id = message.from_user.id
    chat_id = message.successful_payment.invoice_payload

    # Retrieve the stored message ID to delete inline_keyboard
    payment_message_id = dp.get('payment_message_id')
    await bot.edit_message_reply_markup(chat_id=chat_id, message_id=payment_message_id, reply_markup=None)

    amount = message.successful_payment.total_amount // 100
    create_or_update_user(user_id, balance=amount)
    add_new_transaction(user_id, amount, action='top_up')
    balance = get_user_balance(user_id)

    user_name = message.from_user.full_name
    response_text = "{user_name} added {amount} tokens to the balance! Current balance is {balance} tokens"
    user_lang = get_user_lang(message.from_user.id)
    if user_lang!='en':
        response_text = translate(response_text, user_lang)
    response_text = response_text.format(user_name=user_name,amount=amount, balance=balance)
    await bot.send_message(int(chat_id), response_text)


@dp.message(Command('check_transactions'))
async def check_transactions(message: Message):
    user_id = message.from_user.id
    create_or_update_user(user_id, default=True)

    transactions_table = get_user_transactions(message.from_user.id)

    # Send the table to the user
    await message.reply(transactions_table, parse_mode=ParseMode.MARKDOWN)


@dp.message(Command('check_projects'))
async def check_projects(message: Message):
    chat_id = message.chat.id
    if chat_id in get_admin_group_ids():
        chat_member = await bot.get_chat_member(chat_id=message.chat.id, user_id=message.from_user.id) 
        if chat_member.status in {ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR}:
            # Interaction with DB
            project_names = get_projects(chat_id)
            if len(project_names)>0:
                response_text = 'This admin group is linked to these projects {project_names}'
                user_lang = get_user_lang(message.from_user.id)
                if user_lang!='en':
                    response_text = translate(response_text, user_lang)
                response_text = response_text.format(project_names=project_names)
            await message.reply(response_text)
            
        else:
            response_text = '[ERROR] You are NOT the admin of this group!'
            user_lang = get_user_lang(message.from_user.id)
            if user_lang!='en':
                response_text = translate(response_text, user_lang)
            await bot.send_message(message.chat.id, response_text)
    else:
        response_text = '[ERROR] This command executes only in admin group!'
        user_lang = get_user_lang(message.from_user.id)
        if user_lang!='en':
            response_text = translate(response_text, user_lang)
        await bot.send_message(message.chat.id, response_text)


@dp.message(Command("set_language"))
async def set_language(message: Message):
    create_or_update_user(message.from_user.id, default=True)
    # Create inline keyboard with language options
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Русский 🇷🇺', callback_data='ru')],
        [InlineKeyboardButton(text='English 🇺🇸', callback_data='en')]])

    # Print the message on certain language based on the language in DB, here I print the english message by default
    await bot.send_message(
            message.chat.id, 
            "Choose language / Выберите язык",
            reply_markup=keyboard
    )


@dp.message(Command("new_channels"))
async def new_channels(message: Message):
    admin_group_ids = get_admin_group_ids()
    chat_id = message.chat.id
    if chat_id in admin_group_ids:
        chat_member = await bot.get_chat_member(chat_id=chat_id, user_id=message.from_user.id) 
        if chat_member.status in {ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR}:
            related_tg_channels_ids = get_related_tg_channels(admin_group_id=chat_id)
            if len(related_tg_channels_ids)>0:
                # Create keyboard and add buttons dynamically
                builder = InlineKeyboardBuilder()
                for related_tg_channel_id in related_tg_channels_ids:
                    channel_info = await bot.get_chat(related_tg_channel_id)
                    channel_name = channel_info.title
                    builder.button(text=channel_name, callback_data=f'new_channels_to_{related_tg_channel_id}_AKA_{channel_name}')
                
                response_text = 'Pick to which TG channel attach new YT channels'
                user_lang = get_user_lang(message.from_user.id)
                if user_lang!='en':
                    response_text = translate(response_text, user_lang)
                await bot.send_message(chat_id, response_text, reply_markup=builder.as_markup())

            else:
                response_text = "No TG channels attached to admin group with id {chat_id}!"
                user_lang = get_user_lang(message.from_user.id)
                if user_lang!='en':
                    response_text = translate(response_text, user_lang)
                response_text = response_text.format(chat_id=chat_id)
                await bot.send_message(chat_id, response_text)
        else:
            response_text = '[ERROR] You are NOT the admin of this group!'
            user_lang = get_user_lang(message.from_user.id)
            if user_lang!='en':
                response_text = translate(response_text, user_lang)
            await bot.send_message(chat_id, response_text)
    else:
        response_text = '[ERROR] This command executes only in admin group!'
        user_lang = get_user_lang(message.from_user.id)
        if user_lang!='en':
            response_text = translate(response_text, user_lang)
        await bot.send_message(chat_id, response_text)
    

# Run the bot
async def run_bot() -> None:
    if TEST_MODE==1:
        clear_up_db()

    # Create tables if not exist
    create_db()

    if TEST_MODE==1:
        load_dummy_data()

    # Set menu for tg bot
    await set_help_menu()

    # Register handlers
    dp.callback_query.register(process_post_reaction, lambda c: c.data.startswith('post_'))
    dp.callback_query.register(process_lang, lambda c: c.data in ['ru', 'en'])
    dp.callback_query.register(process_new_channels, lambda c: c.data.startswith('new_channels_to_'))
    dp.callback_query.register(choose_lang, lambda c: c.data.startswith('config_to'))
    dp.callback_query.register(choose_reference, lambda c: c.data.startswith('config_lang'))
    dp.callback_query.register(choose_img, lambda c: c.data.startswith('config_reference'))
    dp.callback_query.register(process_full_config, lambda c: c.data.startswith('config_img'))
    dp.callback_query.register(process_chosen_tg, lambda c: c.data.startswith('vtp'))
    dp.callback_query.register(process_cost_approvement, lambda c: c.data.startswith('cost_'))
    dp.callback_query.register(process_cancel, lambda c: c.data.startswith('cancel'))
    dp.pre_checkout_query.register(precheckout)    
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    asyncio.create_task(suggest_new_posts())
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(run_bot())
