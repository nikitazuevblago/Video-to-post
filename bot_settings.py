from os import getenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
try:
    from secret_key import BOT_TOKEN
except:
    BOT_TOKEN = getenv('BOT_TOKEN')

# All handlers should be attached to the Dispatcher (or Router)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
#router = Router()
#dp.include_router(router)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))