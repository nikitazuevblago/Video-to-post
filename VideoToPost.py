import io
from pytube import YouTube
from lxml import etree
import time
import aiotube
from os import getenv
try:    
    from secret_key import TEST_MODE, EXCHANGERATE_API
    TEST_MODE = int(TEST_MODE)
except:
    TEST_MODE = int(getenv('TEST_MODE'))
    EXCHANGERATE_API = int(getenv('EXCHANGERATE_API'))

if TEST_MODE==1:
    try:    
        from secret_key import API_KEY_EDENAI_SANDBOX
    except:
        API_KEY_EDENAI_SANDBOX = getenv('API_KEY_EDENAI_SANDBOX')
    # Configuration for EdenAI
    headers = {"Authorization": API_KEY_EDENAI_SANDBOX}
else:
    try:    
        from secret_key import API_KEY_EDENAI
    except:
        API_KEY_EDENAI = getenv('API_KEY_EDENAI')
    # Configuration for EdenAI
    headers = {"Authorization": API_KEY_EDENAI}

import json
import requests
from PIL import Image
from io import BytesIO
import pytube.exceptions as exceptions
from pytube.innertube import InnerTube
import warnings
warnings.filterwarnings('ignore')

# Create a subclass of YouTube
class MyYouTube(YouTube):
    # Rewrite the function in pytube library for the possibility to iterate clients like "WEB", "ANDROID"...
    def bypass_age_gate(self, client):
        """Attempt to update the vid_info by bypassing the age gate."""
        innertube = InnerTube(
            client=client,
            use_oauth=self.use_oauth,
            allow_cache=self.allow_oauth_cache
        )
        innertube_response = innertube.player(self.video_id)

        playability_status = innertube_response['playabilityStatus'].get('status', None)

        # If we still can't access the video, raise an exception
        # (tier 3 age restriction)
        if playability_status == 'UNPLAYABLE':
            raise exceptions.AgeRestrictedError(self.video_id)

        self._vid_info = innertube_response


# To imitate the open('file_path.mp4','rb')
class NamedBufferedReader:
    def __init__(self, raw, name):
        self.buffered_reader = io.BufferedReader(raw)
        self.name = name

    def read(self, *args, **kwargs):
        return self.buffered_reader.read(*args, **kwargs)

    def readline(self, *args, **kwargs):
        return self.buffered_reader.readline(*args, **kwargs)

    def readlines(self, *args, **kwargs):
        return self.buffered_reader.readlines(*args, **kwargs)

    def __getattr__(self, attr):
        return getattr(self.buffered_reader, attr)


def speech_to_text(audio_bytes, provider='openai'):
    # EdenAI version (openai provider)
    url = "https://api.edenai.run/v2/audio/speech_to_text_async"
    data = {
        "providers": provider,
    }
    files = {'file': audio_bytes}
    response = requests.post(url, data=data, files=files, headers=headers)
    json_result = json.loads(response.text)
    try:
        result = json_result['results'][provider]['text']
        return result
    except:
        raise ValueError(json_result)
    

def detect_language(text, provider='google'):
    # EdenAI version (openai provider)
    url ="https://api.edenai.run/v2/translation/language_detection"
    data = {
        "providers": provider,
        'text':text
    }
    response = requests.post(url, json=data, headers=headers)
    provider_result = json.loads(response.text)[provider]
    try:
        result = provider_result['items'][0]['language']
        return result
    except:
        raise ValueError(provider_result)

# Summarize trascription
def get_summary(transcription:str, post_lang='en', words_amount:int=150,
                light_model:str='gpt-3.5-turbo', heavy_model:str='gpt-4o', max_tokens=350):
    url = "https://api.edenai.run/v2/text/chat"

    transcription_length = len(transcription.split())
    if transcription_length<2500:
        model = light_model
    else:
        model = heavy_model

    if TEST_MODE==0:
        first_words = ' '.join(transcription.split()[:10])
        transcription_lang = detect_language(first_words)
    else:
        transcription_lang = post_lang

    if transcription_lang == 'en':
        prompt = f"Convey the essence with around {words_amount} words. Don't speak in third person. Don't say thx for like, watching, or write a comment under the video."
    elif transcription_lang == 'ru':
        prompt = f"Передай суть примерно в {words_amount} словах. Не говори в третьем лице. Не говори спасибо за лайк, просмотр или пишите комментарий под видео."

    if transcription_lang!=post_lang:
        if transcription_lang == 'en':
            prompt += 'Translate from english to russian. '
        elif transcription_lang == 'ru':
            prompt += 'Переведи с русского на английский. '

    payload = {
        "providers": "openai",
        "text": transcription,
        "chatbot_global_action": prompt,
        "previous_history": [],
        "temperature": 0.0,
        "max_tokens": max_tokens,
        "model": model
    }
    response = requests.post(url, json=payload, headers=headers)

    result = json.loads(response.text)
    try:
        summary = result['openai']['generated_text']
    except:
        raise ValueError(f'Response from EdenAI is not good: {result}')
    return summary


