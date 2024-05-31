import io
from pytube import YouTube
from lxml import etree
from os import getenv
try:    
    from secret_key import TEST_MODE
except:
    TEST_MODE = int(getenv('TEST_MODE'))

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
import warnings
warnings.filterwarnings('ignore')


def speech_to_text(audio_bytes):
    # EdenAI version (openai provider)
    url = "https://api.edenai.run/v2/audio/speech_to_text_async"
    data = {
        "providers": "openai",
        "language": "en-US",
    }
    files = {'file': audio_bytes}
    response = requests.post(url, data=data, files=files, headers=headers)
    result = json.loads(response.text)['results']['openai']['text']
    return result


# SubFunctions
def get_post_txt(yt): # Get subtitles or generate from video's audio
    try:
        all_captions = yt.captions # WARNING: add check of auto-generated by yt.captions['a.en']

        if 'en' in all_captions:
            eng_captions = all_captions['en']
        elif 'a.en' in all_captions:
            eng_captions = all_captions['a.en']
        else:
            raise ValueError("Video doesn't have subtitles, need to create")
        
        xml_captions = eng_captions.xml_captions

        # Parse the XML
        root = etree.fromstring(xml_captions.encode('utf-8'))
        text_blocks = []
        for child in root.findall('.//body/p'):
            text_block = ''.join(child.itertext()).strip().replace('\n', ' ')
            cleaned_text_block = text_block.replace('[Music]','').strip()
            if cleaned_text_block!='':
                text_blocks.append(cleaned_text_block)
            
        transcription = ', '.join(text_blocks) # WARNING: maybe change to dots or smth
    except:
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
        
        audio_bytes = get_audio_bytes(yt)
        transcription = speech_to_text(audio_bytes)


    # Summarize trascription
    def get_summary(transcription:str, words_amount:int=150, light_model:str='gpt-3.5-turbo', heavy_model:str='gpt-4o'):
        url = "https://api.edenai.run/v2/text/chat"

        transcription_length = len(transcription.split())
        if transcription_length<2500:
            model = light_model
        else:
            model = heavy_model

        payload = {
            "providers": "openai",
            "text": transcription,
            "chatbot_global_action": f"Convey the essense with around {words_amount} words. Don't speak in third person. Don't say thx for like, watching, or write a comment under the video.",
            "previous_history": [],
            "temperature": 0.0,
            "max_tokens": 150,
            "model": model
        }
        response = requests.post(url, json=payload, headers=headers)

        result = json.loads(response.text)
        try:
            summary = result['openai']['generated_text']
        except:
            raise ValueError(f'Response from EdenAI is not good: {result}')
        return summary
    
    summary = get_summary(transcription)
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
def VideoToPost(link, img=False):
    yt = YouTube(link)
    yt.bypass_age_gate()
    post_name = yt.title + ' (' + yt.author + ')'
    post_txt = get_post_txt(yt)
    if img:
        post_img = get_post_img(yt, post_name)
        overall_post = {'post_txt':post_txt,'post_img':post_img}
    else:
        overall_post = {'post_txt':post_txt}
    return post_name, overall_post

#link = 'https://youtu.be/jNQXAC9IVRw?si=gjx36t0J7pZtvDyd' # with subtitles
#link = 'https://youtu.be/GC80Dk7eg_A?si=n9pIQh0f_A-zVbA_' # with generative subtitles
#link = 'https://youtu.be/ORMx45xqWkA?si=rhEfMiGPJeUpsHGA'# PyTorch in 100 seconds with subtitles
#link = 'https://youtu.be/8PhdfcX9tG0?si=bi-8LixVwwNrpzAM' # "I tried 10 code editors"
#link = 'https://youtu.be/Bp8LcHfFJbs?si=W-HpkIr4o_Bjm7Kd'
#link = 'https://www.youtube.com/watch?v=hlwcZpEx2IY'
#link = 'https://www.youtube.com/watch?v=NU8XGQphI3k'
# link = 'https://www.youtube.com/watch?v=mY7iweEA_HM'

# post_name,overall_post = VideoToPost(link)
# print(overall_post)

