from pydantic import BaseModel, BaseSettings
from typing import List
import enum


class Modules(enum.Enum):
    bot = 'bot'
    db = 'db'

class Config(BaseSettings):
    pass

class TgUser(Config):
    tg_bot_user_id: int
    tg_bot_user_name: str

class TgBotSettings(Config):
    tg_bot_api_token: str
    tg_bot_admins: List[int]
    tg_bot_users: List[TgUser]

    class Config:
        allow_mutation = False

class PostgresSettings(Config):
    user: str
    psswd: str
    host: str
    port: int

    class Config:
        allow_mutation = False

def load_from_config(module: Modules):
    # TODO: parse input command line args here
    CONFIG_DIR = 'settings/'
    CONFIG_FILE_PATTERN = '_settings.yml'
    CONFIG_MODULES = {
        'bot': TgBotSettings,
        'db': PostgresSettings
    }
