import logging

from aiogram import Bot, Dispatcher, types, executor

from postgres import PostgresEngine
from model import TelegramConfig, DatabaseConfig

logging.basicConfig(
    format='[%(asctime)s | %(levelname)s]: %(message)s',
    datefmt='%m.%d.%Y %H:%M:%S',
    level=logging.DEBUG
)


class TelegramBotEngine:

    def __init__(self, telegram_config: TelegramConfig, db_config: DatabaseConfig, dp) -> None:

        self._config = telegram_config
        self._postgres_engine = PostgresEngine(config=db_config)



#TODO: HOW TO USE dp THERE? HOW TO PASS IT THERE?

    @dp.message_handler(commands=['start', 'help'])
    async def process_start_command(self, message: types.Message):
        output_text = 'Введи расход в формате: продукты 500 либо выбери пункт меню'
        markup = types.reply_keyboard.ReplyKeyboardMarkup(row_width=1)
        markup.add(types.KeyboardButton('Мои расходы в этом месяце'))
        for tg_user in self._config.tg_bot_users:
            if tg_user.tg_bot_user_id != message.from_user.id:
                markup.add(types.KeyboardButton('Расходы ' + tg_user.tg_bot_user_name + ' в этом месяце'))
        await message.answer(output_text, reply_markup=markup)