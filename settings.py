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