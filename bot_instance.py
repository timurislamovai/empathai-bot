import os
from aiogram import Bot, Dispatcher

bot = Bot(token=os.environ["TELEGRAM_TOKEN"])
dp = Dispatcher()
