import datetime, time

from aiogram import Bot, Dispatcher, types, executor
import psycopg2
from psycopg2 import Error
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from settings import bot_settings, db_settings

class DatabaseInsertError(Exception):
    pass

def write_message_to_db(message_text: str, message_datetime: datetime, user_tg_id: int, postgres_cursor, postgres_connection) -> None:
    try:
        query = f'INSERT INTO messages (message_text, message_datetime, user_tg_id) VALUES (\'{message_text}\', \'{message_datetime}\', \'{user_tg_id}\')'
        postgres_cursor.execute(query)
        postgres_connection.commit()
        print('--- INFO --- Сообщение успешно записпно в БД (messages):', message_text, 'от', user_tg_id)
        print('Текст запроса:', query)
    except:
        print('--- ERROR --- Ошибка при записи в БД (messages) сообщения:', message_text, 'от', user_tg_id)
        print('Текст запроса:', query)
        raise DatabaseInsertError('Ошибка при записи в БД (messages) сообщения') from None

def write_cost_to_db(cost_name: str, cost_amount: float, cost_datetime: datetime, cost_message: str, user_tg_id: int, postgres_cursor, postgres_connection) -> None:
    try:
        query = f'INSERT INTO costs (cost_name, cost_amount, cost_datetime, cost_message, user_tg_id) VALUES (\'{cost_name}\', {cost_amount}, \'{cost_datetime}\', \'{cost_message}\', \'{user_tg_id}\')'
        postgres_cursor.execute(query)
        postgres_connection.commit()
        print('--- INFO --- Сообщение успешно записпно в БД (costs):', cost_message, 'от', user_tg_id)
        print('Текст запроса:', query)
    except:
        print('--- ERROR --- Ошибка при записи в БД (costs) сообщения:', cost_message, 'от', user_tg_id)
        print('Текст запроса:', query)
        raise DatabaseInsertError('Ошибка при записи в БД (costs) сообщения') from None

try:
    postgres_connection = psycopg2.connect(
        user=db_settings.postgres_user,
        password=db_settings.postgres_psswd,
        host=db_settings.postgres_host,
        port=db_settings.postgres_port
    )
    postgres_cursor = postgres_connection.cursor()
    print('--- INFO --- Подулючились к БД:', postgres_connection)
    postgres_connected = True
except:
    print('--- ERROR --- Проблема подключения к БД')
    postgres_connected = False


bot = Bot(token=bot_settings.TG_API_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start', 'help'])
async def process_start_command(message: types.Message):
    global postgres_connected
    print(postgres_connected)
    if postgres_connected:
        output_text = 'Введи расход в формате: продукты 500 либо выбери пункт меню'
        markup = types.reply_keyboard.ReplyKeyboardMarkup(row_width=1)
        markup.add(types.KeyboardButton('Мои расходы в этом месяце'))
        for user in bot_settings.TG_USERS.values():
            if user != message.from_user.id:
                markup.add(types.KeyboardButton('Расходы ' + user + ' в этом месяце'))
    else:
        output_text = '! Ошибка подключения к БД - бот недоступен !'
    await message.answer(output_text, reply_markup=markup)

@dp.message_handler(regexp='Мои расходы в этом месяце')
async def view_my_costs(message: types.Message):
    output_text = ''
    current_year = datetime.datetime.now().year
    current_month = datetime.datetime.now().month
    current_total = 0
    query = f'SELECT * FROM costs where extract(month from cost_datetime) = \'{current_month}\' and extract(year from cost_datetime) = \'{current_year}\' and user_tg_id=\'{message.from_user.id}\''
    postgres_cursor.execute(query)
    for record in postgres_cursor.fetchall():
        output_text += f'{record[3].strftime("%d")} {record[1]} {record[2]}\n'
        current_total += int(record[2])
    output_text += f'Всего за месяц: {current_total}'
    await message.answer(output_text)

@dp.message_handler(lambda message: message.from_user.id in bot_settings.TG_USERS)
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
    print('--- INFO --- Соединение с БД успешно закрыто')
except:
    print('--- ERROR --- Проблемы с закрытием соединения с БД')
