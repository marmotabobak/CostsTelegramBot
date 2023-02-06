#TODO: close Postgres cursors and sessions after use - do it "with..."
import datetime
import logging

from aiogram import Bot, Dispatcher, types, executor
import psycopg2

import model
import settings


logging.basicConfig(format='[%(asctime)s | %(levelname)s]: %(message)s', datefmt='%m.%d.%Y %H:%M:%S', level=logging.INFO)

db_settings = settings.AppSettings(model.Modules.db).settings
tg_bot_settings = settings.AppSettings(model.Modules.bot).settings

class DatabaseInsertError(Exception):
    pass

def write_message_to_db(message_text: str, message_datetime: datetime, user_tg_id: int, postgres_cursor, postgres_connection) -> None:
    query = f'INSERT INTO {db_settings.messages_table} (message_text, message_datetime, user_tg_id) VALUES (\'{message_text}\', \'{message_datetime}\', \'{user_tg_id}\')'
    postgres_cursor.execute(query)
    postgres_connection.commit()
    logging.info('SERVICE: Message has been recorded to the messages table.')

def write_cost_to_db(cost_name: str, cost_amount: float, cost_datetime: datetime, cost_message: str, user_tg_id: int, postgres_cursor, postgres_connection) -> None:
    query = f'INSERT INTO {db_settings.costs_table} (cost_name, cost_amount, cost_datetime, cost_message, user_tg_id, display) VALUES (\'{cost_name}\', {cost_amount}, \'{cost_datetime}\', \'{cost_message}\', \'{user_tg_id}\', True)'
    postgres_cursor.execute(query)
    postgres_connection.commit()
    logging.info('SERVICE: Message has been recorded to the costs table.')


postgres_connection = psycopg2.connect(
    user=db_settings.user,
    password=db_settings.psswd,
    host=db_settings.host,
    port=db_settings.port
)

postgres_cursor = postgres_connection.cursor()
logging.info('SERVICE: Connected to database')
if postgres_cursor:
    postgres_connected = True

bot = Bot(token=tg_bot_settings.tg_bot_api_token)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start', 'help'])
async def process_start_command(message: types.Message):
    global postgres_connected
    if postgres_connected:
        output_text = 'Введи расход в формате: продукты 500 либо выбери пункт меню'
        markup = types.reply_keyboard.ReplyKeyboardMarkup(row_width=1)
        markup.add(types.KeyboardButton('Мои расходы'))
        markup.add(types.KeyboardButton('Обнулить период'))
    else:
        output_text = '! Ошибка подключения к БД - бот недоступен !'
    await message.answer(output_text, reply_markup=markup)

@dp.message_handler(regexp='Мои расходы')
async def view_my_costs(message: types.Message):
    output_text = ''
    current_total = 0
    query = f'SELECT * FROM {db_settings.costs_table} where user_tg_id=\'{message.from_user.id}\' and display'
    postgres_cursor.execute(query)
    for record in postgres_cursor.fetchall():
        output_text += f'{record[3].strftime("%d.%m.%Y")} {record[1]} {record[2]}\n'
        current_total += int(record[2])
    output_text += f'Всего за период: {current_total}'
    await message.answer(output_text)

@dp.message_handler(regexp='Обнулить период')
async def view_my_costs(message: types.Message):
    query = f'UPDATE {db_settings.costs_table} SET display = False'
    postgres_cursor.execute(query)
    output_text = f'Данные обнулены'
    await message.answer(output_text)

@dp.message_handler(lambda message: message.from_user.id in (user.tg_bot_user_id for user in tg_bot_settings.tg_bot_users))
async def process_regular_message(message: types.Message):
    if postgres_connected:
        try:
            write_message_to_db(message.text, datetime.datetime.now(), message.from_user.id, postgres_cursor, postgres_connection)
            message_words = message.text.split()
            cost_name = message_words[0]
            cost_amount = int(message_words[1])
            write_cost_to_db(cost_name, cost_amount, datetime.datetime.now(), message.text, message.from_user.id, postgres_cursor, postgres_connection)
            output_text = f'Внесены данные:\n    время {datetime.datetime.now().strftime("%d.%m.%Y %H:%M")} \n    название {cost_name} \n   сумма {cost_amount} руб. \n'
        except DatabaseInsertError as e:
            output_text = '! Ошибка при записи в БД: ' + str(e)
        except:
            output_text = '! Ошибка при обработке сообщения - пжл, повтори. Формат данных: продукты 500'
    else:
        output_text = '! Ошибка подключения к БД - бот недоступен !'
    await message.answer(output_text)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=False)

try:
    postgres_cursor.close()
    postgres_connection.close()
    print('Connection to database is closed')
except Exception as e:
    print('Error while closing connection to database')
    raise e
