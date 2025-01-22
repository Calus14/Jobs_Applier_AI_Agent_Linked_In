import json
import re
from abc import ABC, abstractmethod

from local_config import global_config
from src.data_objects.application_job_configs import ApplicationJobConfigs
from src.data_objects.job_application_profile import JobApplicationProfile
from src.data_objects.job_posting import JobPosting
from src.data_objects.resume import Resume
from src.utils.web_scrapping.web_driver_factory import WebDriverFactory

'''
Base class that needs to be extended by job board specific browsers. Each browser should be holding a web-driver that
will allow us to interact with the job board to advance the client state and get information about the jobs.

Note: Purposely abstract so no implementation of __init__
'''
class JobBoardBrowser(ABC):

    #Used to just get the job board name to snake case to match our file naming schema
    snake_case_pattern = re.compile(r'(?<!^)(?=[A-Z])')

    @abstractmethod
    def __init__(self, driver):
        self.driver = driver
        '''
        First initializer will call the web driver to intialize selenium (This is to account for future sites that use JS to load their html)
        '''
        pass

    @abstractmethod
    def do_search(self, search_terms: str, preferences: {}):
        '''
        Methot that will take a list of terms to search on, as well as a dictionary of preferences for different fields
        that the job board might be able to search on. Then applies these to the client's current session and executes a search
        :param search_terms: terms that need to be searched directly only
        :param preferences: dictionary of job board specific preferences E.G. "remote": true "hybrid":false salary:100

        :return:
        '''
        pass

    @abstractmethod
    def extract_and_evaluate_jobs(self, resume: Resume, ai_model, jobs_to_find = 10) -> list[JobPosting]:
        '''
        Attempts to evaluate the job board which the webdriver should be connected to and evaluates each job get a posting
        as well as an AI evalutaion score on how likely that we are to fit that jobs description.
        :param resume: information about the applicant
        :param ai_model: what AI model will we be asking questions of
        :return: array of Job Posting objects
        '''
        pass

    # Takes a web element and builds a site Item Object
    @abstractmethod
    def create_application_job(self, postings: list[JobPosting], resume:  Resume, job_prefs: JobApplicationProfile) -> list[ApplicationJobConfigs]:
        '''
        Sorts through all job postings and if they meet the configured settings and your job preferences. If so then creates
        objects that hold all information required to automatically apply for you.
        :param postings: Objects that hold information about each job posting and the likely hood that we can get it.
        :param resume: information about the applicant
        :param job_prefs: preferences the user has for jobs
        :return: list of objects that hold all information required to apply to a job
        '''
        pass

    def save_job_board_cookies(self):
        '''
        Called automatically before closing so each time the user runs on a job board their previous cookies are saved
        :param board_name: the name of the board that the cookies are for
        :return:
        '''
        cookies = self.driver.get_cookies()
        board_name = self.snake_case_pattern.sub('_', type(self).__name__).lower()
        cookies_file = global_config.LOG_OUTPUT_FILE_PATH / f"{board_name}_cookies.json"

        # Save cookies to a file
        with open(self.cookies_file, "w") as file:
            json.dump(cookies, file)

    def load_job_board_cookies(self):
        '''
        Utility method that will apply cookies that were saved in previous session
        '''
        board_name = self.snake_case_pattern.sub('_', type(self).__name__).lower()
        cookies_file = global_config.LOG_OUTPUT_FILE_PATH / f"{board_name}_cookies.json"
        try:
            with open(cookies_file, "r") as file:
                cookies = json.load(file)
                for cookie in cookies:
                    if "expiry" in cookie:
                        cookie["expiry"] = int(cookie["expiry"])
                    self.driver.add_cookie(cookie)

                self.driver.refresh()
        except:
            self.logger.info("Could not apply cookies as no cookies files found from previous run.")
            return

    def close_browser(self):
        self.save_job_board_cookies()
        self.driver.close()
        self.driver.quit()