# Function to get audio bytes from a YouTube video
def get_audio_bytes(yt):

    # Filter audio streams and get the first one (usually 'mp4')
    audio_stream = yt.streams.filter(only_audio=True).first()
    
    # Download the audio stream to a buffer
    audio_buffer = io.BytesIO()

    audio_stream.stream_to_buffer(audio_buffer)
    
    # Get the bytes from the buffer
    audio_bytes = audio_buffer.getvalue()
    
    return audio_bytes


# Imitating open('file_path.mp4','rb')
def get_buffered_reader(audio_bytes):
    # Step 2: Create an in-memory binary stream from the audio bytes
    bytes_io = io.BytesIO(audio_bytes)

    # Step 3: Wrap the BytesIO stream with NamedBufferedReader
    named_buffered_reader = NamedBufferedReader(bytes_io, 'audio.mp4')
    return named_buffered_reader


# SubFunctions
def get_post_txt(yt, creator_name=False, post_lang='en'): # Get subtitles or generate from video's audio

    try:
        all_captions = yt.captions

        if post_lang=='en':
            subtitles_order = ['en','a.en','ru']
        elif post_lang=='ru':
            subtitles_order = ['ru','en','a.en']       
        
        for subtitle_lang in subtitles_order:
            if subtitle_lang in all_captions:
                captions = all_captions[subtitle_lang]
                break
        
        if not 'captions' in locals():
            raise ValueError("Video doesn't have subtitles, need to create")
        
        xml_captions = captions.xml_captions
        # print(f'xml_captions {xml_captions}')

        # # Parse the XML
        # root = etree.fromstring(xml_captions.encode('utf-8'))
        # text_blocks = []
        # for child in root.findall('.//body/p'):
        #     text_block = ''.join(child.itertext()).strip().replace('\n', ' ')
        #     cleaned_text_block = text_block.replace('[Music]','').strip()
        #     if cleaned_text_block!='':
        #         text_blocks.append(cleaned_text_block)

        # Parse the XML
        root = etree.fromstring(xml_captions.encode('utf-8'))
        text_blocks = []
        for child in root.findall('.//text'):  # Corrected XPath
            text_block = ''.join(child.itertext()).strip().replace('\n', ' ')
            cleaned_text_block = text_block.replace('[Music]', '').strip()
            if cleaned_text_block != '':
                text_blocks.append(cleaned_text_block)
            
        transcription = ', '.join(text_blocks) 
        #print(f'transcription: {transcription}')
    except:
        audio_bytes = get_audio_bytes(yt)
        named_buffered_reader = get_buffered_reader(audio_bytes)
        transcription = speech_to_text(named_buffered_reader)
    
    # Detect the YT video language
    summary = get_summary(transcription, post_lang=post_lang)

    if creator_name and post_lang=='en':
        summary += f'\nThe original creator is - {creator_name}'
    if creator_name and post_lang=='ru':
        summary += f'\nОригинальный создатель - {creator_name}'
    return summary


def get_post_img(yt, thumbnail=True):
    # Get the video's thumbnail
    if thumbnail:
        thumbnail_url = yt.thumbnail_url

        # Send a GET request to the URL
        response = requests.get(thumbnail_url)

        # Save image
        image = Image.open(BytesIO(response.content))

        # Define the cropping box
        # (left, upper, right, lower) - crop 10% from each side
        width, height = image.size
        left = 0
        right = width
        upper = height * 0.13
        lower = height * 0.87
        croped_img = image.crop((left, upper, right, lower))

        # Convert img to byte array
        img_byte_arr = io.BytesIO()
        croped_img.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()

        # return img_path
        return img_byte_arr
        
    # Generate the video (Then maybe add option to get images from internet)
    else: 
        pass


