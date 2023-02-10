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

def write_message_to_db(message_text: str, message_datetime: datetime, user_tg_id: int, postgres_cursor, postgres_connection, db_settings) -> None:
    query = f'INSERT INTO {db_settings.messages_table} (message_text, message_datetime, user_tg_id) VALUES (\'{message_text}\', \'{message_datetime}\', \'{user_tg_id}\')'
    postgres_cursor.execute(query)
    postgres_connection.commit()
    logging.info('SERVICE: Message has been recorded to the messages table.')

def write_cost_to_db(cost_name: str, cost_amount: float, cost_datetime: datetime, cost_message: str, user_tg_id: int, postgres_cursor, postgres_connection, db_settings) -> None:
    query = f'INSERT INTO {db_settings.costs_table} (cost_name, cost_amount, cost_datetime, cost_message, user_tg_id, display) VALUES (\'{cost_name}\', {cost_amount}, \'{cost_datetime}\', \'{cost_message}\', \'{user_tg_id}\', True)'
    postgres_cursor.execute(query)
    postgres_connection.commit()
    logging.info('SERVICE: Message has been recorded to the costs table.')

def write_balance_to_db(balance_amount: int, balance_datetime: datetime, user_tg_id: str, postgres_cursor, postgres_connection, db_settings) -> None:
    query = f'INSERT INTO {db_settings.balance_table} (balance_amount, balance_datetime, user_tg_id) VALUES ({balance_amount}, \'{balance_datetime}\', \'{user_tg_id}\')'
    postgres_cursor.execute(query)
    postgres_connection.commit()
    logging.info('SERVICE: Balance has been recorded to the balance table.')


def view_int_display_records_by_user(table_name: str, user_tg_id: int, postgres_cursor) -> tuple:
    output_text = ''
    current_total = 0
    query = f'SELECT * FROM {table_name} where user_tg_id=\'{user_tg_id}\' and display'
    postgres_cursor.execute(query)
    for record in postgres_cursor.fetchall():
        output_text += f'{record[3].strftime("%d.%m.%Y")} {record[1]} {record[2]}\n'
        current_total += int(record[2])
    return (output_text, current_total)

def hide_records_by_user(table_name: str, user_tg_id: int, postgres_cursor, postgres_connection) -> None:
    query = f'UPDATE {table_name} SET display = False where user_tg_id=\'{user_tg_id}\''
    postgres_cursor.execute(query)
    postgres_connection.commit()
    logging.info(f'SERVICE: Hided current records of user {user_tg_id}.')

def view_current_balance(table_name: str, user_tg_id: int, postgres_cursor) -> int:
    query = f'SELECT balance_amount from {table_name} WHERE user_tg_id=\'{user_tg_id}\' order by balance_datetime desc limit 1;'
    postgres_cursor.execute(query)
    res = postgres_cursor.fetchone()[0]
    return res


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
        output_text = 'Расход: продукты 500\nБаланс: баланс 1000'
        markup = types.reply_keyboard.ReplyKeyboardMarkup(row_width=1)
        markup.add(types.KeyboardButton('Расходы и баланс'))
        markup.add(types.KeyboardButton('Обнулить расходы'))
    else:
        output_text = '! Ошибка подключения к БД - бот недоступен !'
    await message.answer(output_text, reply_markup=markup)

@dp.message_handler(regexp='Расходы и Баланс')
async def view_my_costs(message: types.Message):
    output_costs = view_int_display_records_by_user(table_name=db_settings.costs_table, user_tg_id=message.from_user.id, postgres_cursor=postgres_cursor)
    output_balance = view_current_balance(table_name=db_settings.balance_table, user_tg_id=message.from_user.id, postgres_cursor=postgres_cursor)
    output_text = output_costs[0] + '-----\nВсего за период: ' + str(output_costs[1]) + '\n\nТекущий баланс: ' + str(output_balance)
    await message.answer(output_text)

@dp.message_handler(regexp='Обнулить период')
async def hide_old_messages(message: types.Message):
    output_text = view_int_display_records_by_user(table_name=db_settings.costs_table, user_tg_id=message.from_user.id, postgres_cursor=postgres_cursor)
    output_balance = view_current_balance(table_name=db_settings.balance_table, user_tg_id=message.from_user.id, postgres_cursor=postgres_cursor)
    hide_records_by_user(table_name=db_settings.costs_table, user_tg_id=message.from_user.id, postgres_cursor=postgres_cursor, postgres_connection=postgres_connection)
    write_balance_to_db(0, datetime.datetime.now(), message.from_user.id, postgres_cursor,
                        postgres_connection, db_settings)
    output_text = 'Обнуляемые данные:\n' + output_text[0] + 'Всего за период: ' + str(output_text[1]) + '\n\nПредыдущий баланс: ' + str(output_balance)+ '\n\n Данные обнулены'
    await message.answer(output_text)

@dp.message_handler(regexp='баланс *')
async def hide_old_messages(message: types.Message):
    if postgres_connected:
        try:
            write_message_to_db(message.text, datetime.datetime.now(), message.from_user.id, postgres_cursor, postgres_connection, db_settings)
            message_words = message.text.split()
            balance_amount = int(message_words[-1])
            output_balance = view_current_balance(table_name=db_settings.balance_table, user_tg_id=message.from_user.id,
                                                  postgres_cursor=postgres_cursor)
            write_balance_to_db(balance_amount, datetime.datetime.now(), message.from_user.id, postgres_cursor,
                                postgres_connection, db_settings)
            output_text = f'Предыдущий баланс: {output_balance} \nБаланс обновлен.'
        except DatabaseInsertError as e:
            output_text = '! Ошибка при записи в БД: ' + str(e)
        except:
            output_text = '! Ошибка при обработке сообщения - пжл, повтори. Формат данных: баланс 1000'
    else:
        output_text = '! Ошибка подключения к БД - бот недоступен !'
    await message.answer(output_text)

@dp.message_handler(lambda message: message.from_user.id in (user.tg_bot_user_id for user in tg_bot_settings.tg_bot_users))
async def process_regular_message(message: types.Message):
    if postgres_connected:
        try:
            write_message_to_db(message.text, datetime.datetime.now(), message.from_user.id, postgres_cursor, postgres_connection, db_settings)
            message_words = message.text.split()
            cost_name = ' '.join(message_words[:-1])
            cost_amount = int(message_words[-1])
            balance_amount = view_current_balance(table_name=db_settings.balance_table, user_tg_id=message.from_user.id, postgres_cursor=postgres_cursor) - cost_amount
            write_cost_to_db(cost_name, cost_amount, datetime.datetime.now(), message.text, message.from_user.id, postgres_cursor, postgres_connection, db_settings)
            write_balance_to_db(balance_amount, datetime.datetime.now(), message.from_user.id, postgres_cursor, postgres_connection, db_settings)
            output_text = f'Внесены данные:\n    время {datetime.datetime.now().strftime("%d.%m.%Y %H:%M")} \n    название {cost_name} \n   сумма {cost_amount} руб. \n\nОбновлен баланс: {balance_amount}'
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
