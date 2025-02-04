import yaml
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from selenium.common import NoSuchElementException, ElementClickInterceptedException
from typing import Tuple

from selenium.webdriver.remote.webdriver import BaseWebDriver

from src.config.local_config import global_config
from src.config.local_logging import LocalLogging
from src.data_objects.application_job_configs import ApplicationJobConfigs
from src.data_objects.job_application_profile import JobApplicationProfile
from src.data_objects.job_posting import JobPosting
from src.data_objects.resume import Resume
from src.utils.module_loader import load_module
from src.utils.web_scrapping.job_boards.job_board_browser import JobBoardBrowser
from src.utils.web_scrapping.selenium_utils import SeleniumUtils
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

class LinkedInBoardBrowser(JobBoardBrowser):
    '''
    TODO add comments explaining any nuiances on how this works.
    '''
    search_url = "https://www.linkedin.com/jobs"
    feed_url = "https://www.linkedin.com/feed"

    '''
    XPaths for element searching below
    '''
    email_xpath = '//*[@id="username"]'
    password_xpath = '//*[@id="password"]'
    sign_in_xpath = '//*/button[@type="submit"]'

    search_box_xpath = '//input[starts-with(@id, "jobs-search-box-keyword-id")]'
    location_box_xpath = '//input[starts-with(@id, "jobs-search-box-location-id")]'

    job_list_scroll_xpath = '//*/div[@class="scaffold-layout__list "]/div'
    job_list_xpath = '//*/div[@data-job-id]'

    job_details_xpath = '//*[@id="job-details"]/div'
    job_apply_link_button_xpath = '//*/div[@class="jobs-apply-button--top-card"]/button[@role="link"]'
    easy_apply_link_button_xpath = '//*/div[@class="jobs-apply-button--top-card"]/*/span[text()="Easy Apply"]'

    '''
    AI Prompt handling strings
    '''
    matching_prompt = "job_matching_prompts"
    matching_call_chance_phrase = "Chance to get a call for the position: "
    matching_hired_chance_phrase = "Chance to be hired for the position: "

    '''
    Linkedin specific info to track what "page" we are on
    '''
    linkedin_page_incrementor_string = "&start="
    linkedin_jobs_per_page = 25

    logger = LocalLogging.get_local_logger("linked_in_board_browser")
    #State variable that allows us to not try and extract jobs if we have not searched them.

    def __init__(self, driver: BaseWebDriver):
        super().__init__(driver)
        '''
        TODO Setup the driver so that it can make calls to Linkedin and actions on it. 
        '''
        self.driver.get(self.feed_url)
        self.driver.maximize_window()

        self.load_job_board_cookies()

        # Sleep for 1 second so we can let Javascript run and get any further info needed for the client
        time.sleep(1)

        #should only need to login if the cookie is expired.
        if "linkedin.com/uas/login" in self.driver.current_url:
            self._do_login_()

    def do_search(self, search_terms: str, config: {}):
        self.driver.get(self.search_url)

        time.sleep(3)
        search_input = self.driver.find_element(By.XPATH, self.search_box_xpath)
        location_input = self.driver.find_element(By.XPATH, self.location_box_xpath)
        if not search_input:
            self.logger.error("Unable to find search input on linkedin browser! xpath that was attempted was: " + self.search_box_xpath)
        self._apply_preferences_(config)
        if len(config["locations"]) == 0:
            self.logger.error("Unable to apply search because there are no locations in the work_preferences")
            raise Exception("Work_preferences needs to list at least 1 work location to search in.")
        elif len(config["locations"]) > 1:
            self.logger.warning("More than one work preference location given, defaulting to only the first one for this iteration.")

        search_input.clear()
        search_input.send_keys(search_terms)
        time.sleep(1)
        location_input.clear()
        location_input.send_keys(config["locations"][0])
        time.sleep(1)

        #Press enter to do the search and save us the trouble of having to press the search button.
        search_input.send_keys(Keys.RETURN)
        time.sleep(2)

    def extract_and_evaluate_jobs(self, resume: Resume, ai_model, jobs_to_find = 10) -> list[JobPosting]:
        '''
        Attempts to evaluate the job board which the webdriver should be connected to and evaluates each job get a posting
        as well as an AI evalutaion score on how likely that we are to fit that jobs description.
        :param resume: information about the applica    nt
        :param ai_model: what AI model will we be asking questions of
        :return: array of Job Posting objects
        '''
        # The actual things we want to build fully evaulte before returning
        job_postings = []
        #Start on the first page (zero indexed)
        self.current_page = 0

        # Scroll the list of jobs to the bottom so we can get all elements at once.
        job_list_scroll = self.driver.find_element(By.XPATH, self.job_list_scroll_xpath)
        SeleniumUtils.scroll_element_in_steps(self.driver, job_list_scroll)

        # Until we have enough postings, or until we cannot click the "next" page of jobs"
        while len(job_postings) < jobs_to_find:

            job_elements = self.driver.find_elements(By.XPATH, self.job_list_xpath)
            # Iterate down each job element, click it, and extract the job details
            for element in job_elements:
                try:
                    element.click()
                except Exception as e:
                    self.logger.error(f"Unable to click job element! Exception: " + str(e))
                    continue

                job_posting = self._create_job_posting_from_client_(resume, ai_model)
                if job_posting is not None:
                    job_postings.append(job_posting)

                if len(job_postings) >= jobs_to_find:
                    break

            #If we need to get more jobs, click on the "next" page
            if self._get_next_page_of_jobs_():
                self.current_page += 1
            else:
                # We arent able to get any more jobs from more pages so return
                return job_postings

        return job_postings

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



    def _do_login_(self):

        if (not global_config.LINKEDIN_EMAIL or len(global_config.LINKEDIN_EMAIL) == 0):
            self.logger.error("Unable to setup linkedin login because no login email was configured in secrets.yaml")
            raise Exception("Cannot automate linkedin browsing without a configured email and password to use.")
        if (not global_config.LINKEDIN_PASSWORD or len(global_config.LINKEDIN_PASSWORD) == 0):
            self.logger.error("Unable to setup linkedin login because no login password was configured in secrets.yaml")
            raise Exception("Cannot automate linkedin browsing without a configured email and password to use.")

        '''
        Internal method that logs the client in with their given credentials.
        :return: returns when the user has been logged in.
        '''
        email_input = self.driver.find_element(By.XPATH, self.email_xpath)
        password_input = self.driver.find_element(By.XPATH, self.password_xpath)
        sign_in_button = self.driver.find_element(By.XPATH, self.sign_in_xpath)
        if not email_input or not password_input or not sign_in_button :
            raise Exception("Cannot find the required elements to auto login to linked in!")

        email_input.send_keys(global_config.LINKEDIN_EMAIL)
        time.sleep(1)
        password_input.send_keys(global_config.LINKEDIN_PASSWORD)
        time.sleep(1)
        sign_in_button.click()
        # Wait longer to make sure it loads
        time.sleep(3)
        #Validate that the client is now at the logged in users feed
        redirect_url = self.driver.current_url
        if self.feed_url not in redirect_url:
            raise Exception("Failed to login to clients feed! May need to configure account if it is brand new!")

    def _apply_preferences_(self, preferences: {}):
        '''
        applies the preferences config option that is the work_preferences object loaded from config to linkedin
        via selenium as best we can.
        Further functionality will allow for more custom configuration
        :param preferences: configuration objectfrom the work_preferences.yaml
        :return: nothing if preferences were able to be applied to the client session.
        '''
        #TODO Please fill in as many preferences as you can with actual selenium actions
        pass

    def _create_job_posting_from_client_(self, resume: Resume, ai_model) -> JobPosting:
        '''
        Helper method that MUST BE CALLED AFTER THE POSTING HAS BEEN CLICKED.
        Will attempt to scrape the job details, url, and other relevant info and return as a JobPosting object
        :param resume: information about the applicant
        :param ai_model: what AI model will we be asking questions of
        :return: Job Posting object representing a listing and its chance that we will be a successfull applicant.
        '''
        job_details_html_element = self.driver.find_element(By.XPATH, self.job_details_xpath)
        job_details_html_string = job_details_html_element.get_attribute("innerHTML")

        chance_of_interview, chance_of_hire = self._evaluate_chance_of_landing_job_(ai_model, job_details_html_string, resume)

        # find the apply button, click it, make sure it opens the application to a 3rd party website, then grab that tabs url and create the posting
        try:
            job_apply_button = self.driver.find_element(By.XPATH, self.job_apply_link_button_xpath)
            try:
                job_apply_button.click()
            except ElementClickInterceptedException:
                self.logger.error("Unable to click job apply button because some other element overlaps it! Screen may not be large avoid message pop up")
                return None

            time.sleep(3)

            # if the button click does not open up a new tab then that is a flow that we currently do not support.
            client_tabs = self.driver.window_handles
            if len(client_tabs) != 2:
                self.logger.warning("Unexpected action occured when clicking the apply button for the job! Currently the application does not handle non-redirects to an external website")
                return None
            # switch to the newly opened tab
            self.driver.switch_to.window(client_tabs[1])

            # TODO add logic in here that inspects the webpage and determines what HCM_Crawler to use?
            # If we cant apply for it then we should create the posting right?

            job_posting_url = self.driver.current_url

            self.driver.close()
            self.driver.switch_to.window(client_tabs[0])

            job_posting = JobPosting(job_details_html_string, job_posting_url, chance_of_interview, chance_of_hire)
            return job_posting

        except NoSuchElementException as no_job_except:
            # If this is an easy apply job, they have such a negative review and different work flow we will not apply to them.
            try:
                easy_apply_button =self.driver.find_element(By.XPATH, self.easy_apply_link_button_xpath)
                self.logger.info("Avoiding applying to job because it is an easy apply job")
                return None
            except NoSuchElementException as no_easy_apply_except:
                self.logger.error("Unable to find either the job apply button or an easy job apply button! It is likely that the Linkedin Schema may have changed!")
                return None

        time.sleep(1)

    def _get_next_page_of_jobs_(self) -> bool:
        '''
        Method that attempts to load the next set of jobs by simply adding a start term to the current url to
        pull new jobs into the client
        :return: True if we successfully clicked the element, False if an exception occured, but was handled
        '''
        next_amount = str(self.current_page*25)
        next_page_url = self.driver.current_url + self.linkedin_page_incrementor_string + next_amount
        try:
            self.driver.get(next_page_url)
        except Exception as e:
            self.logger.error(f"Unable to load next pages of job because we were unable to get the URL for the next page {next_page_url}")
            return False

        try:
            # Scroll the list of jobs to the bottom so we can get all elements at once.
            job_list_scroll = self.driver.find_element(By.XPATH, self.job_list_scroll_xpath)
            SeleniumUtils.scroll_element_in_steps(self.driver, job_list_scroll)
        except Exception as e:
            self.logger.error("Unable to find scroll element and scroll to bottom to load all jobs for this page!")
        return True

    def _evaluate_chance_of_landing_job_(self, ai_model, job_html_string: str, resume: Resume) -> Tuple[int, int]:
        '''
        Method that uses the AI model to ask a specific prompt that will tell us how likely we are to get a call, and how
        likely we are to be hired. This allows us to provide the service of just giving people a list of 100 jobs they are most likely to get.
        :param ai_model:
        :param job_html_string:
        :param resume:
        :return: tuple of chance of getting an interview, chance of getting hired
        '''
        # load files as modules so we can access their strings
        chance_matching_prompt_module = load_module(global_config.PROMPTS_DIRECTORY / f"{self.matching_prompt}.py", self.matching_prompt)
        # convert the resume to yaml form
        matching_prompt = ChatPromptTemplate.from_template( chance_matching_prompt_module.prompt_template.format(
            system_message=chance_matching_prompt_module.system_message,
            job_description=job_html_string,
            resume=yaml.dump(resume.dict(), default_flow_style=False)
        ))
        try:
            matching_chain = matching_prompt | ai_model | StrOutputParser()
            matching_answer = matching_chain.invoke({})
            # Make sure our answer has our target groups
            if matching_answer.find(self.matching_call_chance_phrase) < 0 or matching_answer.find(self.matching_hired_chance_phrase) < 0:
                self.logger.error(f"Received response from OpenAI of {matching_answer} but it does not contain our search groups to extract the values.")
                return [0, 0]

            # Use strict format to our advantage and avoid regex issues
            call_start_index = matching_answer.find(self.matching_call_chance_phrase) + len(self.matching_call_chance_phrase)
            call_end_index = matching_answer.find("%", call_start_index)
            call_chance = int(matching_answer[call_start_index:call_end_index])

            hire_start_index = matching_answer.find(self.matching_hired_chance_phrase) + len(self.matching_hired_chance_phrase)
            hire_end_index = matching_answer.find("%", hire_start_index)
            hire_chance = int(matching_answer[hire_start_index:hire_end_index])
            return [call_chance, hire_chance]
        except Exception as e:
            self.logger.error("Failed to get an answer on the matching percentages for ourself with the job!")
            self.logger.error(e)
            return [0, 0]

        return [0, 0]


