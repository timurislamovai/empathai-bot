# bot_instance.py

import os
from aiogram import Bot, Dispatcher
from handlers import menu_handlers, aiogram_handlers

# Инициализация бота и диспетчера
bot = Bot(token=os.environ["TELEGRAM_TOKEN"])
dp = Dispatcher()

# Подключение всех маршрутов
dp.include_routers(
    menu_handlers.router,
    aiogram_handlers.router
)
