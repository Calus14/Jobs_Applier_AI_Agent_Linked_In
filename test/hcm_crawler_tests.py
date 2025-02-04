import unittest
import logging
import os
from pathlib import Path
from src.utils.config_validator import ConfigValidator, ConfigError
from src.config.local_config import global_config


class HcmCrawlerTests(unittest.TestCase):
    logger = logging.getLogger("hcm_crawler_tests")

    '''
    Tests that validate that state machine for the HCM crawler works as expected
    '''
    def test_hcm_handles_unstarted_right(self):
        #TODO Mockito like test that validate a HCM is doing the correct flow.
        pass
