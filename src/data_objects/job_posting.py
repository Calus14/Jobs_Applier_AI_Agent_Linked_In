from datetime import datetime
'''
This class is meant to be Plain Old Python Object that holds all information needed to make decisions on a job posting,
and to follow the job posting and save/load it to a database
'''
class JobPosting:
    html_string: str
    url_link: str
    #percent from 0-100%
    interview_chance: int
    hired_chance: int

    date_created: str
    applied_to_job: bool

    def __init__(self, html_string, url_link, interview_chance, hired_chance, date_created=datetime.now().strftime("%m/%d/%Y"), applied_to_job=False):
        self.html_string = html_string
        self.url_link = url_link

        self.interview_chance = interview_chance
        self.hired_chance = hired_chance

        self.date_created = date_created
        self.applied_to_job = applied_to_job

