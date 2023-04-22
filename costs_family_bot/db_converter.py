import yaml
import logging

from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, BigInteger, Text, Integer, DateTime, select

from postgres import PostgresEngine
from model import Config


logging.basicConfig(
    format='[%(asctime)s | %(levelname)s]: %(message)s',
    datefmt='%m.%d.%Y %H:%M:%S',
    level=logging.INFO
)


Base = declarative_base()


with open('../configs/dev.yml') as f:
    data = yaml.safe_load(f)

config = Config.parse_obj(data)

postgres_engine = PostgresEngine(config.db)

session = postgres_engine.session()


class Cost(Base):
    __tablename__ = 'costs'
    __table_args__ = {'schema': 'family_cost_bot'}

    id = Column('cost_id', BigInteger, quote=False, primary_key=True)
    name = Column('cost_name', Text, quote=False)
    amount = Column('cost_amount', Integer, quote=False)
    ts = Column('cost_ts', DateTime, quote=False)
    message_text = Column('cost_message_text', Text, quote=False)
    user_telegram_id = Column('user_tg_id', Integer, quote=False)


class Message(Base):
    __tablename__ = 'messages'
    __table_args__ = {'schema': 'family_cost_bot'}

    id = Column('message_id', BigInteger, quote=False, primary_key=True)
    text = Column('message_text', Text, quote=False)
    ts = Column('message_ts', DateTime, quote=False)
    user_telegram_id = Column('user_tg_id', Integer, quote=False)


postgres_engine.drop_and_create_all_tables()


class CostOld(Base):
    __tablename__ = 'costs'

    id = Column('cost_id', BigInteger, quote=False, primary_key=True)
    name = Column('cost_name', Text, quote=False)
    amount = Column('cost_amount', Integer, quote=False)
    ts = Column('cost_datetime', DateTime, quote=False)
    message_text = Column('cost_message', Text, quote=False)
    user_telegram_id = Column('user_tg_id', Integer, quote=False)


class MessageOld(Base):
    __tablename__ = 'messages'

    id = Column('message_id', BigInteger, quote=False, primary_key=True)
    text = Column('message_text', Text, quote=False)
    ts = Column('message_datetime', DateTime, quote=False)
    user_telegram_id = Column('user_tg_id', Integer, quote=False)


stmt = select(CostOld)
costs_to_add = []

for data in session.scalars(stmt):

    session.add(
        Cost(
            name=data.name,
            amount=data.amount,
            ts=data.ts,
            message_text=data.message_text,
            user_telegram_id=int(data.user_telegram_id)
        )
    )


stmt = select(MessageOld)
messages_to_add = []

for data in session.scalars(stmt):

    session.add(
        Message(
            ts=data.ts,
            text=data.text,
            user_telegram_id=int(data.user_telegram_id)
        )
    )

session.commit()
session.close()
