import unittest
import logging

import os
from pathlib import Path
from src.config.local_config import global_config
from src.utils.config_validator import ConfigValidator, ConfigError
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_openai import ChatOpenAI
from src.config.local_config import global_config
from src.utils.llm_utils.open_ai_action_wrapper import OpenAiActionWrapper

test_prompt = "I am testing that i can communicate with you, please respond with \"Hello World\""

test_embedded_prompt = "Here is a little bit about me {self_summary}, can you sumarize for me what my pickup line should be?"
test_embedded_string = """
Bob the Builder is a beloved fictional character who serves as the centerpiece of a popular children’s television series of the same name. Created by British animator Keith Chapman, the show first aired in 1999 and quickly gained international acclaim for its engaging storylines and positive messaging. Bob is a skilled and resourceful construction contractor who, with the help of his team, undertakes various building and repair projects in the vibrant town of Sunflower Valley.
Bob’s team includes an array of anthropomorphic construction vehicles, including Scoop the digger, Muck the bulldozer, Dizzy the cement mixer, Roley the steamroller, and Lofty the crane. Each member of his team has a unique personality and skill set, promoting teamwork and the idea that everyone’s contribution is valuable. Bob’s human partner, Wendy, is equally essential, assisting with project management and offering solutions to challenges.
The show is known for its signature catchphrase, “Can we fix it? Yes, we can!” which encapsulates Bob’s optimistic and solution-oriented attitude. Themes of problem-solving, cooperation, and community building are central to the series, making it both educational and entertaining for young audiences. Episodes often explore topics like environmental conservation, recycling, and the importance of perseverance.
Over the years, Bob the Builder has evolved in terms of animation style and storytelling. The original stop-motion animation was updated to CGI in 2015, modernizing the visuals while retaining the show’s core values. Bob’s impact extends beyond television, with a wide range of toys, books, and merchandise, as well as live-action stage shows and theme park attractions.
Bob the Builder’s enduring appeal lies in its ability to teach important life lessons through relatable characters and engaging narratives. It continues to inspire children worldwide to approach challenges with creativity, teamwork, and a positive attitude.
"""

class OpenAiTests(unittest.TestCase):
    logger = logging.getLogger("open_ai_tests")

    '''
    These tests will not be purely unit tests but more integration tests that verify that your system is set up to actually
    be able to execute calls to open_ai API's. Tests will just validate that a test prompt is being sent and returning a 200
    response.
    '''

    def setUp(self):
        try:
            # Define and validate the data folder
            data_folder = Path("data_folder")
            secrets_file, config_file, plain_text_resume_file, output_folder = ConfigValidator.validate_data_folder(data_folder)

            # Validate configuration and secrets
            config = ConfigValidator.validate_config(config_file)
            secrets = ConfigValidator.validate_secrets(secrets_file)
            global_config.API_KEY = secrets["llm_api_key"]
            # NEEDED for some Open AI libraries to be on the OS path like Embeddings
            os.environ["OPENAI_API_KEY"] = global_config.API_KEY
            global_config.LINKEDIN_EMAIL = secrets["linkedin_email"]
            global_config.LINKEDIN_PASSWORD = secrets["linkedin_password"]
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
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred: {e}")

    def test_open_ai_wrapper_can_ask_questions(self):
        '''
        Basic test that validates that OpenAiActionWrapper can be used to ask OpenAi a question based on our configurations.
        :return: attempts to send a helloworld to openai and get a response.
        '''
        self.llm = OpenAiActionWrapper(
            ChatOpenAI(
                model_name=global_config.LLM_MODEL, openai_api_key=global_config.API_KEY, temperature=global_config.LLM_TEMPERATURE
            ),
            enable_logging=False
        )

        self.llm.embedd_string_for_future_chats(test_embedded_prompt)
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

    def test_open_ai_wrapper_can_embedd_and_use_embedded_strings(self):
        '''
        Makes sure that we can take a much larger string and condense it through embedding. Then makes sure that
        the prompt is able to return an answer still
        :return:
        '''
        self.llm = OpenAiActionWrapper(
            ChatOpenAI(
                model_name=global_config.LLM_MODEL, openai_api_key=global_config.API_KEY, temperature=global_config.LLM_TEMPERATURE
            ),
            enable_logging=False
        )

        self.llm.embedd_string_for_future_chats(test_embedded_string, "test_embedded_string")
        summary_embedded = self.llm.get_embedded_string("test_embedded_string")
        prompt = ChatPromptTemplate.from_template(test_embedded_prompt.format(self_summary=summary_embedded))

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
