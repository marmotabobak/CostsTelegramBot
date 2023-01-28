import psycopg2

import settings, model

db_settings = settings.AppSettings(model.Modules.db).settings
print(db_settings)

try:
    postgres_connection = psycopg2.connect(
        user=db_settings.user,
        password=db_settings.psswd,
        host=db_settings.host,
        port=db_settings.port
    )
    posgtres_cursor = postgres_connection.cursor()
    print('--- INFO --- Подулючились к БД для инициализации:', postgres_connection)
    query = '''
        CREATE TABLE IF NOT EXISTS costs (
            cost_id SERIAL PRIMARY KEY,
            cost_name VARCHAR(255),
            cost_amount INT,
            cost_datetime TIMESTAMP,
            cost_message VARCHAR(255),
            user_tg_id VARCHAR(50));
        '''
    posgtres_cursor.execute(query)
    postgres_connection.commit()
    print('--- INFO --- Таблица costs успешно создана (либо существует)')
    query = '''
        CREATE TABLE IF NOT EXISTS messages (
            message_id SERIAL PRIMARY KEY,
            message_text VARCHAR(255),
            message_datetime TIMESTAMP,
            user_tg_id varchar(50));
        '''
    posgtres_cursor.execute(query)
    postgres_connection.commit()
    print('--- INFO --- Таблица messages успешно создана (либо существует)')
except:
    print('--- ERROR --- Проблема при создании инициализации таблицы costs и/или messages')

try:
    posgtres_cursor.close()
    postgres_connection.close()
    print('--- INFO --- Соединение с БД после инициализации успешно закрыто')
except:
    print('--- ERROR --- Проблемы с закрытием соединения с БД в процессе инициализации БД')
