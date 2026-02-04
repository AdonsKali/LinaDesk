import json
from paths import Path
from configparser import ConfigParser
load_ini_config = lambda path: ConfigParser().read(path)


def load_json_config() -> dict:
    
    path = Path("config.json")
    with open(path, 'r', encoding='utf-8') as file:
        data = json.load(file)
        
    return data

json_config: dict = load_json_config()


CONFIG: dict = load_json_config()
global current_language
current_language = CONFIG['current_language']
        
global lang
lang = CONFIG['translates'][current_language]
def _(key: str):
    """ Return translates the key object by CURRENT_LANGUAGE """
    return lang[key] 