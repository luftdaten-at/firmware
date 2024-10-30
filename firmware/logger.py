import logging
import time

# Step 1: Define the send_status function
def send_status(timestamp, level, message):
    # TODO: send data to API
    # This is where you can handle the status messages
    print(f"Status Update - Time: {timestamp}, Level: {level}, Message: {message}")

# Step 2: Create a custom logging handler
class StatusLoggingHandler(logging.Handler):
    def emit(self, record):
        # Get the log message details
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created))
        level = record.levelname
        message = record.getMessage()
        
        # Call the send_status function
        send_status(timestamp, level, message)

# Step 3: Create a logger instance
logger = logging.getLogger("GlobalLogger")
logger.setLevel(logging.DEBUG)  # Set the logging level

# Add the custom handler to the logger
status_handler = StatusLoggingHandler()
logger.addHandler(status_handler)

file_handler = logging.FileHandler('log.txt')
logger.addHandler(file_handler)
