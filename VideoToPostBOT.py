import asyncio
import logging
import requests
import sys
import re
from os import getenv

from aiogram import Bot, Dispatcher, Router
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton, Message, BotCommand
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.enums.chat_member_status import ChatMemberStatus
from aiogram.types import Message
import aiotube
from pytube import Channel
import psycopg2
from VideoToPost import VideoToPost
from DB_functions import *
from callback_functions import *
try:
    from secret_key import BOT_TOKEN, YT_API_KEY, TEST_MODE, CREATOR_ID
except:
    BOT_TOKEN = getenv('BOT_TOKEN')
    YT_API_KEY = getenv('YT_API_KEY')
    TEST_MODE = int(getenv('TEST_MODE'))
    CREATOR_ID = int(getenv('CREATOR_ID'))


# All handlers should be attached to the Dispatcher (or Router)
dp = Dispatcher()
#router = Router()
#dp.include_router(router)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Hello, I'm a bot created by @blago7daren! Please contact me if something happens.")


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


async def check_new_videos(admin_group_id, yt_channel_urls, tracked_yt_channels, yt_api=False):
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
                if video_duration>60 and video_duration<1200:
                    new_video_url = f"https://www.youtube.com/watch?v={video_id}"
                    new_latest_videos.add(new_video_url)
                elif video_duration<60:
                    await bot.send_message(admin_group_id, f'[INFO] The last video of {yt_author} was SHORTS(too short)')
                else:
                    await bot.send_message(admin_group_id, f'[INFO] The last video of {yt_author} was PODCAST(too long)')
            except:
                await bot.send_message(admin_group_id, f'[INFO] Trouble with the creator {yt_author};\nRequests.get(url) response -> "{response}"')
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
                if video_duration>60 and video_duration<1200:
                    new_video_url = f"https://www.youtube.com/watch?v={video_id}"
                    new_latest_videos.add(new_video_url)
                elif video_duration<60:
                    await bot.send_message(admin_group_id, f'[INFO] The last video of {yt_author} was SHORTS(too short)')
                else:
                    await bot.send_message(admin_group_id, f'[INFO] The last video of {yt_author} was PODCAST(too long)')
                    
            except Exception as e:
                await bot.send_message(admin_group_id, f'[INFO] Trouble with the creator {yt_author}; Exception: {e} (AIOTUBE)')
                bad_creators.add(yt_author)

    used_video_urls = get_used_video_urls()
    new_latest_video_urls = new_latest_videos - used_video_urls
    return new_latest_video_urls, bad_creators


