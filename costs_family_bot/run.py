# TODO: write autotests
# TODO: Refactor with classes in outer modules (how to pass dp and how not to use global postgres_engine)
import yaml
import logging
from pathlib import Path
import argparse
import os

from aiogram import Bot, Dispatcher, types, executor
from sqlalchemy import select, func

from model import Config, Cost, Message
from postgres import PostgresEngine
from funcs import *


logging.basicConfig(
    format='[%(asctime)s | %(levelname)s]: %(message)s',
    datefmt='%m.%d.%Y %H:%M:%S',
    level=logging.INFO
)

parser = argparse.ArgumentParser()
parser.add_argument('--config', '-c', type=str, help='config path')
args = parser.parse_args()
config_path_str = args.config or os.environ.get('APP_CONFIG_PATH')

if config_path_str:
    config_path = Path(config_path_str).resolve()
    logging.info(f'Starting service with config {config_path}')
else:
    raise ValueError('App config path should be provided in -c argument')

with open(config_path) as f:
    data = yaml.safe_load(f)

config = Config.parse_obj(data)
logging.info(f'[x] Service started')

TG_USERS = {user.tg_bot_user_id: user.tg_bot_user_name for user in config.telegram.tg_bot_users}
logging.info(f'[x] {len(TG_USERS)} user{"s" if len(TG_USERS) > 1 else ""} info loaded from config')

try:
    bot = Bot(token=config.telegram.tg_bot_api_token)
    dp = Dispatcher(bot)
    logging.info(f'[x] Telegram bot initialized')
except Exception:
    logging.error(f'[x] Error while initializing Telegram bot')
    raise

try:
    postgres_engine = PostgresEngine(config=config.db)
    # postgres_engine.drop_and_create_all_tables()
except Exception:
    logging.error(f'[x] Error while initializing Postgres engine')
    raise


def current_total_month_costs_by_users() -> str:
    global postgres_engine
    global TG_USERS

    output_text = 'Сумарно за месяц:'

    session = postgres_engine.session()
    try:

        result = session.query(Cost.user_telegram_id, func.sum(Cost.amount)).group_by(Cost.user_telegram_id).where(
             Cost.ts >= first_day_of_current_month()
        ).all()

        for tg_user_id, cost_amount in result:
            tg_user_name = TG_USERS.get(tg_user_id, tg_user_id)
            output_text += f'\n    {tg_user_name}: {num_with_delimiters(num=cost_amount)} руб.'

        return output_text

    except Exception as e:
        logging.error(f'Error while reading database: {e}')
        return '!ERR! Ошибка получения данных'
    finally:
        session.close()
        logging.debug('[x] Postgres session closed')


@dp.message_handler(commands=['start', 'help'])
async def process_start_command(message: types.Message) -> None:
    global TG_USERS

    output_text = 'Введи расход в формате: продукты 500 либо выбери пункт меню'
    markup = types.reply_keyboard.ReplyKeyboardMarkup(row_width=1)
    markup.add(types.KeyboardButton('Мои расходы в этом месяце'))
    for tg_user_id, tg_user_name in TG_USERS.items():
        if tg_user_id != message.from_user.id:
            markup.add(types.KeyboardButton('Расходы ' + tg_user_name + ' в этом месяце'))
    markup.add(types.KeyboardButton('Отчет по расходам за прошлый месяц'))
    await message.answer(output_text, reply_markup=markup)


