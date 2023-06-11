import logging
import datetime
from typing import List
import random

from sqlalchemy.orm import Session
from sqlalchemy import create_engine

from model import DatabaseConfig, Base, Cost


class PostgresEngine:

    def __init__(self, config: DatabaseConfig) -> None:
        self._config = config
        try:
            self._engine = create_engine(
                f'postgresql://{self._config.db_name}:{self._config.password}@{self._config.host}:{self._config.port}',
                echo=True
            )
            self._engine.connect()
            logging.info('[x] Postgres engine created')
        except Exception:
            logging.error('Error while creating Postgres Engine')
            raise

    def session(self) -> Session:
        try:
            result = Session(bind=self._engine)
            logging.debug('[x] Postgres session created')
            return result
        except Exception as e:
            logging.error(f'Error while creating Postgres session: {e}')
            raise

    def drop_all_tables(self) -> None:
        if input('SURE TO DELETE ALL DATA? Print YES if so: ') == 'YES':
            try:
                Base.metadata.drop_all(self._engine)
                logging.info('[x] All service tables dropped')
            except Exception as e:
                logging.error(f'Error while dropping tables: {e}')

    def create_all_tables(self) -> None:
        try:
            Base.metadata.create_all(self._engine)
            logging.info('[x] All service tables created')
        except Exception as e:
            logging.error(f'Error while creating tables: {e}')

    def drop_and_create_all_tables(self) -> None:
        self.drop_all_tables()
        self.create_all_tables()

    def generate_data(self, from_date: datetime, to_date: datetime, user_tg_ids: List[int]):
        session = self.session()
        while from_date <= to_date:
            for user_tg_id in user_tg_ids:
                session.add(
                    Cost(
                        name='test cost',
                        amount=random.randint(10, 1000),
                        ts=from_date,
                        message_text='test message',
                        user_telegram_id=user_tg_id
                    )
                )
            from_date += datetime.timedelta(days=1)
        session.commit()






