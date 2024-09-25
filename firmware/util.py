from lib.cptoml import put
from storage import remount, fetch

class Util:
    @staticmethod
    def write_to_settings(data: dict):
        remount('/', False)
        for k, v in data.items():
            try:
                put(k, v, toml='settings.toml')
            except Exception as e:
                print(f"can't write {k}: {v}, to settings.toml")
                print(e)
    @staticmethod
    def get_from_settings(keys: list) -> dict:
        remount('/', False)
        data = {}
        for k in keys:
            try:
                data[k] = fetch(k, toml='settings.toml')
            except Exception as e:
                print(f"can't read {k}, form settings.toml")
                print(e)

        return data

    @staticmethod
    def check_if_configs_are_set(keys: list):
        remount('/', False)
        for k in keys:
            try:
                fetch(k, toml='settings.toml')
            except:
                return False
        return True
