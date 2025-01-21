import unittest
import logging

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_openai import ChatOpenAI
from local_config import global_config
from src.utils.llm_utils.open_ai_action_wrapper import OpenAiActionWrapper

class LinkedInBoardBrowserTest(unittest.TestCase):
    '''
    TODO Explain what functionality this will provide a test to.
    '''
    logger = logging.getLogger("linked_in_board_browser_test")

    def test_can_do_search(self):
        '''
        Validates that the LinkedInBoardBrowser is able to apply searches with different search terms, and different
        preferences.
        :return: True if html reflects search terms are in box, preferences were set, and that some search was performed
        '''
        # TODO Please write this test.
        pass

    def test_can_extract_and_evaluate_jobs(self):
        '''
        Validates that after an arbitrary simple search is done we are able to extract and job information and attempt
        to call an AI Model
        :return: True if html element that reveals how many jobs there were on the page matches the length of jobs extracted
        '''
        # TODO Please write this test.
        pass