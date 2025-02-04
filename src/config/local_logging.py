import logging

LOG_TO_FILE = True
LOG_TO_CONSOLE = True
LOG_LEVEL = logging.INFO

class LocalLogging():
    @staticmethod
    def get_local_logger(logger_name: str):
        logger = logging.getLogger(logger_name)
        logger.setLevel(LOG_LEVEL)  # Set the logging level to INFO

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        if LOG_TO_FILE:
            file_handler = logging.FileHandler('local_logs.log', 'w')  # Log to a file named 'app.log'
            file_handler.setLevel(LOG_LEVEL)  # Set the file handler level to INFO
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        if LOG_TO_CONSOLE:
            console_handler = logging.StreamHandler()  # Log to the console
            console_handler.setLevel(logging.INFO)  # Set the console handler level to INFO
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        return logger
