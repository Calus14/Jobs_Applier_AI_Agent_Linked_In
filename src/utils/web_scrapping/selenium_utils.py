import time

class SeleniumUtils:
    '''
    Just a util class that will hold static methods that are useful for interacting with web-pages on selenium
    '''

    @staticmethod
    def scroll_element_in_steps(driver, element, num_steps=5, sleep_time_per_step=.25):
        """
        Scrolls a given element in chunks.

        :param driver: Selenium WebDriver instance.
        :param element: The scrollable element.
        :param num_steps: How many steps to scroll in.
        :param sleep_time_per_step: Pause in seconds between each scroll step (default is 0.25 seconds).
        """
        # Get the total scroll height of the element
        total_scroll_height = driver.execute_script("return arguments[0].scrollHeight;", element)
        # Calculate the chunk size
        chunk_size = total_scroll_height / num_steps

        for step in range(num_steps) :
            # Scroll the element by the chunk size
            driver.execute_script("arguments[0].scrollTop = arguments[1];", element, (step+1) * chunk_size)
            # Pause to allow content to load
            time.sleep(sleep_time_per_step)

        # Ensure the element is fully scrolled to the bottom
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", element)