# Main logic   ## WARNING: manual_check - the user can choose whether to check the new videos of YouTube creators auto or manually
async def suggest_new_posts(delete_bad_creators=True, manual_check=False, test_sleep=45, production_sleep=18000): # delete_bad_creators behaviour should be checked on the same yt_authors (maybe they're bad only sometimes)
    while True:
        all_projects = get_projects_details()
        if len(all_projects)>0:
            for tg_channel_id, admin_group_id in all_projects:
                tracked_yt_channels = get_tracked_channels(tg_channel_id)
                if len(tracked_yt_channels)>0:
                    yt_channel_urls = [f'https://www.youtube.com/c/{channel}' for channel in tracked_yt_channels]
                    print(f"\n{'-'*15}New check cycle{'-'*15}")
                    new_latest_video_urls, bad_creators = await check_new_videos(admin_group_id, yt_channel_urls, tracked_yt_channels) # channel:video_url
                    
                    if len(new_latest_video_urls)>0:
                        for video_url in new_latest_video_urls:
                            try:
                                post_name, post_dict = VideoToPost(video_url, img=True) 
                            except ValueError as e:
                                raise ValueError(e)
                            except:
                                print(f'ERROR: video url did not pass VideoToPost "{video_url}"')
                                continue

                            # Create inline keyboard with approve and disapprove buttons
                            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text='Approve', callback_data='approve')],
                                [InlineKeyboardButton(text='Disapprove', callback_data='disapprove')]])

                            if 'post_img' in post_dict.keys():
                                # Send image with a caption
                                await bot.send_photo(
                                        admin_group_id, 
                                        BufferedInputFile(post_dict['post_img'], filename=f"{post_name}.jpeg"),
                                        caption=post_dict['post_txt'], reply_markup=keyboard)
                            else:
                                await bot.send_message(admin_group_id, post_dict['post_txt'], reply_markup=keyboard) # + ' (youtube_video_link)'

                            await asyncio.sleep(13) # EdenAI request limit ("start" - billing plan)

                        insert_new_video_urls(new_latest_video_urls)

                    if delete_bad_creators:
                        if len(bad_creators)>0:
                            print(f"\n{'*'*15}Removing creators from which we couldn't retreive the video{'*'*15}")
                            remove_yt_creators(bad_creators)

                    if TEST_MODE==1:                
                        await asyncio.sleep(test_sleep)  
                    else:
                        await asyncio.sleep(production_sleep) # Check for new videos every 5 hours (18000 sec)
                else:
                    await bot.send_message(CREATOR_ID, f"[INFO] There are 0 tracked YouTube channels! Auto post sugessting doesn't work...")
                    if TEST_MODE==1:                
                        await asyncio.sleep(test_sleep)  
                    else:
                        await asyncio.sleep(production_sleep)
        else:
            await bot.send_message(CREATOR_ID, f"[INFO] There are 0 projects! Auto post sugessting doesn't work...")
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
        BotCommand(command="/process_video_url", description="Convert a YouTube video URL into telegram post manually"),
        BotCommand(command="/settings", description="Configure bot settings"), # post settings, post destination(maybe later create post_destinations)
        BotCommand(command="/top_up", description="Top up your balance"),
        BotCommand(command="/support", description="Contact the creator"),
        BotCommand(command="/create_project", description="Project is a combo of (name,admin_group,tg_channel)"),
        BotCommand(command="/get_group_id", description="Add bot to admin/destination tg channel and get id")
    ]
    await bot.set_my_commands(commands)


# Sequential data gathering for /create_project 
# Define states
class create_project_FORM(StatesGroup):
    project_name = State()
    admin_group_id = State()
    tg_channel_id = State()

@dp.message(Command('create_project'))
async def create_project(message: Message, state: FSMContext):
    await state.set_state(create_project_FORM.project_name)
    await message.reply("Project name")


