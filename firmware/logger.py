import time
import storage
import json

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

    def log(self, *message, level='DEBUG'):
        message = ' '.join(str(x) for x in message)
        level_num = LOG_LEVELS.get(level, 0)
        if level_num >= self.level:
            # Get current time in the desired format
            current_time = time.localtime()
            formatted_time = f"{current_time.tm_year:04}-{current_time.tm_mon:02}-{current_time.tm_mday:02}T{current_time.tm_hour:02}:{current_time.tm_min:02}:{current_time.tm_sec:02}.000Z"
            
            log_message = f"{formatted_time} [{level}] {message}"
            print(log_message)  # Print to console or handle as needed

            log_entry = {
                'time': formatted_time,
                'level': level,
                'message': message
            }

            storage.remount('/', False)
            with open('log.txt', 'a') as f:
                print(json.dumps(log_entry), file=f)
            storage.remount('/', False)

    def debug(self, message):
        self.log(message, 'DEBUG')

    def info(self, message):
        self.log(message, 'INFO')

    def warning(self, message):
        self.log(message, 'WARNING')

    def error(self, message):
        self.log(message, 'ERROR')

    def critical(self, message):
        self.log(message, 'CRITICAL')

# Create a global logger instance
logger = SimpleLogger(level='DEBUG')  # Set your desired default log level
