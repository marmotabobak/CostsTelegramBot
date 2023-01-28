import enum
import yaml
import logging

import model

class Modules(enum.Enum):
    bot = 'bot'
    db = 'db'

class AppSettings:
    def __init__(self, module: Modules):
        # TODO: parse input command line args here
        CONFIG_DIR = 'settings/'
        CONFIG_FILE_PATTERN = '_settings.yml'
        CONFIG_MODULES = {
            'bot': model.TgBotSettings,
            'db': model.PostgresSettings
        }

        settings_file_name = CONFIG_DIR + module.value + CONFIG_FILE_PATTERN
        with open(settings_file_name, 'r') as settings_file:
            settings_dict = yaml.safe_load(settings_file)
            try:
                settings = CONFIG_MODULES[module.value].parse_obj(settings_dict)
                logging.info(f'SERVICE: {module.value} config loaded from file: {settings_file_name}')
            except ValueError as e:
                logging.error(f'SERVICE: Error while loading {module.value} config from file')
                raise e
        self.settings = settings