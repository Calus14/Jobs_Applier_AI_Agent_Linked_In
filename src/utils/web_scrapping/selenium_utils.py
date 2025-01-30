import copy
import time
from typing import List, Dict

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import BaseWebDriver
from bs4 import BeautifulSoup, Tag
from selenium.webdriver.remote.webelement import WebElement

from local_config import LocalLogging


class SeleniumUtils:

    logger = LocalLogging.get_local_logger("SeleniumUtils")

    '''
    Just a util class that will hold static methods that are useful for interacting with web-pages on selenium
    '''
    # Used to simplify a html page into relevant elements that can be put through vector embeddings
    critical_tags = ['a', 'button', 'input', 'textarea', 'select', 'label', 'form', ]

    @staticmethod
    def scroll_element_in_steps(driver, element=None, num_steps=5, sleep_time_per_step=.25):
        """
        Scrolls a given element in chunks.

        :param driver: Selenium WebDriver instance.
        :param element: The scrollable element.
        :param num_steps: How many steps to scroll in.
        :param sleep_time_per_step: Pause in seconds between each scroll step (default is 0.25 seconds).
        """
        if element is None:
            element = driver.find_element(By.TAG_NAME, "html")
            if not element:
                SeleniumUtils.logger.warn("Unable to find base html element so unable to scroll whole page.")
                return

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

    @staticmethod
    def get_drivers_html_as_critical_html_strings(driver: BaseWebDriver, context_level=1) -> Dict[str, WebElement]:
        """
        Gets a drivers HTML but only keeps fields that we consider critical for purposes of embedded vector comparisons
        allowing us

        :param driver: Selenium WebDriver instance.
        :param element_cache: Cache that can be passed in
        :return map of the html critical string -> the selenium element
        """

        page_html = driver.page_source
        soup = BeautifulSoup(page_html, 'html.parser')
        # Remove all the heavy strings that likely load with javascript
        for tag in soup.find_all(['style', 'meta', 'script']):
            tag.decompose()

        # Map the context string we build up with beautiful soup, to its XPath string, so that we can retrieve all
        # selenium elements in one client interaction
        context_to_xpath_map = {}
        for tag in SeleniumUtils.critical_tags:
            for element in soup.find_all(tag):
                copy_element = copy.copy(element)
                element_xpath = SeleniumUtils.get_xpath_for_element(copy_element)

                # get a vertical parent context
                parent = copy_element.parent
                parent_context = SeleniumUtils.get_parent_tags_with_cleared_children(copy_element, context_level)

                # get the vertical child context
                SeleniumUtils.recursive_soup_child_clearer(copy_element, context_level)

                # If there was a parent wrap the current tag
                if parent_context and parent:
                    parent.append(copy_element)

                # get the top level tag so that we can print the whole context
                top_level_tag = copy_element
                while top_level_tag.parent is not None:
                    top_level_tag = top_level_tag.parent

                # remove all the dead tags so that the vector embedding is better
                SeleniumUtils.prune_empty_tags(top_level_tag)
                try:
                    element_context_html = str(top_level_tag)
                    # put the whole html as the key incontext_to_xpath_map = {dict: 1} {'<div class="main-header page-full-width section-wrapper"><div class="main-header-content page-centered narrow-section page-full-width"><a class="main-header-logo" href="https://jobs.lever.co/finix"></a></div></div>': '/html/body/div[1]/div/div/a'}
                    context_to_xpath_map[element_context_html] = element_xpath
                except:
                    SeleniumUtils.logger.error("Unable to get element Context html because element had structure broken, likely in prune method")


        selenium_elements = SeleniumUtils.get_selenium_elements_by_xpaths(driver, list(context_to_xpath_map.values()))
        if len(selenium_elements) != len(context_to_xpath_map.values()):
            raise Exception("Was not able to find all selenium elements for each critical Tag found in the html! Error could be that the xpath was invalid or the page changed!")

        context_to_selenium_element = {}
        context_list = list(context_to_xpath_map.keys())
        # Take out all the null values that we werent able to find with the xpath
        for index in range(len(selenium_elements)):
            if selenium_elements[index] != None:
                context_string = context_list[index]
                context_to_selenium_element[context_string] = selenium_elements[index]

        return context_to_selenium_element

    @staticmethod
    def recursive_soup_child_clearer(html_obj: Tag, level_to_keep = 0) -> None:
        '''
        Utility method that will clear a children elements off a given soup object after N levels.
        E.G.
        <div id="div1">
            <p>
                Cool stuff
                <a href=google.com>Click Me</a>
            <p>
        </div>
        -> level_to_keep - 0
        <div id="div1">
        </div>
        -> level_to_keep - 1
        <div id="div1">
            <p>
                Cool stuff
            <p>
        </div>
        -> level_to_keep - 2
        <div id="div1">
            <p>
                Cool stuff
                <a href=google.com>Click Me</a>
            <p>
        </div>
        :param html_obj: ONE element to clear N levels below must be a PageElement
        :param level_to_keep: how many levels lower than this object get cleared
        :return:
        '''
        if not html_obj or not isinstance(html_obj, Tag):
            return

        stack = [(html_obj, level_to_keep)]

        while stack:
            current_element, current_depth = stack.pop()

            # If depth is 0, clear all children of the current element
            if current_depth <= 0:
                current_element.clear()
                continue

            # Process children and add them to the stack with reduced depth
            for child in current_element.find_all(recursive=False):
                stack.append((child, current_depth - 1))

    @staticmethod
    def get_parent_tags_with_cleared_children(html_obj: Tag, levels: int) -> Tag:
        if not html_obj or not isinstance(html_obj, Tag) or levels < 0:
            return html_obj

        current_element = html_obj
        for parent_level in range(levels):
            if current_element.parent and isinstance(current_element.parent, Tag):
                parent = current_element.parent

                # Clear children but preserve the parent's attributes and siblings, but only clear down to the original tag level
                for child in parent.find_all(recursive=False):
                    # Dont clear the child data on the node that we are getting the parent context for
                    if child == html_obj:
                        continue
                    # keep the parent tags info, and clear to the same level below
                    SeleniumUtils.recursive_soup_child_clearer(child, parent_level)

                current_element = parent
            else:
                break

        return current_element.extract()

    @staticmethod
    def get_xpath_for_element(element: Tag):
        '''
        Utility method that returns a BeautifulSoup Tag's xpath so that we can easily execute selenium to get
        the element so we can interact with it.
        :param element:
        :return: absolute xpath using indexing E.G '/html[1]/body[1]/div[1]/div[1]/p[1]'
        '''
        path_parts = []

        # Traverse up the tree
        while element is not None and element.name != '[document]':
            parent = element.parent
            if parent is not None:
                # Count occurrences of the same tag type at this level
                siblings = parent.find_all(element.name, recursive=False)
                if len(siblings) > 1:
                    index = siblings.index(element) + 1  # XPath index is 1-based
                    path_parts.append(f"{element.name}[{index}]")
                else:
                    path_parts.append(element.name)

            element = parent

        return "/" + "/".join(reversed(path_parts))

    @staticmethod
    def get_css_selector(tag: Tag) -> str:
        '''
        Method to get a css_selector for a given tag so that we can retrieve it from the built parent later
        :param tag:
        :return:
        '''
        if not tag:
            return ""

        selector = tag.name  # Start with the tag name
        if tag.get('class'):  # Add class if it exists
            selector += '.' + '.'.join(tag['class'])
        if tag.get('id'):  # Add ID if it exists
            selector += f'#{tag["id"]}'
        return selector


    @staticmethod
    def get_selenium_elements_by_xpaths(driver, xpaths: List[str]) -> List[WebElement]:
        script = """
            var xpaths = arguments[0];
            var elements = [];
            for (var i = 0; i < xpaths.length; i++) {
                var result = document.evaluate(xpaths[i], document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                if (result.singleNodeValue) {
                    elements.push(result.singleNodeValue);
                } else {
                    elements.push(null)
                }
            }
            return elements;
            """
        return driver.execute_script(script, xpaths)

    @staticmethod
    def interact_with_element(element: WebElement, action: str = "click", text: str = None):
        """
        Interacts with a Selenium WebElement based on the specified action.

        :param element: The Selenium WebElement to interact with.
        :param action: The action to perform ("click", "send_keys", etc.).
        :param text: The text to send (only used for "send_keys" action).
        :except any selenium exceptions are passed up to caller
        """
        # Ensure the element is visible and interactable
        if not element.is_displayed() or not element.is_enabled():
            raise Exception(f"Element is not visible or not enabled: {element}")

        # Perform the specified action
        if action == "click":
            element.click()
        elif action == "send_keys":
            if text is None:
                raise Exception("No text provided for 'send_keys' action.")
            element.clear()
            element.send_keys(text)
        else:
            raise Exception(f"Unsupported action: {action}")

    @staticmethod
    def prune_empty_tags(tag: Tag) -> None:
        """Recursively remove empty tags, preserving the root."""
        if not isinstance(tag, Tag):
            return

        # Process children first (post-order traversal)
        for child in tag.find_all(recursive=False):
            SeleniumUtils.prune_empty_tags(child)  # Recurse into children

        # If the tag is now empty (no text and no non-empty children), decompose it
        if( not tag.get_text(strip=True) # No text content
                and not tag.attrs # No attributes like href or other things
                and not tag.find(recursive=False)  # No non-empty children
                and tag.parent is not None  # Don't decompose root tags
        ):
            tag.decompose()