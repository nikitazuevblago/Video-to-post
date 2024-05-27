import os
from pytube import YouTube
from lxml import etree
from pathlib import Path
import ffmpeg
from secret_key import api_key_edenai
import json
import requests
from PIL import Image
from io import BytesIO
import pickle
import warnings
warnings.filterwarnings('ignore')

# Configuration for EdenAI
headers = {"Authorization": api_key_edenai}


def speech_to_text(audio_filepath):
    # EdenAI version (openai provider)
    url = "https://api.edenai.run/v2/audio/speech_to_text_async"
    data = {
        "providers": "openai",
        "language": "en-US",
    }
    files = {'file': open(audio_filepath, 'rb')}
    response = requests.post(url, data=data, files=files, headers=headers)
    result = json.loads(response.text)['results']['openai']['text']
    return result




# SubFunctions
def get_post_txt(yt, post_name, audio_dir_path:str='yt_audio/'): # Get subtitles or generate from video's audio
    try:
        all_captions = yt.captions # WARNING: add check of auto-generated by yt.captions['a.en']

        if 'en' in all_captions:
            eng_captions = all_captions['en']
        elif 'a.en' in all_captions:
            eng_captions = all_captions['a.en']
        else:
            raise ValueError("Video doesn't have subtitles, need to create")
        
        xml_captions = eng_captions.xml_captions

        # Fn for extracting subtitles
        def format_time(milliseconds):
            seconds, milliseconds = divmod(milliseconds, 1000)
            minutes, seconds = divmod(seconds, 60)
            hours, minutes = divmod(minutes, 60)
            return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

        # Parse the XML
        root = etree.fromstring(xml_captions.encode('utf-8'))
        text_blocks = []
        for i, child in enumerate(root.findall('.//body/p')):
            text_block = ''.join(child.itertext()).strip().replace('\n', ' ')
            cleaned_text_block = text_block.replace('[Music]','').strip()
            if cleaned_text_block!='':
                text_blocks.append(cleaned_text_block)
            
        transcription = ', '.join(text_blocks) # WARNING: maybe change to dots or smth
    except:
        # Function to get the audio stream URL
        def get_audio_stream_url(yt):
            audio_stream = yt.streams.filter(only_audio=True).first()
            return audio_stream.url

        # Function to stream and save the audio using ffmpeg
        def stream_audio(yt, audio_filepath):
            audio_url = get_audio_stream_url(yt)
            stream = ffmpeg.input(audio_url)
            stream = ffmpeg.output(stream, str(audio_filepath), format='mp3')
            ffmpeg.run(stream)

        # Define paths
        audio_dir = Path(audio_dir_path)
        audio_dir.mkdir(parents=True, exist_ok=True)
        audio_filepath = audio_dir / f'{post_name}.mp3'

        # Save audio file
        stream_audio(yt, str(audio_filepath))
        transcription = speech_to_text(audio_filepath)


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
        summary = result['openai']['generated_text']
        return summary
    
    summary = get_summary(transcription)
    return summary


def get_post_img(yt, post_name, thumbnail=True, img_path:str='images'):
    # Get the video's thumbnail
    if thumbnail:
        thumbnail_url = yt.thumbnail_url

        # Send a GET request to the URL
        response = requests.get(thumbnail_url)

        # Save image
        image = Image.open(BytesIO(response.content))
        
        # Save the image to the specified path
        img_path = Path(img_path)
        img_path.mkdir(parents=True, exist_ok=True)
        img_path = img_path / f'{post_name}.jpg'
        image.save(img_path)
        return image
    # Generate the video (Then maybe add option to get images from internet)
    else: 
        pass


# MainFunction
def VideoToPost(link, img=False, post_dir='posts/'):
    yt = YouTube(link)
    yt.bypass_age_gate()
    post_name = yt.title + ' (' + yt.author + ')'
    post_txt = get_post_txt(yt, post_name)
    if img:
        post_img = get_post_img(yt, post_name)
        overall_post = {'post_text':post_txt,'post_img':post_img}
    else:
        overall_post = {'post_text':post_txt}
    post_dir = Path(post_dir)
    post_dir.mkdir(parents=True, exist_ok=True)
    post_path = post_dir / f'{post_name}.pkl'
    with open(post_path,'wb') as post_file:
        pickle.dump(overall_post, post_file)

link = 'https://youtu.be/jNQXAC9IVRw?si=gjx36t0J7pZtvDyd' # with subtitles
#link = 'https://youtu.be/GC80Dk7eg_A?si=n9pIQh0f_A-zVbA_' # with generative subtitles
#link = 'https://youtu.be/ORMx45xqWkA?si=rhEfMiGPJeUpsHGA'# PyTorch in 100 seconds with subtitles
#link = 'https://youtu.be/8PhdfcX9tG0?si=bi-8LixVwwNrpzAM' # "I tried 10 code editors"
#link = 'https://youtu.be/Bp8LcHfFJbs?si=W-HpkIr4o_Bjm7Kd'

VideoToPost(link)

