import os
import gettext

def get_translator(lang):
    locales_path = os.path.join(os.path.dirname(__file__), 'locales')
    return gettext.translation('messages', localedir=locales_path, languages=[lang], fallback=True)

def translate(text, lang):
    translator = get_translator(lang)
    return translator.gettext(text)
