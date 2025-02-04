import os
import traceback
from typing import List

from anyio import Path

from src.config.local_config import LocalConfig
from src.config.local_logging import LocalLogging
from src.data_objects.job_posting import JobPosting
from src.data_objects.resume import Resume
from src.utils.config_validator import ConfigValidator, ConfigError
from src.utils.web_scrapping.hcm.hcm_crawler import HcmCrawler
from src.utils.web_scrapping.job_boards.job_board_browser import JobBoardBrowser


class FindJobsForUser:
    '''
    This class represents the flow, checks and logging, that this application will take when attempting to "find jobs
    for a given user.
    Although it is not currently handling multiple job boards or multiple scraping/filling techniques, this is meant
    to be configurable so that we can dependency inject any given settings that best fit the user or the client who wants
    this application ran.
    '''
    def __init__(self, board_browser: JobBoardBrowser, ai_model):
        self.board_browser = board_browser
        self.ai_model = ai_model
        self.jobs_found_for_user: List[JobPosting] = []
        self.logger = LocalLogging.get_local_logger("FindJobsForUser")
        self.local_config = LocalConfig()

    def configure_for_user(self, secrets_file: Path, resume_file: Path, work_pref_file: Path):
        '''
        Takes 3 given paths that point to location of files to be used on this run, then creates a local config that will
        be used for this entire process

        :param secrets_path: path to file that contains user provided AI secrets that they will be charged with
        :param resume_path: path to the user provided information about their work history
        :param work_pref_path: path to user provided preferences for jobs to find them
        '''
        if not secrets_file or not resume_file or not work_pref_file:
            self.logger.error("Cannot start process to FindJobsForUser because one of the configuration files was not provided!")
            raise Exception("Not all config files provided")

        try:
            # Validate configuration and secrets
            config = ConfigValidator.validate_config(work_pref_file)
            secrets = ConfigValidator.validate_secrets(secrets_file)
            self.local_config.API_KEY = secrets["llm_api_key"]

            # TODO NEEDED for some Open AI libraries to be on the OS path like Embeddings, so if your thinking of scaling this horizontally need to find a way
            # for each process to use their own embedding using their own api key
            os.environ["OPENAI_API_KEY"] = self.local_config.API_KEY
            self.local_config.LINKEDIN_EMAIL = secrets["linkedin_email"]
            self.local_config.LINKEDIN_PASSWORD = secrets["linkedin_password"]
            self.local_config.DEFAULT_EMAIL = secrets["default_account_email"]
            self.local_config.DEFAULT_PASSWORD = secrets["default_account_password"]
            self.local_config.WORK_PREFS = config

            with open(resume_file, "r", encoding="utf-8") as file:
                plain_text_resume = file.read()
                self.local_config.RESUME = Resume(plain_text_resume)
        except ConfigError as ce:
            self.logger.error(f"Configuration error: {ce}")
            self.logger.error(
                "Refer to the configuration guide for troubleshooting on this projects github readme!"
            )
        except FileNotFoundError as fnf:
            self.logger.error(f"File not found: {fnf}")
            self.logger.error("Ensure all required files are present in the data folder.")
        except RuntimeError as re:
            self.logger.error(f"Runtime error: {re}")
            self.logger.debug(traceback.format_exc())
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred: {e}")

    def find_jobs_for_user(self) -> List[JobPosting]:
        try:
            # Attempt to go to linkedin and search
            self.board_browser.do_search(self.local_config.WORK_PREFS["positions"], self.local_config.WORK_PREFS)
            job_postings = self.board_browser.extract_and_evaluate_jobs(self.local_config.RESUME, self.ai_model, self.local_config.WORK_PREFS["max_jobs_apply_to"])
            most_likely_postings = sorted(job_postings, key=lambda posting: posting.interview_chance, reverse=True)
            for posting in most_likely_postings:
                self.logger.info(f"Found a job posting with url {posting.url_link} and we have a {posting.interview_chance} of getting an interview and {posting.hired_chance} of getting hired")
        finally:
            self.board_browser.close_browser()