import logging

from src.data_objects.application_job_configs import ApplicationJobConfigs
from src.data_objects.job_application_profile import JobApplicationProfile
from src.data_objects.job_posting import JobPosting
from src.data_objects.resume import Resume
from src.utils.web_scrapping.job_boards.job_board_browser import JobBoardBrowser
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

class LinkedInBoardBrowser(JobBoardBrowser):
    '''
    TODO add comments explaining any nuiances on how this works.
    '''

    default_url = "https://www.linkedin.com/jobs/"
    search_box_xpath = '//*[starts-with(@id, "jobs-search-box-keyword-id-ember")]'
    logger = logging.getLogger("linked_in_board_browser")

    def __init__(self, driver):
        super().__init__(driver)
        '''
        TODO Setup the driver so that it can make calls to Linkedin and actions on it. 
        '''
        self.driver.get(self.default_url)
        # Sleep for 1 second so we can let Javascript run and get any further info needed for the client
        time.sleep(1)


    def do_search(self, search_terms: str, preferences: {}):
        search_input = self.driver.find_element(By.XPATH, self.search_box_xpath)
        if not search_input:
            self.logger.error("Unable to find search input on linkedin browser! xpath that was attempted was: " + self.search_box_xpath)
        search_input.send_keys(search_terms)

        #Press enter to do the search and save us the trouble of having to press the search button.
        search_input.send_keys(Keys.RETURN)

        time.sleep(3)

        self.logger.debug("Search has been applied")

    def extract_and_evaluate_jobs(self, resume: Resume, ai_model) -> list[JobPosting]:
        '''
        Attempts to evaluate the job board which the webdriver should be connected to and evaluates each job get a posting
        as well as an AI evalutaion score on how likely that we are to fit that jobs description.
        :param resume: information about the applica    nt
        :param ai_model: what AI model will we be asking questions of
        :return: array of Job Posting objects
        '''
        pass

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