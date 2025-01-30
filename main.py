import argparse
import logging
import os
import traceback
import sys
from pathlib import Path

import yaml
from langchain_openai import ChatOpenAI
from local_config import global_config, LocalLogging
from src.data_objects.job_posting import JobPosting
from src.data_objects.resume import Resume
from src.utils.config_validator import ConfigValidator, ConfigError
from src.utils.llm_utils.llm_logger import LLMLogger
from src.utils.llm_utils.open_ai_action_wrapper import OpenAiActionWrapper
from src.utils.web_scrapping.hcm.vector_store_hcm_crawler import VectorStoreHcmCrawler
from src.utils.web_scrapping.job_boards.linked_in_board_browser import LinkedInBoardBrowser
from src.utils.web_scrapping.web_driver_factory import WebDriverFactory


from langchain_community.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

main_logger = LocalLogging.get_local_logger("main_script.py")

def load_config():
    try:
        # Define and validate the data folder
        data_folder = Path("data_folder")
        secrets_file, config_file, plain_text_resume_file, output_folder = ConfigValidator.validate_data_folder(data_folder)

        # Validate configuration and secrets
        config = ConfigValidator.validate_config(config_file)
        secrets = ConfigValidator.validate_secrets(secrets_file)
        global_config.API_KEY = secrets["llm_api_key"]
        # NEEDED for some Open AI libraries to be on the OS path like Embeddings
        os.environ["OPENAI_API_KEY"] = global_config.API_KEY
        global_config.LINKEDIN_EMAIL = secrets["linkedin_email"]
        global_config.LINKEDIN_PASSWORD = secrets["linkedin_password"]
        global_config.DEFAULT_EMAIL = secrets["default_account_email"]
        global_config.DEFAULT_PASSWORD = secrets["default_account_password"]

        with open(plain_text_resume_file, "r", encoding="utf-8") as file:
            plain_text_resume = file.read()
            global_config.RESUME = Resume(plain_text_resume)

        # Prepare parameters
        config["uploads"] = ConfigValidator.get_uploads(plain_text_resume_file)
        config["outputFileDirectory"] = output_folder
        return config

    except ConfigError as ce:
        main_logger.error(f"Configuration error: {ce}")
        main_logger.error(
            "Refer to the configuration guide for troubleshooting on this projects github readme!"
        )
    except FileNotFoundError as fnf:
        main_logger.error(f"File not found: {fnf}")
        main_logger.error("Ensure all required files are present in the data folder.")
    except RuntimeError as re:
        main_logger.error(f"Runtime error: {re}")
        main_logger.debug(traceback.format_exc())
    except Exception as e:
        main_logger.exception(f"An unexpected error occurred: {e}")

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
        main_logger.error("Must provide different positions you would like us to attempt to apply jobs for you")
        return

    # In the future set the model based on a config that is passed in.
    global_config.AI_MODEL = OpenAiActionWrapper(
        ChatOpenAI(
            model_name=global_config.LLM_MODEL, openai_api_key=global_config.API_KEY, temperature=global_config.LLM_TEMPERATURE
        ),
        enable_logging=True
    )

    test_posting = JobPosting(html_string="",
                              url_link= "https://jobs.lever.co/kochava/1b4a3c3d-e05b-494f-ac40-9f5aefbe0733",
                              interview_chance=100, hired_chance=100)
    test_crawler = VectorStoreHcmCrawler(driver=WebDriverFactory().get_chrome_web_driver(), posting=test_posting)
    test_crawler.do_application_flow()

    #linked_in_board_browser = LinkedInBoardBrowser(driver=WebDriverFactory().get_chrome_web_driver())

    # try:
    #     # Attempt to go to linkedin and search
    #     linked_in_board_browser.do_search(config["positions"], config)
    #     job_postings = linked_in_board_browser.extract_and_evaluate_jobs(global_config.RESUME, global_config.AI_MODEL, config["max_jobs_apply_to"])
    #     most_likely_postings = sorted(job_postings, key=lambda posting: posting.interview_chance, reverse=True)
    #     for posting in most_likely_postings:
    #         main_logger.info(f"Found a job posting with url {posting.url_link} and we have a {posting.interview_chance} of getting an interview and {posting.hired_chance} of getting hired")
    # finally:
    #     linked_in_board_browser.close_browser()

    main_logger.info(f"Finished running the applicaiton and spent a total of {LLMLogger.total_run_cost} credits")


if __name__ == "__main__":
    main()
