import logging
from logging.handlers import RotatingFileHandler


class Logger:
    def __init__(self, log_file_path, log_level=logging.INFO):
        self.logger = logging.getLogger()
        self.logger.setLevel(log_level)

        # Create a rotating file handler to write logs to a file with UTF-8 encoding
        self.log_file_path = log_file_path
        self.file_handler = RotatingFileHandler(
            filename=self.log_file_path,
            maxBytes=1024 * 1024 * 1024,  # 1 GB
            backupCount=10
        )
        self.file_handler.setLevel(log_level)

        # Define the log format
        log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # Set the format for the file handler
        self.file_handler.setFormatter(log_format)

        # Add the file handler to the logger
        self.logger.addHandler(self.file_handler)

    def info(self, message):
        self.logger.info(message)

    def debug(self, message):
        self.logger.debug(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)
