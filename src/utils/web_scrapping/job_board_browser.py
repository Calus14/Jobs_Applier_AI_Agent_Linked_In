from abc import ABC, abstractmethod

'''
Base class that needs to be extended by job board specific browsers. Each browser should be holding a web-driver that
will allow us to interact with the job board to advance the client state and get information about the jobs.

Note: Purposely abstract so no implementation of __init__
'''
class JobBoardBrowser(ABC):

    @abstractmethod
    def initialize(self, driver):
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

        0000
        :return:
        '''
        pass

    @abstractmethod
    def extract_and_evaluate_jobs(self, htmlElement) -> JobPosting[]:

        pass

    # Takes a web element and builds a site Item Object
    @abstractmethod
    def getItemFromWebElement(self, htmlElement):
        pass

    def scrapeWebsite(self, itemToSearch):

        filledWebItems = []
        self.initializeScrapper(itemToSearch)

        possibleWebElements = self.getPossibleItemWebElements()

        for possibleElement in possibleWebElements:
            if( self.isValidWebElement(possibleElement)):
                filledWebItems.append(self.getItemFromWebElement(possibleElement))

        return filledWebItems