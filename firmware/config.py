from lib.cptoml import fetch

class Config:
    # startup config consistent with settings.toml
    SSID = None
    PASSWORD = None
    API_URL = None
    FIRMWARE_MAJOR = None
    FIRMWARE_MINOR = None
    FIRMWARE_PATCH = None
    PROTOCOL_VERSION = None
    MODEL = None
    MANUFACTURE_ID = None
    TEST_MODE = None

    # running config (is not saved in settings.toml)
    rtc_is_set = False
    JSON_QUEUE = 'json_queue'
    CERTIFICATE_PATH = 'certs/isrgrootx1.pem'
    API_KEY_LENGTH = 32

    @staticmethod
    def init():
        Config.TEST_MODE = fetch('TEST_MODE')
        Config.SSID = fetch('SSID')
        Config.PASSWORD = fetch('PASSWORD')
        Config.FIRMWARE_MAJOR = fetch('FIRMWARE_MAJOR')
        Config.FIRMWARE_MINOR = fetch('FIRMWARE_MINOR')
        Config.FIRMWARE_PATCH = fetch('FIRMWARE_PATCH')
        Config.PROTOCOL_VERSION = fetch('PROTOCOL_VERSION')
        Config.MODEL = fetch('model')
        Config.MANUFACTURE_ID = fetch('MANUFACTURE_ID')


        if Config.TEST_MODE:
            Config.API_URL = fetch('TEST_API_URL')
        else:
            Config.API_URL = fetch('API_URL')