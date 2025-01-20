
'''
This class is meant to be Plain Old Python Object that holds all information needed to make decisions on a job posting,
and to follow the job posting and save/load it to a database
'''
class JobPosting:
    html_body: object
    url_link: str
    match_score: float
    date_created: str
    applied_to_job: bool

