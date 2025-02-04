from pathlib import Path

from inquirer import List

from src.config.local_logging import LocalLogging


class BuildEmbeddedVectorManually:
    '''
    NOTE: THIS IS A DEVELOPER TOOL CLASS
    Class that has a web driver go to a predefined URL then pauses for the user to CLICK on each element
    then computes the average embedded vector. This way i can use specific embedded vectors for elements i want to
    identify, and wont have to go through the trouble of training my own model on my wifes computer.
    '''

    # JavaScript to track clicks with Shift key pressed
    __tracking_script = """
        window.clickData = [];
        document.addEventListener('click', function(e) {
            if (e.shiftKey) {  // Check if Shift key is pressed
                var rect = e.target.getBoundingClientRect();
                window.clickData.push({
                    element: e.target,
                    scrollX: window.scrollX,
                    scrollY: window.scrollY,
                    clientX: e.clientX,
                    clientY: e.clientY
                });
            }
        }, true);
    """


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
        self.vector_save_file = Path("data_folder/output")

    def collect_average_vector_over_urls(self):
        total_element_vector = self._run_page_collection()
        for url in self.list_of_urls:
            total_element_vector.append(self._run_page_collection(url))

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

        try:
            self.driver.execute_script(BuildEmbeddedVectorManually.__tracking_script)
        except Exception as scriptException:
            self.logger.error(f"Unable to execute script which tracks clicks while holding shift!")
            return None


        # Get clicked elements directly from JavaScript
        clicked_elements = self.driver.execute_script("""
            return window.clickData.map(function(data) {
                return data.element;
            });
        """)

        # Convert to WebElement objects and deduplicate
        unique_elements = []
        seen_elements = set()
        for elem in clicked_elements:
            element_id = self.driver.execute_script("return arguments[0].id;", elem)
            element_xpath = self.driver.execute_script(
                "return getXPath(arguments[0]);",
                elem
            )
            if element_xpath not in seen_elements:
                seen_elements.add(element_xpath)
                unique_elements.append(elem)

        # Display results
        print(f"\nFound {len(unique_elements)} elements clicked with Shift:")
        for idx, elem in enumerate(unique_elements, 1):
            try:
                tag = elem.tag_name
                text = elem.text[:50].strip() if elem.text else ''
                attributes = []
                for attr in ['id', 'class', 'href', 'name']:
                    value = elem.get_attribute(attr)
                    if value: attributes.append(f'{attr}="{value}"')
                print(f"{idx}: {tag} {' '.join(attributes)}")
                print(f"   Text: {text}{'...' if len(elem.text) > 50 else ''}")
            except Exception as e:
                print(f"{idx}: [Element no longer exists]")

