import argparse
import logging
import traceback
import sys
from pathlib import Path

from langchain_openai import ChatOpenAI

from local_config import global_config
from src.data_objects.resume import Resume
from src.logging import logger
from src.utils.config_validator import ConfigValidator, ConfigError
from src.utils.llm_utils.llm_logger import LLMLogger
from src.utils.llm_utils.open_ai_action_wrapper import OpenAiActionWrapper
from src.utils.web_scrapping.job_boards.linked_in_board_browser import LinkedInBoardBrowser
from src.utils.web_scrapping.web_driver_factory import WebDriverFactory

handler = logging.StreamHandler(sys.stdout)

root_logger = logging.getLogger("root_logger")
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(handler)

def load_config():
    try:
        # Define and validate the data folder
        data_folder = Path("data_folder")
        secrets_file, config_file, plain_text_resume_file, output_folder = ConfigValidator.validate_data_folder(data_folder)

        # Validate configuration and secrets
        config = ConfigValidator.validate_config(config_file)
        secrets = ConfigValidator.validate_secrets(secrets_file)
        global_config.API_KEY = secrets["llm_api_key"]
        global_config.LINKEDIN_EMAIL = secrets["linkedin_email"]
        global_config.LINKEDIN_PASSWORD = secrets["linkedin_password"]

        with open(plain_text_resume_file, "r", encoding="utf-8") as file:
            plain_text_resume = file.read()
            global_config.RESUME = Resume(plain_text_resume)

        # Prepare parameters
        config["uploads"] = ConfigValidator.get_uploads(plain_text_resume_file)
        config["outputFileDirectory"] = output_folder
        return config

    except ConfigError as ce:
        root_logger.error(f"Configuration error: {ce}")
        root_logger.error(
            "Refer to the configuration guide for troubleshooting on this projects github readme!"
        )
    except FileNotFoundError as fnf:
        root_logger.error(f"File not found: {fnf}")
        root_logger.error("Ensure all required files are present in the data folder.")
    except RuntimeError as re:
        root_logger.error(f"Runtime error: {re}")
        root_logger.debug(traceback.format_exc())
    except Exception as e:
        root_logger.exception(f"An unexpected error occurred: {e}")

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
        root_logger.error("Must provide different positions you would like us to attempt to apply jobs for you")
        return

    # In the future set the model based on a config that is passed in.
    global_config.AI_MODEL = OpenAiActionWrapper(
        ChatOpenAI(
            model_name=global_config.LLM_MODEL, openai_api_key=global_config.API_KEY, temperature=global_config.LLM_TEMPERATURE
        ),
        enable_logging=True
    )

    linked_in_board_browser = LinkedInBoardBrowser(driver=WebDriverFactory().get_chrome_web_driver())

    try:
        # Attempt to go to linkedin and search
        linked_in_board_browser.do_search(config["positions"], config)
        job_postings = linked_in_board_browser.extract_and_evaluate_jobs(global_config.RESUME, global_config.AI_MODEL, config["max_jobs_apply_to"])
        most_likely_postings = sorted(job_postings, key=lambda posting: posting.interview_chance, reverse=True)
        for posting in most_likely_postings:
            root_logger.info(f"Found a job posting with url {posting.url_link} and we have a {posting.interview_chance} of getting an interview and {posting.hired_chance} of getting hired")
    finally:
        linked_in_board_browser.close_browser()

    root_logger.info(f"Finished running the applicaiton and spent a total of {LLMLogger.total_run_cost} credits")


if __name__ == "__main__":
    main()
