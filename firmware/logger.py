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

class SimpleLogger:
    def __init__(self, level='DEBUG'):
        self.level = LOG_LEVELS.get(level, 0)  # Default to DEBUG level
        self.log_list = []

    def log(self, message, level='DEBUG'):
        level_num = LOG_LEVELS.get(level, 0)
        if level_num >= self.level:
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

# Create a global logger instance
logger = SimpleLogger(level='DEBUG')  # Set your desired default log level
