import time
import json
import storage

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

    def log(self, message, level='DEBUG'):
        level_num = LOG_LEVELS.get(level, 0)
        if level_num >= self.level:
            # Get current time in the desired format
            current_time = time.localtime()
            formatted_time = f"{current_time.tm_year:04}-{current_time.tm_mon:02}-{current_time.tm_mday:02}T{current_time.tm_hour:02}:{current_time.tm_min:02}:{current_time.tm_sec:02}.000Z"
            
            log_message = f"{formatted_time} [{level}] {message}"
            print(log_message)  # Print to console or handle as needed

            log_entry = {
                'time': formatted_time,
                'level': level_num,
                'message': message
            }

            self.save(log_entry)

    def save(self, data):
        
        with open('write/json_queue/tmp_log.txt', 'a') as f:
            print(json.dumps(data), file=f)
        

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
