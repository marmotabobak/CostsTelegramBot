# TODO: write autotests
# TODO: Refactor with classes in outer modules (how to pass dp and how not to use global postgres_engine)
import yaml
import logging
import datetime

from aiogram import Bot, Dispatcher, types, executor
from sqlalchemy import select, desc, func

from model import Config, Cost
from postgres import PostgresEngine


logging.basicConfig(
    format='[%(asctime)s | %(levelname)s]: %(message)s',
    datefmt='%m.%d.%Y %H:%M:%S',
    level=logging.INFO
)

CONFIG_FILE_PATH = '../configs/dev.yml'

logging.info(f'Starting service with config {CONFIG_FILE_PATH}')
with open(CONFIG_FILE_PATH) as f:
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
except Exception:
    logging.error(f'[x] Error while initializing Postgres engine')
    raise


def first_day_of_current_month() -> datetime:
    return datetime.datetime(
        year=datetime.datetime.now().year,
        month=datetime.datetime.now().month,
        day=1
    )


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
            output_text += f'\n    {tg_user_name}: {cost_amount} руб.'

        return output_text

    except Exception as e:
        logging.error(f'Error while reading database: {e}')
        return('!ERR! Ошибка получения данных')
    finally:
        session.close()
        logging.debug('Postgres session closed')


@dp.message_handler(commands=['start', 'help'])
async def process_start_command(message: types.Message) -> None:
    global TG_USERS

    output_text = 'Введи расход в формате: продукты 500 либо выбери пункт меню'
    markup = types.reply_keyboard.ReplyKeyboardMarkup(row_width=1)
    markup.add(types.KeyboardButton('Мои расходы в этом месяце'))
    for tg_user_id, tg_user_name in TG_USERS.items():
        if tg_user_id != message.from_user.id:
            markup.add(types.KeyboardButton('Расходы ' + tg_user_name + ' в этом месяце'))
    await message.answer(output_text, reply_markup=markup)


@dp.message_handler(regexp=r'.+асходы .*в этом месяце')
async def view_my_costs(message: types.Message) -> None:

    global postgres_engine
    global TG_USERS

    output_text = ''

    try:
        if 'Мои расходы' in message.text:
            user_tg_id = message.from_user.id
        else:
            another_user_name = message.text.split('Расходы ')[1].split(' в этом месяце')[0]
            user_tg_id = int(next(filter(lambda x: TG_USERS[x] == another_user_name, TG_USERS.keys())))
    except IndexError as e:
        user_tg_id = None
        logging.error(f'Error while parsing button text for user_name: {e}')
        output_text = f'!ERR! Ошибка определения имени пользователя'
    except Exception:
        raise

    if user_tg_id:
        output_text = ''
        current_total = 0

        session = postgres_engine.session()
        try:
            stmt = select(Cost).order_by(desc(Cost.ts)).where(
                Cost.user_telegram_id == user_tg_id
            ).where(
                Cost.ts >= first_day_of_current_month()
            )

            for cost in session.scalars(stmt):
                output_text += f'{cost.ts.strftime("%d")} {cost.name} {cost.amount}\n'
                current_total += cost.amount

            output_text += f'Всего за месяц: {current_total}'
        except Exception as e:
            logging.error(f'Error while reading database: {e}')
            output_text += f'!ERR! Ошибка чтения из базы данных'
        finally:
            session.close()
            logging.debug('Postgres session closed')

    await message.answer(output_text)


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

    if cost_name and cost_amount:
        session = postgres_engine.session()
        try:
            session.add(
                Cost(
                    name=cost_name,
                    amount=cost_amount,
                    ts=datetime.datetime.now(),
                    message_text=message.from_user.id,
                    user_telegram_id=message.from_user.id
                )
            )
            session.commit()

            output_text = f'Внесены данные:\n    время: {datetime.datetime.now().strftime("%d.%m.%Y %H:%M")}'\
                          f'\n    название: {cost_name} \n    сумма: {cost_amount} руб. \n'
            output_text += '\n\n' + current_total_month_costs_by_users()

            logging.info('[x] Data added to database')
        except Exception as e:
            output_text = '!ERR! Ошибка записи данных в базу'
            logging.error(f'Error while writing to database: {e}')
        finally:
            session.close()
            logging.debug('Postgres session closed')

    else:
        logging.error('Incorrect Type/Value of data to be put in database - skipping...')
        output_text = 'Некорректные данные: должны быть в формате: (текст) (целое число)'

    await message.answer(output_text)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=False)