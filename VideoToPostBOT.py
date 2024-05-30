import asyncio
import logging
import requests
import sys
import re
from os import getenv

from aiogram import Bot, Dispatcher, Router
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from pytube import Channel
from VideoToPost import VideoToPost
import pandas as pd
try:
    from secret_key import BOT_TOKEN, YT_API_KEY, TG_CHANNEL_ID, ADMIN_GROUP_CHAT_ID
except:
    BOT_TOKEN = getenv('BOT_TOKEN')
    YT_API_KEY = getenv('YT_API_KEY')
    TG_CHANNEL_ID = getenv('TG_CHANNEL_ID')
    ADMIN_GROUP_CHAT_ID = getenv('ADMIN_GROUP_CHAT_ID')
    api_key_edenai = getenv('api_key_edenai')


# All handlers should be attached to the Router (or Dispatcher)
dp = Dispatcher()
router = Router(name=__name__)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))



@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Hello, I'm a bot created by @blago7daren!")


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


async def check_new_videos(yt_channel_ids, TRACKED_YT_CHANNELS, last_video_ids):
    new_video_urls = []
    bad_creators = []
    for i, CHANNEL_ID  in enumerate(yt_channel_ids):
        yt_author = TRACKED_YT_CHANNELS[i]
        LAST_VIDEO_ID = last_video_ids[i]
        url = f'https://www.googleapis.com/youtube/v3/search?key={YT_API_KEY}&channelId={CHANNEL_ID}&part=snippet,id&order=date&maxResults=5&type=video'#&videoDefinition=any'

        response = requests.get(url).json()
        try: # Some creator's videos can't be accessed, create a logger which notifies about such youtube creator
            latest_video = response['items'][0]
            video_id = latest_video['id']['videoId']

            if video_id != LAST_VIDEO_ID:
                last_video_ids[i] = video_id
                video_details_url = f'https://www.googleapis.com/youtube/v3/videos?key={YT_API_KEY}&id={video_id}&part=contentDetails'
                video_details_response = requests.get(video_details_url).json()
                # Duration of the video in ISO 8601 format
                video_duration = video_details_response['items'][0]['contentDetails']['duration']
                # Convert it to seconds
                video_duration = parse_duration(video_duration)
                # Check if it's a shorts or regular youtube video
                if video_duration>60 and video_duration<1200:
                    new_video_url = f"https://www.youtube.com/watch?v={video_id}"
                    new_video_urls.append(new_video_url)
                elif video_duration<60:
                    await bot.send_message(ADMIN_GROUP_CHAT_ID, f'The last video of {yt_author} was SHORTS(too short)')
                else:
                    await bot.send_message(ADMIN_GROUP_CHAT_ID, f'The last video of {yt_author} was PODCAST(too long)')
        except:
            await bot.send_message(ADMIN_GROUP_CHAT_ID, f'Trouble with the creator {yt_author};\nRequests.get(url) respone -> "{response}"')
            bad_creators.append(yt_author)
            
    return new_video_urls, bad_creators


async def suggest_new_posts():
    while True:
        TRACKED_YT_CHANNELS = pd.read_excel('tracked_yt_channels.xlsx')['tracked_yt_channels']
        yt_channel_ids = [Channel(f'https://www.youtube.com/c/{channel}').channel_id 
                        for channel in TRACKED_YT_CHANNELS]
        last_video_ids = [None for _ in range(len(TRACKED_YT_CHANNELS))]
        print(f"\n{'-'*15}New check cycle{'-'*15}")
        new_video_urls, bad_creators = await check_new_videos(yt_channel_ids, TRACKED_YT_CHANNELS, last_video_ids)
        if len(new_video_urls)>0:
            for video_url in new_video_urls:
                try:
                    post_name, post_dict = VideoToPost(video_url, img=True) 
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
                            ADMIN_GROUP_CHAT_ID, 
                            BufferedInputFile(post_dict['post_img'], filename=f"{post_name}.jpeg"),
                            caption=post_dict['post_txt'], reply_markup=keyboard)
                else:
                    await bot.send_message(ADMIN_GROUP_CHAT_ID, post_dict['post_txt'], reply_markup=keyboard) # + ' (youtube_video_link)'

                await asyncio.sleep(13) # EdenAI request limit ("start" - billing plan)

        if len(bad_creators)>0:
            print(f"\n{'*'*15}Removing creators from which we couldn't retreive the video{'*'*15}")
            TRACKED_YT_CHANNELS = [channel for channel in TRACKED_YT_CHANNELS if channel not in bad_creators]
            pd.DataFrame({'tracked_yt_channels':TRACKED_YT_CHANNELS}).to_excel('tracked_yt_channels.xlsx',index=False)
                        
        await asyncio.sleep(10)  # Check for new videos every 5 hours (18000 sec)


async def process_callback(callback_query: CallbackQuery):
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
                TG_CHANNEL_ID,
                photo=callback_query.message.photo[-1].file_id,  # Send the highest resolution photo
                caption=callback_query.message.caption
            )
        else:
            await bot.send_message(
                TG_CHANNEL_ID,
                text=callback_query.message.text
            )
    elif action == 'disapprove':
        response_text = f"{user_name} disapproved the post."
    
    # Optionally, reply to the user to confirm the action
    await callback_query.message.reply(response_text)


async def main() -> None:
    # Register handlers
    dp.callback_query.register(process_callback, lambda c: c.data in ['approve', 'disapprove'])
    
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    asyncio.create_task(suggest_new_posts())
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
