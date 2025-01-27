import logging

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FireFoxService
from selenium.webdriver.remote.webdriver import BaseWebDriver
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

from local_config import global_config


class WebDriverFactory():
    '''
    Factory class that allows us to specify drivers that will be used for specific functions
    (Visual if need be, non-visual, etc.)
    '''

    logger = logging.getLogger("web_driver_factory")

    def chrome_browser_options(self) -> Options:
        options = webdriver.ChromeOptions()
        return options

    def firefox_browser_options(self) -> Options:
        options = webdriver.FirefoxOptions()
        return options

    def get_chrome_web_driver(self) -> BaseWebDriver:
        '''
        :return: web-driver for chrome
        '''
        try:
            # Use webdriver_manager to handle ChromeDriver
            driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()),
                                      options=self.chrome_browser_options())
            self.logger.debug("Chrome Browser initialized successfully.")
            return driver

        except Exception as e:
            self.logger.error(f"Failed to initialize chrome browser: {str(e)}")
            raise RuntimeError(f"Failed to initialize chrome browser: {str(e)}")

    def get_fire_fox_web_browser(self):
        '''
        :return: web-driver for fire fox
        '''
        try:
            # Use webdriver_manager to handle ChromeDriver
            driver = webdriver.Firefox(service=FireFoxService(GeckoDriverManager().install()),
                                       options=self.firefox_browser_options())
            self.logger.debug("FireFox Browser initialized successfully.")
            return driver
        except Exception as e:
            self.logger.error(f"Failed to initialize firefox browser: {str(e)}")
            raise RuntimeError(f"Failed to initialize firefox browser: {str(e)}")
