from aiogram import Bot, Dispatcher
import os

bot = Bot(token=os.environ["TELEGRAM_TOKEN"])
dp = Dispatcher()