@dp.message_handler(regexp=r'.+асход.* месяц.?')
async def view_my_costs(message: types.Message) -> None:

    global postgres_engine
    global TG_USERS

    output_text = ''

    try:
        day_from = first_day_of_current_month()
        day_to = first_day_of_next_month()
        month_name = get_month_name(day_from.month)
        if message.text == 'Мои расходы в этом месяце':
            users = {message.from_user.id: TG_USERS[message.from_user.id]}
        elif message.text == 'Отчет по расходам за прошлый месяц':
            day_from = first_day_of_last_month()
            day_to = first_day_of_current_month()
            month_name = get_month_name(day_from.month)
            users = TG_USERS
        elif 'Расходы ' in message.text:
            user_name = message.text.split('Расходы ')[1].split(' в этом месяце')[0]
            user_tg_id = int(next(filter(lambda x: TG_USERS[x] == user_name, TG_USERS.keys())))
            users = {user_tg_id: user_name}
        else:
            raise ValueError

        users_costs = {}

        try:
            session = postgres_engine.session()

            for user_tg_id, user_name in users.items():
                output_text = f'Расходы {user_name} за {month_name}:\n'
                current_total = 0

                stmt = select(Cost).order_by(Cost.ts).where(
                    Cost.user_telegram_id == user_tg_id
                ).where(
                    Cost.ts >= day_from
                ).where(
                    Cost.ts < day_to
                )

                for cost in session.scalars(stmt):
                    output_text += f'    {cost.ts.strftime("%d")} {cost.name} {num_with_delimiters(num=cost.amount)}\n'
                    current_total += cost.amount

                if current_total:
                    output_text += f'\nВсего: {num_with_delimiters(num=current_total)}'
                else:
                    output_text += 'Данные за период отсутствуют'

                users_costs[user_tg_id] = current_total

                await message.answer(output_text)

            if len(users) == 2:
                output_text = f'Суммарно за {month_name}:'
                for user_tg_id, user_name in users.items():
                    output_text += f'\n    {user_name}: {num_with_delimiters(users_costs[user_tg_id])}'
                    to_extra_pay = int((max(users_costs.values()) - users_costs[user_tg_id]) / 2)
                    output_text += f' (+ {to_extra_pay})' if to_extra_pay else ''
                output_text += f'\n\nВсего: {num_with_delimiters(sum(users_costs.values()))}'
                await message.answer(output_text)
            elif len(users) > 2:
                # TODO: calculate extrapay distributaion among users
                pass

        except Exception as e:
            logging.error(f'Error while reading database: {e}')
            output_text += f'!ERR! Ошибка чтения из базы данных'
        finally:
            session.close()
            logging.debug('[x] Postgres session closed')

    except (IndexError, ValueError) as e:
        users = []
        logging.error(f'Error while parsing button message text: {e}')
        output_text = f'!ERR! Ошибка парсинга сообщения'
    except Exception:
        raise


@dp.message_handler(lambda message: message.from_user.id in (
        user.tg_bot_user_id for user in config.telegram.tg_bot_users
))
async def process_regular_message(message: types.Message):
    global postgres_engine

    try:
        message_text_words = message.text.split()
        cost_name = ' '.join(message_text_words[:-1])
        cost_amount = int(message_text_words[-1])
    except (TypeError, ValueError):
        cost_name, cost_amount = None, None
    except Exception:
        raise

    now_ts = datetime_now()
    session = postgres_engine.session()

    try:
        session.add(
            Message(
                text=message.text,
                ts=now_ts,
                user_telegram_id=message.from_user.id
            )
        )
        session.commit()

        if cost_name and cost_amount:
            session.add(
                Cost(
                    name=cost_name,
                    amount=cost_amount,
                    ts=now_ts,
                    message_text=message.text,
                    user_telegram_id=message.from_user.id
                )
            )
            session.commit()

            output_text = f'Внесены данные:\n    время: {datetime_now().strftime("%d.%m.%Y %H:%M")}'\
                          f'\n    название: {cost_name} \n    сумма: {num_with_delimiters(num=cost_amount)} руб.\n'
            output_text += '\n' + current_total_month_costs_by_users()

            logging.info('[x] Data added to database')
        else:
            logging.error('Incorrect Type/Value of data to be put in database - skipping...')
            output_text = 'Некорректные данные: должны быть в формате: (текст) (целое число)'

    except Exception as e:
        output_text = '!ERR! Ошибка записи данных в базу'
        logging.error(f'Error while writing to database: {e}')
    finally:
        session.close()
        logging.debug('Postgres session closed')

    await message.answer(output_text)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=False)
