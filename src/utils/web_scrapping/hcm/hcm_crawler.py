import re
from abc import abstractmethod
from enum import Enum
from typing import List

from selenium.webdriver.remote.webelement import WebElement

from local_config import global_config, LocalLogging
from src.data_objects.job_posting import JobPosting
from src.utils.web_scrapping.selenium_utils import SeleniumUtils
from src.utils.web_scrapping.selenium_web_scrapper import SeleniumWebScrapper


class HcmCrawler(SeleniumWebScrapper):
    '''
    Base class that needs to be extended by hcm specific crawlers. Each browser should be holding a web-driver that
    will allow us to interact with the hcm site. Also there will be a "state" variable for all HCM management because
    there is such a complex state. This state will be queryable for logging.
    '''

    snake_case_pattern = re.compile(r'(?<!^)(?=[A-Z])')

    class State(Enum):
        UN_STARTED = 1
        LOGGING_IN = 2
        LOGGED_IN = 3
        CREATING_ACCOUNT = 4
        CREATED_ACCOUNT = 5
        FILLING_APPLICATION = 6
        SUBMITTED_APPLICATION = 7
        ERROR = 8

    def __init__(self, driver, posting: JobPosting):
        super().__init__(driver)
        self.driver = driver

        self.logger = LocalLogging.get_local_logger(__name__)

        if not posting:
            self.logger.error("Passed a null Job Posting to a HCM Crawler! Not able to make an HCM Crawler without a job posting!")
            raise Exception("Null Job Posting given for HCM Crawler")
        self.posting = posting

        try:
            self.driver.get(posting.url_link)
        except Exception as e:
            self.logger.error(f"Unable to get posting url of {posting.url_link} via web-driver!")
            raise e

        #List of strings that can be used to debug, each string represents a state movement.
        self.application_logs = []
        self.internal_state: Enum = self.State.UN_STARTED
        self.app_elements_to_fill: List[WebElement] = []
        self.elements_to_fill_out = []

    def __progress_state(self, new_state: Enum, change_msg: str):
        '''
        private helper method that logs whenever a state change occurs and updates our internal state then calls the
        do_application_flow once the new state has been set.
        NOTE: any state can change to any state in its current implementation
        :param new_state: state you wish to set on this crawler
        :param change_msg: message you want recorded with this state change.
        '''
        logger_msg = f"{self.internal_state.name}->{new_state.name}: {change_msg}"
        self.application_logs.append(logger_msg)
        self.internal_state = new_state
        self.do_application_flow()

    def do_application_flow(self):
        '''
        method that will attempt to follow the flow steps listed above. Where each specific HCM crawler will implement
        the abstract methods that are relied on to move the state.
        Uses recursion to call itself again after each progress_state call.

        Please refer to documentation/hcm_state_flow.drawio diagram to see what is going on here
        '''

        # Always scroll the page so that all elements are loaded before progressing to next step
        SeleniumUtils.scroll_element_in_steps(self.driver)

        #See if we need to login, and if so move to that state, otherwise move to a logged in state
        if self.internal_state == self.State.UN_STARTED:
            self._handle_unstarted_state()
        # If we are logging in, attempt to login, and if that fails attempt to create an ccount
        elif self.internal_state == self.State.LOGGING_IN:
            self._handle_logging_in_state()
        # If we are creating an account, attempt to do so.
        elif self.internal_state == self.State.CREATING_ACCOUNT:
            self._handle_creating_account()
        #see if we need to login, and move to the according state from there.
        elif self.internal_state == self.State.CREATED_ACCOUNT:
            self._handle_created_account()
        # If we are logged in, attempt to get application elements, then fill them out until we get no elements to fill out
        elif self.internal_state == self.State.LOGGED_IN:
            self._handle_logged_in()
        elif self.internal_state == self.State.FILLING_APPLICATION:
            self._handle_filling_application()
        elif self.internal_state == self.State.SUBMITTED_APPLICATION:
            self._handle_submitted_application()
        elif self.internal_state == self.State.ERROR:
            self._handle_error()
        else:
            self.logger.error("HCM_CRAWLER in a state that should be impossible")

    '''
    HELPER STATE METHODS BELOW
    All methods below handle how the internal crawlers state moves in a specific state.
    '''
    def _handle_unstarted_state(self):
        try:
            self._progress_app_to_start()
        except Exception as app_start_exc:
            self.logger.info(f"Unable to progress app to start but may not need to progress to start.- {app_start_exc}")

        try:
            login_bool = self._requires_login()
        except Exception as req_login_exc:
            self.__progress_state(self.State.ERROR, f"{req_login_exc} - Could not tell if we required a login")
            return

        if login_bool:
            self.__progress_state(self.State.LOGGING_IN, "Found login element, attempting to login.")
        else:
            self.__progress_state(self.State.LOGGED_IN, "No login element found, assuming we are \"logged in\"")

    def _handle_logging_in_state(self):
        # attempt to login
        try:
            attempt_bool = self._attempt_login()
        except Exception as login_exc:
            self.__progress_state(self.State.CREATING_ACCOUNT, f"{login_exc} - Could not login, trying to create an account")
            return

        # if we logged in, validate that we no longer "need to login"
        if attempt_bool:
            try:
                verify_login_bool = self._requires_login()
            except Exception as req_login_exc:
                self.__progress_state(self.State.CREATING_ACCOUNT, f"{req_login_exc} - Thought we successfully logged in, an exception occured while checking if we needed to login. attempting to create an account")
                return

            # If we still "need to login" it failed, we need to create an account
            if verify_login_bool:
                self.__progress_state(self.State.CREATING_ACCOUNT, "Thought we successfully logged in, however still see that we require to login. Attempting to create an account")
            else:
                self.__progress_state(self.State.LOGGED_IN, "Successfully logged in.")
        # We couldnt login, so make an account
        else:
            self.__progress_state(self.State.CREATING_ACCOUNT, f"Could not login, trying to create an account")

    def _handle_creating_account(self):
        # attempt to create an account
        try:
            attempt_create_account = self._create_account()
        except Exception as create_exc:
            self.__progress_state(self.State.ERROR, f"{create_exc} - Could not create an account!")
            return

        # if we logged in, validate that we no longer "need to login"
        if attempt_create_account:
            self.__progress_state(self.State.CREATED_ACCOUNT, "Successfully created an account!")
        # We couldnt create an account
        else:
            self.__progress_state(self.State.ERROR, "Could not create an account, ending application attempt!")

    def _handle_created_account(self):
        try:
            verify_login_bool = self._requires_login()
        except Exception as req_login_exc:
            self.__progress_state(self.State.ERROR, f"{req_login_exc} - Thought we successfully created an account, an exception occured while checking if we needed to login, ending application attempt!")
            return

            # If we still "need to login" try now that we made the account
        if verify_login_bool:
            try:
                final_attempt_bool = self._attempt_login()
            except Exception as final_login_exc:
                self.__progress_state(self.State.ERROR, f"{final_login_exc} - Thought we successfully created an account, but failed to login after, ending application attempt!")
                return

            # we still could not on our final login, so stop trying to apply
            if not final_attempt_bool:
                self.__progress_state(self.State.ERROR, f"Thought we successfully created an account, but failed to login after, ending application attempt!")
            else:
                self.__progress_state(self.State.LOGGED_IN, "Successfully logged in.")
        else:
            self.__progress_state(self.State.LOGGED_IN, "Successfully logged in.")

    def _handle_logged_in(self):
        # get all elements that need to be filled out
        try:
            self.app_elements_to_fill = self._get_application_elements()
        except Exception as app_elements_exc:
            self.__progress_state(self.State.ERROR, f"{app_elements_exc} - Could not retrieve application elements!")
            return

        # if there are elements that we need to fill out, move to filling out application
        if self.app_elements_to_fill and len(self.app_elements_to_fill) > 0:
            self.__progress_state(self.State.FILLING_APPLICATION, "Attempting to fill out the application")
        # we have no more elements to fill, attempt to submit and move to a submitted state
        else:
            try:
                self._attempt_submit_app()
            except Exception as submit_exc:
                self.__progress_state(self.State.ERROR, f"{submit_exc} - Failed to submit application!")
                return

            self.__progress_state(self.State.SUBMITTED_APPLICATION, "Submitted Application")

    def _handle_filling_application(self):
        # get all elements that need to be filled out
        try:
            self._fill_application_elements(self.app_elements_to_fill)
        except Exception as fill_elements_exc:
            self.__progress_state(self.State.ERROR, f"{fill_elements_exc} - Could not fill application elements!")
            return

        self.app_elements_to_fill = []
        self.__progress_state(self.State.LOGGED_IN, "Filled out application elements")

    def _handle_submitted_application(self):
        self._log_application_progression()
        self.save_job_board_cookies()

    def _handle_error(self):
        self._log_application_progression()

    @abstractmethod
    def _progress_app_to_start(self):
        '''
        protected method  that attempts to progress the webpage to the application by clicking buttons like "apply now"
        or "apply here" etc. as well as handle any other options that would generally be required before filling out the app or logging in
        :except if there is any issue with progressing the app to a "starting point"
        '''
        pass

    @abstractmethod
    def _requires_login(self):
        '''
        protected method  that will check the state of the web driver to see if the loaded page has a "log in element"
        :returns true if this page requires a login, false if we can apply without loggin in
        '''
        pass

    @abstractmethod
    def _attempt_login(self):
        '''
        protected method that will attempt to login with the current state of the web driver using the
        default_account_email and default_account_password defined in the secrets.yaml and stored in the global_config
        object

        :return: true if we were able to log in, false or an exception if there was an error
        '''
        pass

    @abstractmethod
    def _create_account(self):
        '''
        protected method that will attempt to create an account with the current state of the web driver using the
        default_account_email and default_account_password defined in the secrets.yaml and stored in the global_config
        object

        :return: true if we were able to create an account, false or an exception if there was an error
        '''
        pass

    @abstractmethod
    def _get_application_elements(self) -> List[WebElement]:
        '''
        protected method that will use AI to find all elements on the page that need to be filled out as part of the
        application.

        NOTE: there are 2 implemenations of doing this, 1 using vector storage to find what elements on the page
        are required inputs, and the other using just a LLM directly to fill out all html elements that need to be
        filled out.
        :return: a list of all webElements that need to be filled out, WITH their appropriate FILLED IN DATA
        '''
        pass

    @abstractmethod
    def _fill_application_elements(self, web_elements: List[WebElement]):
        '''
        protected method that will fill out all elements required for the applicaiton to move its state forward.
        - If we are using LLM's these web elements will be filled out and will simply need to be applied to the driver
        - If we are using vectorstore we will need to pull the most relevant data
        It will progress the webdriver states by submitting all of these elements too
        :param webElements: elements that need to be filled out for the application
        '''
        pass

    @abstractmethod
    def _attempt_submit_app(self):
        '''
        Attempts to submit the application and confirm that the application is fully completed.
        :return: true if the application was able to be submitted
        '''
        pass

    def _log_application_progression(self):
        '''
        Writes to a log file all of the state logs that this crawler has went through so that the user can see all
        applications states
        '''
        crawler_name = self.snake_case_pattern.sub('_', type(self).__name__).lower()
        applications_file = global_config.LOG_OUTPUT_FILE_PATH / f"{crawler_name}_applications.json"

        # Save cookies to a file
        with open(applications_file, "a") as file:
            for log in self.application_logs:
                file.write(log + "\n")
