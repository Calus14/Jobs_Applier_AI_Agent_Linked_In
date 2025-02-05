import time
from pathlib import Path
from typing import List

import numpy as np
from selenium.webdriver.remote.webelement import WebElement

from src.config.local_logging import LocalLogging
from src.utils.llm_utils.open_ai_action_wrapper import OpenAiActionWrapper
from src.utils.web_scrapping.selenium_utils import SeleniumUtils


class BuildEmbeddedVectorManually:
    '''
    NOTE: THIS IS A DEVELOPER TOOL CLASS
    Class that has a web driver go to a predefined URL then pauses for the user to CLICK on each element
    then computes the average embedded vector. This way i can use specific embedded vectors for elements i want to
    identify, and wont have to go through the trouble of training my own model on my wifes computer.
    '''

    # Javascript to disable navigation from this pages url so that

    # JavaScript to track clicks with Shift key pressed
    __tracking_script = """
        // Create status container
        const statusDiv = document.createElement('div');
        statusDiv.style.position = 'fixed';
        statusDiv.style.top = '10px';
        statusDiv.style.right = '100px';
        statusDiv.style.backgroundColor = 'yellow';
        statusDiv.style.padding = '10px';
        statusDiv.style.zIndex = '9999';
        statusDiv.innerHTML = 'Status: Waiting for elements...';
        document.body.appendChild(statusDiv);
    
        window.clickData = [];
        window.enterPressed = false;
    
        // Track clicks
        document.addEventListener('click', function(e) {
            if (e.shiftKey) {  // Check if Shift key is pressed
                window.clickData.push({
                    element: e.target,
                    timestamp: Date.now()
                });
                statusDiv.innerHTML = `Selected elements: ${window.clickData.length}<br>Press ENTER to finish`;
            }
        }, true);
    
        // Track Enter key press
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                window.enterPressed = true;
                statusDiv.innerHTML = 'Processing...';
                e.preventDefault();  // Stop default Enter behavior
            }
        });
    """

    base_directory = Path(__file__).resolve().parent.parent


    def __init__(self, driver, ai_model, list_of_urls, vector_name):
        '''
        :param driver: Provide a driver that will be used to navigate the pages
        :param ai_model: a model that will do the embedding
        :param list_of_urls: a list of urls to navigate
        :param vector_name: the name that this average vector will be saved to in our output file
        '''
        self.driver = driver
        self.ai_model = ai_model
        self.list_of_urls = list_of_urls
        self.vector_name = vector_name

        self.logger = LocalLogging.get_local_logger("build_embedded_vector_manually_process")
        self.vector_save_file = BuildEmbeddedVectorManually.base_directory / "data_folder/output"

    def collect_average_vector_over_urls(self):
        total_element_vectors = []
        for url in self.list_of_urls:
            try:
                total_element_vectors.append(self._run_page_collection(url))
            except Exception as e:
                self.logger.error(e)

        # remove any empty vectors that could have come from an error
        non_empty_vectors_matrix = [vector for vector in total_element_vectors if len(vector) > 0]
        element_vector_matrix = np.array(non_empty_vectors_matrix)

        # Compute the mean across the vectors (this will give us the average
        average_vector = np.mean(element_vector_matrix, axis=0)
        vector_str = ",".join(map(str, average_vector))

        # Append to a file
        with open(self.vector_save_file, "a") as f:
            f.write(vector_str + "\n")


    def _run_page_collection(self, url : str):
        '''
        Moves the client to a given url and allows the user (a developer) to click on elements while holding
        SHIFT (please remember to hold shift) REMEMBER TO HOLD SHIFT
        To exit recording elements that you wish to be added press enter and the elements will be added.
        :return: List of all embedded vector representations selected while on the web-page
        '''
        try:
            self.driver.get(url)  # Replace with your URL
        except:
            self.logger.error(f"Unable to open url: {url} to select elements to build embedded vector for vector: {self.vector_name}")
            return None

        starting_url = self.driver.current_url
        try:
            self.driver.execute_script(BuildEmbeddedVectorManually.__tracking_script)
        except Exception as scriptException:
            self.logger.error(f"Unable to execute script which tracks clicks while holding shift!")
            return None

        # Wait until Enter is pressed in the browser
        while True:
            enter_pressed = self.driver.execute_script("return window.enterPressed;")
            if enter_pressed:
                break
            time.sleep(0.5)  # Check every 500ms
            # there is an edge case where clicking an element cad take the current url to a different page completely
            # If this happens we will simply go to the next url and this is an edge case we can solve later
            if self.driver.current_url != starting_url:
                self.logger.warn(f"Unable to get elements for url: {url} because clicking an element navigated us to a different page!")
                raise Exception("Element navigated away from original page.")

        # Get clicked elements directly from JavaScript
        clicked_elements = self.driver.execute_script("""
            return window.clickData.map(function(data) {
                return data.element;
            });
        """)

        unique_elements_html_context_map = SeleniumUtils.get_selenium_elements_as_critical_html_strings(self.driver, clicked_elements, context_level=1)
        unique_elements_html_strings = list(unique_elements_html_context_map.keys())
        if isinstance(self.ai_model, OpenAiActionWrapper):
            return self.ai_model.embed_documents(unique_elements_html_strings)
        else:
            self.logger.error("Unable to find embedded vectors for given page because configured AI is not an type that has been handled explicitly.")
            raise Exception("Unconfigured AI Model in _run_page_collection")
