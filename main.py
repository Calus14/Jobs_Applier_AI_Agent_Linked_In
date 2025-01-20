import argparse
import traceback
from pathlib import Path

from local_config import global_config
from src.logging import logger
from src.utils.config_validator import ConfigValidator, ConfigError
from src.utils.web_scrapping.job_boards.linked_in_board_browser import LinkedInBoardBrowser
from src.utils.web_scrapping.web_driver_factory import WebDriverFactory

def load_config():
    try:
        # Define and validate the data folder
        data_folder = Path("data_folder")
        secrets_file, config_file, plain_text_resume_file, output_folder = ConfigValidator.validate_data_folder(data_folder)

        # Validate configuration and secrets
        config = ConfigValidator.validate_config(config_file)
        global_config.API_KEY = ConfigValidator.validate_secrets(secrets_file)

        # Prepare parameters
        config["uploads"] = ConfigValidator.get_uploads(plain_text_resume_file)
        config["outputFileDirectory"] = output_folder

    except ConfigError as ce:
        logger.error(f"Configuration error: {ce}")
        logger.error(
            "Refer to the configuration guide for troubleshooting on this projects github readme!"
        )
    except FileNotFoundError as fnf:
        logger.error(f"File not found: {fnf}")
        logger.error("Ensure all required files are present in the data folder.")
    except RuntimeError as re:
        logger.error(f"Runtime error: {re}")
        logger.debug(traceback.format_exc())
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")

    return config

def main():
    # Create the parser
    parser = argparse.ArgumentParser(description="Application that will automatically search job boards and apply for jobs"
                                                 + " that fit your experience based on what AI thinks you are a good fit for.")
    # Add arguments
    parser.add_argument("--max-applies", type=int, help="How many jobs to apply too.", default=10)
    parser.add_argument("--max-page-depth", type=int, help="How many pages will we search for each position you list.", default=5)
    # Parse the arguments
    args = parser.parse_args()

    config = load_config()

    """Main entry point for the Job Application Bot."""


    if not config["positions"] or len(config["positions"]) == 0:
        logger.error("Must provide different positions you would like us to attempt to apply jobs for you")
        return

    # Attempt to go to linkedin and search
    linked_in_board_browser = LinkedInBoardBrowser(driver=WebDriverFactory().get_chrome_web_driver())

    linked_in_board_browser.do_search(config["positions"])

    logger.info("Successfuly searched")
    logger.info("Successfuly searched")


if __name__ == "__main__":
    main()