# MainFunction
def VideoToPost(link, post_lang='en', reference=False, post_img=False):
    yt = MyYouTube(link)
    clients = ['ANDROID', 'IOS', 'WEB_EMBED', 'ANDROID_EMBED', 'IOS_EMBED', 'WEB_MUSIC', 'ANDROID_MUSIC',
               'IOS_MUSIC', 'WEB_CREATOR', 'WEB', 'ANDROID_CREATOR', 'IOS_CREATOR', 'MWEB', 'TV_EMBED']
    for client in clients:
        try:
            # I modified the function bypass_age_gate() in pytube/__main__
            yt.bypass_age_gate(client=client)
            print(f'Bypassed YouTube age gate with "{client}" as a client')
            break
        except:
            pass
    post_name = yt.title + ' (' + yt.author + ')'
    if reference:
        creator_name = yt.author
    else:
        creator_name = False
    
    max_attempts = 3
    for i_attempt in range(1,max_attempts+1):
        try:
            post_txt = get_post_txt(yt, creator_name=creator_name, post_lang=post_lang)
            break
        except:
            print(f'{i_attempt} attempt of get_post_txt failed!')
            time.sleep(5)
    if 'post_txt' in locals(): 
        if post_img:
            post_img = get_post_img(yt, post_name)
            overall_post = {'post_txt':post_txt,'post_img':post_img}
        else:
            overall_post = {'post_txt':post_txt}
        return post_name, overall_post
    else:
        raise ValueError("Couldn't get text for the post!")


# Additional functions before VideoToPost()
def usd_rub_rate(api_key):
    base_currency = 'USD'
    target_currency = 'RUB'
    url = f'https://v6.exchangerate-api.com/v6/{api_key}/latest/{base_currency}'
    response = requests.get(url)
    data = response.json()
    if response.status_code == 200:
        exchange_rate = data['conversion_rates'][target_currency]
        return exchange_rate
    else:
        raise Exception("Error fetching exchange rate data: " + data['error-type'])
    

def get_post_cost(link):
    yt = MyYouTube(link)
    clients = ['ANDROID', 'IOS', 'WEB_EMBED', 'ANDROID_EMBED', 'IOS_EMBED', 'WEB_MUSIC', 'ANDROID_MUSIC',
               'IOS_MUSIC', 'WEB_CREATOR', 'WEB', 'ANDROID_CREATOR', 'IOS_CREATOR', 'MWEB', 'TV_EMBED']
    for client in clients:
        try:
            # I modified the function bypass_age_gate() in pytube/__main__
            yt.bypass_age_gate(client=client)
            print(f'Bypassed YouTube age gate with "{client}" as a client')
            break
        except:
            pass
    all_captions = {caption.code for caption in yt.captions}
    accepted_captions = {'a.en','en','ru'} & all_captions
    if len(accepted_captions)<1:
        # Price is calculated in dollars!
        whisper_per_second_price = 0.006/60
        speech_to_text_price = yt.length * whisper_per_second_price

        # Details for summarization_price
        gpt40_per_token_price = 0.015/1000
        max_summary_tokens = 350

        summarization_price = max_summary_tokens * gpt40_per_token_price
        manufacturing_cost = speech_to_text_price+summarization_price
    else:
        # Details for summarization_price
        gpt40_per_token_price = 0.015/1000
        max_summary_tokens = 350

        summarization_price = max_summary_tokens * gpt40_per_token_price
        manufacturing_cost = summarization_price
    
    # Return the "market price" in rubles with multiplier of 10
    market_price = round(usd_rub_rate(EXCHANGERATE_API)*manufacturing_cost*10,2)

    # Minimal market_price is 20 rubles
    minimal_market_price = 20
    if market_price<minimal_market_price:
        market_price = minimal_market_price
    return market_price



#link = 'https://youtu.be/jNQXAC9IVRw?si=gjx36t0J7pZtvDyd' # with subtitles
#link = 'https://youtu.be/GC80Dk7eg_A?si=n9pIQh0f_A-zVbA_' # with generative subtitles
# link = 'https://youtu.be/hRKXaQbCSWE?si=sImvVnFIthAFRmtH' # Russian music clip
# link = 'https://youtu.be/eH_TOrddnZ0?si=pwpELPdAcO5XOzG5'
# link = 'https://youtu.be/eH_TOrddnZ0?si=pwpELPdAcO5XOzG5'

# name, post = VideoToPost('https://www.youtube.com/watch?v=RJDCvuW7C9A', reference=True, post_lang='ru')
# print(post)