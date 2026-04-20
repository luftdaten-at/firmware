import json
import storage

from tz_format import format_iso8601_tz

# Define the log levels
LOG_LEVELS = {
    'DEBUG': 0,
    'INFO': 1,
    'WARNING': 2,
    'ERROR': 3,
    'CRITICAL': 4
}


def _configured_log_threshold():
    """Minimum level from ``settings.toml`` ``LOG_LEVEL`` (default DEBUG). Unknown → DEBUG."""
    try:
        from config import Config

        raw = Config.settings.get('LOG_LEVEL', 'DEBUG')
    except Exception:
        return 0
    if raw is None:
        return 0
    name = str(raw).strip().upper()
    return LOG_LEVELS.get(name, 0)


class SimpleLogger:
    def __init__(self):
        self.log_list = []

    def log(self, message, level='DEBUG'):
        level_num = LOG_LEVELS.get(level, 0)
        if level_num >= _configured_log_threshold():
            formatted_time = format_iso8601_tz()
            
            log_message = f"{formatted_time} [{level}] {message}"
            print(log_message)  # Print to console or handle as needed

            log_entry = {
                'time': formatted_time,
                'level': level_num,
                'message': message
            }

            self.save(log_entry)

    def save(self, data):
        self.log_list.append(data)
        '''
        storage.remount('/', False)
        with open('json_queue/tmp_log.txt', 'a') as f:
            print(json.dumps(data), file=f)
        storage.remount('/', True)
        '''

    def debug(self, *args):
        self.log(self.format_message(*args), 'DEBUG')

    def info(self, *args):
        self.log(self.format_message(*args), 'INFO')

    def warning(self, *args):
        self.log(self.format_message(*args), 'WARNING')

    def error(self, *args):
        self.log(self.format_message(*args), 'ERROR')

    def critical(self, *args):
        self.log(self.format_message(*args), 'CRITICAL')

    def format_message(self, *args):
        """Format the message from a list of arguments with spaces."""
        return ' '.join(str(arg) for arg in args)

# Global logger; threshold from ``Config.settings['LOG_LEVEL']`` (see ``config.py``).
logger = SimpleLogger()
