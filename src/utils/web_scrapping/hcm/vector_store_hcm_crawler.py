import json
import time
from typing import List, Dict

import numpy as np
from bs4 import PageElement
from selenium.webdriver.remote.webelement import WebElement

from src.config.local_config import global_config
from src.config.local_logging import LocalLogging
from src.data_objects.job_posting import JobPosting
from src.utils.llm_utils.open_ai_action_wrapper import OpenAiActionWrapper
from src.utils.math_utils import MathUtils, RunningAverage
from src.utils.module_loader import load_module
from src.utils.web_scrapping.hcm.hcm_crawler import HcmCrawler
from src.utils.web_scrapping.selenium_utils import SeleniumUtils

class ElementMatchPair:
    '''
    Helper class that avoids having to use maps everywhere
    '''
    def __init__(self, element: WebElement, embedding_vector: List[float], match_confidence: float):
        self.element = element
        self.embedding_vector = embedding_vector
        self.match_confidence = match_confidence


class VectorStoreHcmCrawler(HcmCrawler):
    '''
    Abstract HCM Crawler class that uses vector embeddings to break down an html page into only elements that are
    most used by users to navigate a page, then creates vector embeddings for each element, and finally takes basic prompts
    and calculates the prompt and those critical elements dot product to determine if an element exists, and if so which
    element to interact with.
    '''

    #static floating value that limits what we actually consider, and what we think is "reaching"
    certainty_clearance = 0.5 # number that the dot product projection has to be over to be considered
    prompt_average_top_score_map: Dict[str, RunningAverage] = {} #static map that will keep a running mark on all prompts and what the average top score is.

    prompt_module = load_module(global_config.PROMPTS_DIRECTORY / "hcm_crawler_prompts.py", "hcm_crawler_prompts")

    ''' 
    TODO create Query class that uses "persistence" which for now will be just files that allows us to start with an initial
    string that represents the vector, then everytime we find a html element that correlates past the threshhold we will
    update our internal embedded vector to be closer to the found element. Marking each page as "contributed" so we do not
    have 1 test page setting all the weights.
    '''

    def __init__(self, driver, posting: JobPosting, ai_model):
        super().__init__(driver, posting, ai_model)
        self.element_to_vector_map = {}
        self.logger = LocalLogging.get_local_logger(__name__)
        if type(self.ai_model) is not OpenAiActionWrapper:
            raise Exception("UNABLE TO USE VECTOR STORE HCM CRAWLER! Need an OpenAiActionWrapper to use the OpenAiEmbeddings"
                            + " for this Crawler to work! Configured AI Model is - " + str(type(self.ai_model)))

    @staticmethod
    def dump_average_prompt_scores():
        '''
        Appends to a file each time these are run so that we can later know how accurate our prompts are for each run.
        '''
        prompt_score_file = global_config.LOG_OUTPUT_FILE_PATH / "vector_prompt_scores_cookies.json"

        # Save to a file
        with open(prompt_score_file, "a") as file:
            file.write("\n\n----------------------------------------\n\n")
            json.dump(VectorStoreHcmCrawler.prompt_average_top_score_map, file, default=lambda o : o.__dict__)

    def close_browser(self):
        ''' We do not need cookies for the hcm websites we are crawling'''
        pass

    def _progress_app_to_start(self):
        '''
        protected method  that attempts to progress the webpage to the application by clicking buttons like "apply now"
        or "apply here" etc. as well as handle any other options that would generally be required before filling out the app or logging in
        :except if there is any issue with progressing the app to a "starting point"
        '''
        self.__break_page_into_vector_store()

        # Checks to see if there are any elements to fill out
        self.elements_to_fill_out = self.__get_all_matches_for_query(VectorStoreHcmCrawler.prompt_module.critical_elements_query)

        # If there are elements to fill out on the current clients page, then we can start the application more than likely.
        if len(self.elements_to_fill_out) == 0:
            # If there is an element like "apply now" or "click here to apply" we will need to click that button
            apply_element_pair = self.__get_top_match_for_query(VectorStoreHcmCrawler.prompt_module.apply_now_element_query)
            if not apply_element_pair:
                raise Exception("Was unable to find any elements to fill out or find any element to start application!")

            # click it
            SeleniumUtils.interact_with_element(apply_element_pair.element)
            time.sleep(1)

            # Covers the case of a popup for "apply with linkedin/apply manually"
            self.__break_page_into_vector_store()
            apply_manual_element_pair = self.__get_all_matches_for_query(VectorStoreHcmCrawler.prompt_module.apply_manual_element_query)
            if apply_manual_element_pair:
                SeleniumUtils.interact_with_element(apply_element_pair)
                time.sleep(1)
            return
        return

    # NOTE: Don't worry about trying and catching, the Hcm_Crawler state machine will handle exceptions in the following methods
    def _requires_login(self):
        '''
        protected method  that will check the state of the web driver to see if the loaded page has a "log in element"
        :returns true if this page requires a login, false if we can apply without loggin in
        '''
        self.__break_page_into_vector_store()

        login_element_pair = self.__get_top_match_for_query(VectorStoreHcmCrawler.prompt_module.login_element_query)

        # if we dont have any element to login
        if not login_element_pair:
            self.login_element = None

            # Do we have anything on the page that would indicate we need to login?
            login_indicator_pair = self.__get_top_match_for_query(VectorStoreHcmCrawler.prompt_module.login_indicator_element_query)
            if login_indicator_pair:
                raise Exception(f"Found an element that indicates we do need to login with certaintiy of {login_indicator_pair.match_confidence} but could not find a login element")

            # we didnt find any login element, and we didnt find any element that indicates we need to login
            return False
        else:
            # we found a login element, go ahead and store it on this crawlers self and return true
            self.login_element = login_element_pair.element
            return True

    def _attempt_login(self):
        '''
        protected method that will attempt to login with the current state of the web driver using the
        default_account_email and default_account_password defined in the secrets.yaml and stored in the global_config
        object

        :return: true if we were able to log in, false or an exception if there was an error
        '''
        if not self.login_element:
            raise Exception("Attempted to login before the login_element was set, must call requires_login first!")

        # Will throw exception to state machine if it is stale
        SeleniumUtils.interact_with_element(self.login_element)
        # wait 1 second for the page to move to logging in
        time.sleep(1)
        # get the new pages elements in the vector store
        self.__break_page_into_vector_store()

        login_element_pair = self.__get_top_match_for_query(VectorStoreHcmCrawler.prompt_module.login_element_query)
        username_element_pair = self.__get_top_match_for_query(VectorStoreHcmCrawler.prompt_module.user_element_query)
        password_element_pair = self.__get_top_match_for_query(VectorStoreHcmCrawler.prompt_module.password_element_query)

        if not login_element_pair or not username_element_pair or not password_element_pair:
            raise Exception("Cannot login because we could not find all 3 elements, login, username, and password!")

        # Fill out the username and password fields
        SeleniumUtils.interact_with_element(username_element_pair.element, action="send_keys", text=global_config.DEFAULT_EMAIL)
        SeleniumUtils.interact_with_element(password_element_pair.element, action="send_keys", text=global_config.DEFAULT_PASSWORD)
        SeleniumUtils.interact_with_element(login_element_pair.element)

        # Exceptions would be thrown if there was any error so return true
        return True

    def _create_account(self):
        '''
        protected method that will attempt to create an account with the current state of the web driver using the
        default_account_email and default_account_password defined in the secrets.yaml and stored in the global_config
        object

        :return: true if we were able to create an account, false or an exception if there was an error
        '''
        # get the first element of the most matching elements
        create_account_element_pair = self.__get_most_matching_elements_to_prompt(VectorStoreHcmCrawler.create_account_element_query)
        if not create_account_element_pair:
            raise Exception("No element found to create account.")

        # attempt to click the create_account button
        SeleniumUtils.interact_with_element(create_account_element_pair.element)
        time.sleep(2)

        # re-index the vector storage with the pages new elements that should have appeared
        self.__break_page_into_vector_store()

        confirm_element_pair = self.__get_top_match_for_query(VectorStoreHcmCrawler.prompt_module.confirm_element_query)
        username_element_pair = self.__get_top_match_for_query(VectorStoreHcmCrawler.prompt_module.user_element_query)
        password_element_pair = self.__get_top_match_for_query(VectorStoreHcmCrawler.prompt_module.password_element_query)

        if not confirm_element_pair or not username_element_pair or not password_element_pair:
            raise Exception("Cannot login because we could not find all 3 elements, confirm, username, and password!")

        # Fill out the username and password fields
        SeleniumUtils.interact_with_element(username_element_pair.element, action="send_keys", text=global_config.DEFAULT_EMAIL)
        SeleniumUtils.interact_with_element(password_element_pair.element, action="send_keys", text=global_config.DEFAULT_PASSWORD)
        SeleniumUtils.interact_with_element(confirm_element_pair.element)

        return True

    def _get_application_elements(self) -> List[WebElement]:
        '''
        protected method that will use AI to find all elements on the page that need to be filled out as part of the
        application.

        NOTE: there are 2 implemenations of doing this, 1 using vector storage to find what elements on the page
        are required inputs, and the other using just a LLM directly to fill out all html elements that need to be
        filled out.
        :return: a list of all webElements that need to be filled out, WITH their appropriate FILLED IN DATA
        '''
        self.__break_page_into_vector_store()

        # Checks to see if there are any elements to fill out
        self.elements_to_fill_out = self.__get_all_matches_for_query(VectorStoreHcmCrawler.prompt_module.critical_elements_query)

        # If there are elements to fill out on the current clients page, then we can start the application more than likely.
        if len(self.elements_to_fill_out) == 0:
            raise Exception("Was unable to find any elements to fill out!")


    def _fill_application_elements(self, web_elements: List[WebElement]):
        '''
        protected method that will fill out all elements required for the applicaiton to move its state forward.
        - If we are using LLM's these web elements will be filled out and will simply need to be applied to the driver
        - If we are using vectorstore we will need to pull the most relevant data
        It will progress the webdriver states by submitting all of these elements too
        :param webElements: elements that need to be filled out for the application
        '''

        # get all the embedding vectors from all out elements_to_fill_out
        elements_to_fill_vector_batch = np.array(
            list(pair.embedding_vector for pair in self.elements_to_fill_out)
        )
        # get all the given user info's keys, so that we can know what user provided info most matches the elements
        resume_keys_to_embedded_vect_map = global_config.get_user_resume_as_embedded_vector_map()
        resume_keys = list(resume_keys_to_embedded_vect_map.keys())
        resume_keys_vector_batch = np.array(
            list(resume_keys_to_embedded_vect_map.values())
        )

        # Now try to map each "key" that holds info on our users resume, to each element
        element_to_key_indexes = MathUtils.match_embedded_vector_batches(elements_to_fill_vector_batch, resume_keys_vector_batch)

        # each entry in the above list corresponds to the n'th element and its value is the index in our resume map
        if len(element_to_key_indexes) != len(self.elements_to_fill_out):
            self.logger.error("Unable to find element that matches to user info because element_to_indexes is not the "
                + "same length as elements_to_fill_out")
            return False
        if len(element_to_key_indexes) != len(global_config.RESUME_FLATTENED_MAP):
            self.logger.error("Unable to find element that matches to user info because element_to_indexes is not the "
                              + "same length as RESUME_FLATTENED_MAP")

        failed_elements_message = ""

        for index in len(element_to_key_indexes):
            # the math util matches the 'index' element to a number the number represents what key it is when
            resume_key = resume_keys[index]
            # get the value that most closely matches via dot product to the vector store of the element
            resume_key_value = global_config.RESUME_FLATTENED_MAP[resume_key]
            required_element = self.elements_to_fill_out[index]

            try:
                SeleniumUtils.interact_with_element(required_element.element, resume_key_value)
            except Exception as element_fill_out_exception:
                failed_elements_message += f"Failed to fill out element with html:{str(required_element.element)} \t with value:{resume_key_value}"
        if failed_elements_message and len(failed_elements_message) > 0:
            raise Exception(failed_elements_message)

        return True

    def _attempt_submit_app(self):
        '''
        Attempts to submit the application and confirm that the application is fully completed.
        :return: true if the application was able to be submitted
        '''
        print("TODO")
        return 0

    def __break_page_into_vector_store(self):
        '''
        Attempts to break the current page down into contextual HTML strings on all "critical" tags that we would expect
        to be used to fill out and navigate an application. Then uses AI Embeddings to break each contextual string
        into a vector_store so that we can calculate a cosine similarity. These vector stores are then mapped to their
        Selenium Element so that we can query for specific elements/actions and get the selenium element, act on it,
        and progress the state
        '''
        if type(self.ai_model) is not OpenAiActionWrapper:
            raise Exception("UNABLE TO USE VECTOR STORE HCM CRAWLER! Need an OpenAiActionWrapper to use the OpenAiEmbeddings"
                            + " for this Crawler to work! Configured AI Model is - " + str(type(self.ai_model)))
        self.element_to_vector_map.clear()
        start_milliseconds = int(round(time.time() * 1000))

        critical_strings_selenium_elements_map = SeleniumUtils.get_drivers_html_as_critical_html_strings(self.driver, context_level=2)
        html_break_time = int(round(time.time() * 1000)) - start_milliseconds
        self.logger.info(f"Took {html_break_time} milliseconds to break page into critical html strings.")

        crit_strings = list(critical_strings_selenium_elements_map.keys())
        embedded_vectors = self.ai_model.embed_documents(crit_strings)

        for selenium_element, embedded_vector in zip(critical_strings_selenium_elements_map.items(), embedded_vectors):
            self.element_to_vector_map[selenium_element] = embedded_vector

        total_run_time = int(round(time.time() * 1000)) - start_milliseconds
        self.logger.info(f"Took {total_run_time} milliseconds to break page into vector store.")

    def __get_highest_match_for_query_batch(self, query_vectors) -> List[ElementMatchPair]:
        '''
        Utility method that takes a batch of queries as embedded vectors, and then does linear algebra to fine the
        cosine similarity of each critical element to the query. Then finally, grabs the highest score for each element

        :param query_vectors: list of queries as embedded vectors
        :return: List of ElementMatchPairs representing each element and its match chance
        '''
        # 2d array where each row is the element as an embedded vector
        element_list = list(self.element_to_vector_map.keys())
        element_vector_list = list(self.element_to_vector_map.values())
        elements_vector_batch = np.array(element_vector_list)

        # 2d array where each row is a query as a vector
        resume_keys_vector_batch = np.array(query_vectors)

        # NOTE: Does not require to be normalized as embeddings the vector before returning
        # multiply by the transpose to do a dot product per each element to query
        similarity_matrix = np.dot(elements_vector_batch, resume_keys_vector_batch.T)

        # Now each row will have been the element, and each value in the elements chance can be averaged to see how likely that element is ultimately
        element_match_list = []
        for index in range(len(similarity_matrix)):
            # Get the list of dot products of this element vector embedding with each query embedding
            element_chances_list = similarity_matrix[index]
            # get objects to create the elementMatchPair
            element = element_list[index]
            element_vector = element_vector_list[index]

            # create a running average
            element_max = 0.0
            for query_chance in element_chances_list:
                if query_chance > element_max:
                    element_max = query_chance

            # add it to our element_match_kist
            element_match_list.append(ElementMatchPair(element, element_vector, element_max))

        return element_match_list


    def __get_most_matching_elements_to_prompt(self, query: str | List[str], top_matches = 1) -> Dict[PageElement, float]:
        '''
        MAGIC HAPPENS HERE
        Takes a prompt that is direct and ambiguous and attempts to find an elements that match the most to what its describing.
        This is done by using the dot product projection of all critical string vector embeddings and the prompt's vector embedding.
        :param query: String or list of strings to search the critical elements for that most closely matches it
        :param top_matches: how many matches to show,
        :return: dictionary of selenium element -> dotProductProjection (score of how closely it matches)
        '''
        if type(self.ai_model) is not OpenAiActionWrapper:
            raise Exception("UNABLE TO USE VECTOR STORE HCM CRAWLER! Need an OpenAiActionWrapper to use the OpenAiEmbeddings"
                            + " for this Crawler to work! Configured AI Model is - " + str(type(self.ai_model)))
        if not self.element_to_vector_map or len(self.element_to_vector_map) == 0:
            raise Exception("Cannot find most matching elements to prompt because the element_to_vector_map is empty!")

        # If we are passed a batch, we need to do an aggregate of each prompts similarity to the element
        if isinstance(query, List):
            query_vectors = self.ai_model.embed_documents(query)
            rep_prompt_string = query[0]
            element_match_list = self.__get_highest_match_for_query_batch(query_vectors)
        else: # its just one query so we can do a more simple flow.
            query_vector = self.ai_model.embed_string(query)
            rep_prompt_string = query
            element_match_list = [ElementMatchPair(v[0], v[1], MathUtils.cosine_similarity(query_vector, v[1]))
                                  for v in self.element_to_vector_map.items()]
        # Now get the top similarity scores
        top_element_matches = sorted(element_match_list, key=lambda x: x.match_confidence, reverse=True)[:top_matches]

        # Add to the running average so we can better tune queries and limits
        if rep_prompt_string not in VectorStoreHcmCrawler.prompt_average_top_score_map:
            VectorStoreHcmCrawler.prompt_average_top_score_map[rep_prompt_string] = RunningAverage()
        VectorStoreHcmCrawler.prompt_average_top_score_map[rep_prompt_string].update(top_element_matches[0].match_confidence)

        return top_element_matches


    def __get_top_match_for_query(self, query: str | List[str]) -> ElementMatchPair:
        '''
        Utility method that executes a query and gets only the top one, then logs if it doesnt meet the certainty level
        and finally returns the ElementMatchPair or None
        :param query: query to try and find a match for
        :return: top match as an ElementMatchPair or None
        '''
        # get the first element of the most matching elements
        element_top_match_list = self.__get_most_matching_elements_to_prompt(query)
        if len(element_top_match_list) == 0:
            raise Exception("Could not find a single element in the critical tags on this webpage")
        element_top_match = element_top_match_list[0]

        # if it falls below the threshold then log it and return None
        if element_top_match.match_confidence < VectorStoreHcmCrawler.certainty_clearance:
            self.logger.info(f"Did not find any element for the query \"{query}\", highest score was {element_top_match.match_confidence}")
            return None
        return element_top_match


    def __get_all_matches_for_query(self, query: str | List[str]) -> List[ElementMatchPair]:
        '''
        Utility method that executes a query and gets all matches that are above our match_confidence.

        :param query: query to try and find a match for
        :return: All matches for this query, that pass a threshold
        '''
        # get the first element of the most matching elements
        element_match_pairs = self.__get_most_matching_elements_to_prompt(query, len(self.element_to_vector_map))

        # if it falls below the threshold then log it and return None
        qualified_matches = [em for em in element_match_pairs if em.match_confidence >= VectorStoreHcmCrawler.certainty_clearance]
        return qualified_matches