import unittest
import logging

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_openai import ChatOpenAI
from local_config import global_config
from src.utils.llm_utils.open_ai_action_wrapper import OpenAiActionWrapper

test_prompt = "I am testing that i can communicate with you, please respond with \"Hello World\""

class OpenAiTests(unittest.TestCase):
    logger = logging.getLogger("open_ai_tests")

    '''
    These tests will not be purely unit tests but more integration tests that verify that your system is set up to actually
    be able to execute calls to open_ai API's. Tests will just validate that a test prompt is being sent and returning a 200
    response.
    '''

    def test_open_ai_wrapper_can_ask_questions(self):
        '''
        Basic test that validates that OpenAiActionWrapper can be used to ask OpenAi a question based on our configurations.
        :return: attempts to send a helloworld to openai and get a response.
        '''
        self.llm = OpenAiActionWrapper(
            ChatOpenAI(
                model_name="gpt-4o-mini", openai_api_key=global_config.API_KEY, temperature=global_config.LLM_TEMPERATURE
            ),
            enable_logging=False
        )

        prompt = ChatPromptTemplate.from_template(test_prompt)

        try:
            chain = prompt | self.llm | StrOutputParser()
            result = chain.invoke({})
            extracted_info = result.strip()
            self.logger.debug(f"Extracted information: {extracted_info}")

            self.assertTrue(len(extracted_info) > 0)
        except Exception as e:
            self.logger.error(f"Error during information extraction: {e}")
            #Force fail
            self.assertTrue(False)