# State handler for project_name
@dp.message(create_project_FORM.project_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(project_name=message.text)
    await state.set_state(create_project_FORM.admin_group_id)
    await message.reply("Admin group id\nP.s. Can be accessed with /get_group_id, using bot in created tg group ONLY FOR ADMINS)")


# State handler for admin_group_id
@dp.message(create_project_FORM.admin_group_id)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(admin_group_id=message.text)
    await state.set_state(create_project_FORM.tg_channel_id)
    await message.reply("TG channel id (posts destination)\nP.s. Can be accessed with /get_group_id, using bot in created tg channel for viewers)")


# State handler for tg_channel_id
@dp.message(create_project_FORM.tg_channel_id)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(tg_channel_id=message.text)
    data = await state.get_data()

    # Changes in DB
    try:
        response = insert_new_project(data['project_name'], int(data['admin_group_id']), int(data['tg_channel_id']))
    except:
        response = False

    if response:
        chat_id = message.chat.id
        await bot.send_message(chat_id, f"[INFO] The project {data['project_name']} has been created!...")
    else:
        chat_id = message.chat.id
        await bot.send_message(chat_id, f"The new project HASN'T been created!\nP.s. The frequent error - letters in 'Admin group id' or 'TG channel id'")

    # Finish conversation
    await state.clear()

    
@dp.message(Command('get_group_id'))
async def get_group_id(message: Message):
    if message.chat.type in ['group', 'supergroup']:
        await message.reply(f"ID of this group: {message.chat.id}")
    else:
        await message.reply("This command can only be used in a group or supergroup.")


@dp.message(Command("set_language"))
async def set_language(message: Message):
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
async def insert_yt_creators(message: Message, table_name='TRACKED_YT_CHANNELS'):
    try:
        '''# Extract the channels from the message text
        # channels = message.text.split(' ', 1)[1]

        # Remove any extra spaces and split the channel names by comma
        # new_channels = [channel.strip() for channel in channels.split(',')] # WARNING: MAKE THE SEQUENTIAL DATA GATHERING AS IN /create_project'''

        # Establish db connection
        conn = psycopg2.connect(**DB_config)
        cur = conn.cursor()

        # Check if the command /new_channels executes in admin_group
        cur.execute("""SELECT admin_group_id FROM PROJECTS""")
        admin_group_ids_postgres = cur.fetchall()
        admin_group_ids = {channel_tuple[0] for channel_tuple in admin_group_ids_postgres}
        if message.chat.id in admin_group_ids:
            chat_member = await bot.get_chat_member(chat_id=message.chat.id, user_id=message.from_user.id) 
            if chat_member.status in {ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR}: # WARNING: is channel owner admin by default??
                cur.execute(f"""SELECT TG_CHANNEL_ID FROM PROJECTS WHERE admin_group_id={message.chat.id}""")
                related_tg_channels_ids_postgres = cur.fetchall()
                if len(related_tg_channels_ids_postgres)>0:
                    related_tg_channels_ids = [row[0] for row in related_tg_channels_ids_postgres]
                    
                    # Create keyboard and add buttons dynamically
                    markup = InlineKeyboardMarkup(resize_keyboard=True)
                    id_to_name = {}
                    for related_tg_channel_id in related_tg_channels_ids:
                        channel_name = await bot.get_chat(related_tg_channel_id)
                        markup.add(InlineKeyboardButton(channel_name))
                        id_to_name[channel_name] = related_tg_channel_id
                        
                    await bot.send_message(message.chat.id, f'Pick to which TG channel attach new YT channels', reply_markup=markup)

                    # for channel in new_channels:
                    #     try:
                    #         cur.execute(f"""INSERT INTO {table_name} (YT_channel_id, TG_channel_id) VALUES ('{channel}', {TG_channel_id});""")
                    #         conn.commit()
                    #         await bot.send_message(message.chat.id, f'[INFO] Channels {new_channels} have been added to DB by {message.from_user.full_name}!')
                    #     except psycopg2.errors.UniqueViolation:
                    #         conn.rollback()
                    #         await bot.send_message(message.chat.id, f'[INFO] Channel {channel} already exists in the project!')
                    #     except psycopg2.errors.UndefinedTable:
                    #         conn.rollback()
                    #         '''
                    #         # await bot.send_message(message.chat.id, f'[INFO] Table "{table_name}" does not exist, creating one...')
                    #         # cur.execute(f"""CREATE TABLE IF NOT EXISTS {table_name} (
                    #         #                 channel VARCHAR(255) PRIMARY KEY);""")
                    #         # cur.execute(f"""INSERT INTO {table_name} (YT_channel_id) VALUES ('{channel}');""")
                    #         # conn.commit()
                    #         # await bot.send_message(message.chat.id, f'[INFO] Channels {new_channels} have been added to DB by {message.from_user.full_name}!')
                    #         '''
                else:
                    await bot.send_message(message.chat.id, f'No TG channels attached to admin group with id {message.chat.id}!')
            else:
                await bot.send_message(message.chat.id, f'[ERROR] You are NOT the admin of this group!')
        else:
            await bot.send_message(message.chat.id, f'[ERROR] This command executes only in admin group!')
    except IndexError:
        # WARNING - RESPONSE BASED ON LANG
        # If the command is used incorrectly, send an error message
        await message.reply("Please use the correct format: /new_channels channel1,channel2")
    except psycopg2.errors.OperationalError:
        raise('ERROR: cannot connect to PostgreSQL while insert_new_yt_creators()')
    finally:
        cur.close()
        conn.close()


# Run the bot
async def run_bot() -> None:
    if TEST_MODE==1:
        clear_up_db()

    # Create tables if not exist
    create_db()

    # Set menu for tg bot
    await set_help_menu()

    # Register handlers
    dp.callback_query.register(process_post_reaction, lambda c: c.data in ['approve', 'disapprove'])
    dp.callback_query.register(process_lang, lambda c: c.data in ['ru', 'en'])
    
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    asyncio.create_task(suggest_new_posts())
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(run_bot())
