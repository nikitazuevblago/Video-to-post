import asyncio
import logging
import requests
import sys
import re
from os import getenv

from aiogram import Bot, Dispatcher, html
from aiogram.types import BufferedInputFile
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from pytube import Channel
from VideoToPost import VideoToPost
from secret_key import BOT_TOKEN, YT_API_KEY, GROUP_CHAT_ID, TRACKED_YT_CHANNELS


yt_channel_ids = [Channel(f'https://www.youtube.com/c/{channel}').channel_id 
                  for channel in TRACKED_YT_CHANNELS]
last_video_ids = [None for _ in range(len(TRACKED_YT_CHANNELS))]


# All handlers should be attached to the Router (or Dispatcher)
dp = Dispatcher()


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


def check_new_videos():
    global last_video_ids
    new_video_urls = []
    for i, CHANNEL_ID  in enumerate(yt_channel_ids):
        LAST_VIDEO_ID = last_video_ids[i]
        url = f'https://www.googleapis.com/youtube/v3/search?key={YT_API_KEY}&channelId={CHANNEL_ID}&part=snippet,id&order=date&maxResults=1'
        response = requests.get(url).json()
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
            if video_duration>60:
                new_video_url = f"https://www.youtube.com/watch?v={video_id}"
                new_video_urls.append(new_video_url)
            else:
                new_video_urls.append(None)
        else:
            new_video_urls.append(None)
    return new_video_urls


async def suggest_new_posts(bot):
    while True:
        print('----------------------------New check cycle----------------------------')
        #new_video_urls = check_new_videos()
        new_video_urls = ['https://www.youtube.com/watch?v=rkZzg7Vowao']
        for video_url in new_video_urls:
            if video_url!=None:
                post_name, post_dict = VideoToPost(video_url, img=True) # Somehow img can't be sent.. it says "aiogram.exceptions.TelegramNetworkError"
                if 'post_img' in post_dict.keys():
                    
                    # Send image with a caption
                    await bot.send_photo(
                            GROUP_CHAT_ID, 
                            BufferedInputFile(post_dict['post_img'], filename=f"{post_name}.jpeg"),
                            caption=post_dict['post_txt'])
                else:
                    await bot.send_message(GROUP_CHAT_ID, post_dict['post_txt']) # + ' (youtube_video_link)'
                        
        await asyncio.sleep(20)  # Check for new videos every 10 hours (36000 sec)


async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    async with Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)) as bot:
        await suggest_new_posts(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
