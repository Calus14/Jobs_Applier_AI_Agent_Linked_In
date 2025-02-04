import os
import traceback
from typing import List

from anyio import Path

from src.config.local_config import LocalConfig
from src.config.local_logging import LocalLogging
from src.data_objects.job_posting import JobPosting
from src.data_objects.resume import Resume
from src.utils.config_validator import ConfigValidator, ConfigError
from src.utils.web_scrapping.hcm.hcm_crawler import HcmCrawler
from src.utils.web_scrapping.hcm.vector_store_hcm_crawler import VectorStoreHcmCrawler
from src.utils.web_scrapping.job_boards.job_board_browser import JobBoardBrowser


class ApplyForJobs:
    '''
    This class wraps the ability to apply for jobs via a given Hcm Crawler class.
    the main point of wrapping this in a process is so that we can easily add other likeable features such as persisting
    all jobs that we have applied for, emailing when a job applicaiton is done, avoiding applying the same job for a user.
    etc.

    '''
    def __init__(self, driver, hcm_crawler_class, job_postings: List[JobPosting], local_config: LocalConfig, ai_model):
        self.driver = driver
        self.hcm_crawler_class = hcm_crawler_class
        self.job_postings = job_postings
        self.ai_model = ai_model
        self.local_config = local_config
        self.applied_jobs = []
        self.failed_jobs = []
        self.logger = LocalLogging.get_local_logger("apply_for_jobs_process")

    def validate_should_apply_for_jobs(self):
        '''
        Method that runs any specific pre-checks on the job postings given the configuration they were obtained with.
        I.E. in the future checking to see if the user has ever applied to that job before
        '''
        #TODO
        pass

    def apply_for_jobs(self):
        '''
        Applies for all jobs that still remain on this process.

        '''

        for posting in self.job_postings:
            try:
                self.logger.info(f"Found a job posting with url {posting.url_link} and we have a {posting.interview_chance} of getting an interview and {posting.hired_chance} of getting hired")
                posting_crawler = self.hcm_crawler_class(self.driver, posting, self.ai_model)
                posting_crawler.do_application_flow()
                posting_crawler.close_browser()
                if posting_crawler.internal_state == HcmCrawler.State.SUBMITTED_APPLICATION:
                    self.applied_jobs.append(posting)
                else:
                    self.applied_jobs.append(posting)
            except Exception as e:
                self.logger.error(e)
                self.logger.error(traceback.format_exc())
                self.applied_jobs.append(posting)
        if (self.hcm_crawler_class == VectorStoreHcmCrawler):
            VectorStoreHcmCrawler.dump_average_prompt_scores()

    def save_jobs_applied_to(self):
        '''
        Method that uses whatever persistence method we so chose to save jobs that we have applied to
        '''
        #TODO
        pass

    def save_jobs_failed_applied_to(self):
        '''
        Method that uses whatever persistence method we so chose to save jobs that we have applied to
        '''
        #TODO
        pass