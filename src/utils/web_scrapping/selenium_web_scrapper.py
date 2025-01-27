import json
from abc import abstractmethod, ABC

from selenium.webdriver.remote.webdriver import BaseWebDriver

from local_config import global_config


class SeleniumWebScrapper(ABC):
    '''
    Base class that this application will use for scrapping any website.
    Specifically allows for cookies to be saved and defines a close down method
    '''
    @abstractmethod
    def __init__(self, driver: BaseWebDriver):
        self.driver = driver
        '''
        First initializer will call the web driver to intialize selenium (This is to account for future sites that use JS to load their html)
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
        with open(cookies_file, "w") as file:
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