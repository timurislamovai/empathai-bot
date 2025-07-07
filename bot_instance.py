# bot_instance.py

import os
from aiogram import Bot, Dispatcher

# Инициализация бота и диспетчера
bot = Bot(token=os.environ["TELEGRAM_TOKEN"])
dp = Dispatcher()
