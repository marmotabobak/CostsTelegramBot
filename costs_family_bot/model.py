from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, BigInteger, Text, Integer, DateTime
from pydantic import BaseModel
from typing import List


Base = declarative_base()


class TelegramUserConfig(BaseModel):
    tg_bot_user_id: int
    tg_bot_user_name: str


class TelegramConfig(BaseModel):
    tg_bot_api_token: str
    tg_bot_admins: List[int]
    tg_bot_users: List[TelegramUserConfig]


class DatabaseConfig(BaseModel):
    host: str
    port: int
    user: str
    password: str
    db_name: str


class Config(BaseModel):
    db: DatabaseConfig
    telegram: TelegramConfig


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