from src.data_objects.job_posting import JobPosting
from src.data_objects.resume import Resume

class ApplicationJobConfigs:
    '''
    This class is meant to be Plain Old Python Object that holds all information needed to spin up a selenium session and
    attempt to applie to a Job Posting.
    '''

    job_posting: JobPosting
    resume: Resume


