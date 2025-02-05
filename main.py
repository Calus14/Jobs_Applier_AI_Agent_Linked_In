import argparse
import os
import traceback


from pathlib import Path
from typing import List

from langchain_openai import ChatOpenAI
from src.config.local_config import global_config
from src.config.local_logging import LocalLogging
from src.data_objects.job_posting import JobPosting
from src.data_objects.resume import Resume

from src.processes.apply_for_jobs import ApplyForJobs
from src.processes.build_embedded_vector_manually import BuildEmbeddedVectorManually
from src.processes.find_jobs_for_user import FindJobsForUser
from src.utils.config_validator import ConfigValidator, ConfigError
from src.utils.llm_utils.llm_logger import LLMLogger
from src.utils.llm_utils.open_ai_action_wrapper import OpenAiActionWrapper
from src.utils.web_scrapping.hcm.vector_store_hcm_crawler import VectorStoreHcmCrawler
from src.utils.web_scrapping.job_boards.linked_in_board_browser import LinkedInBoardBrowser
from src.utils.web_scrapping.web_driver_factory import WebDriverFactory

main_logger = LocalLogging.get_local_logger("main_script.py")

def load_config():
    try:
        # Define and validate the data folder
        data_folder = Path("data_folder")
        secrets_file, config_file, plain_text_resume_file, output_folder = ConfigValidator.validate_data_folder(data_folder)

        # Validate configuration and secrets
        config = ConfigValidator.validate_config(config_file)
        secrets = ConfigValidator.validate_secrets(secrets_file)
        global_config.API_KEY = secrets["llm_api_key"]
        # NEEDED for some Open AI libraries to be on the OS path like Embeddings
        os.environ["OPENAI_API_KEY"] = global_config.API_KEY
        global_config.LINKEDIN_EMAIL = secrets["linkedin_email"]
        global_config.LINKEDIN_PASSWORD = secrets["linkedin_password"]
        global_config.DEFAULT_EMAIL = secrets["default_account_email"]
        global_config.DEFAULT_PASSWORD = secrets["default_account_password"]
        global_config.WORK_PREFS = config

        with open(plain_text_resume_file, "r", encoding="utf-8") as file:
            plain_text_resume = file.read()
            global_config.RESUME = Resume(plain_text_resume)

        return config

    except ConfigError as ce:
        main_logger.error(f"Configuration error: {ce}")
        main_logger.error(
            "Refer to the configuration guide for troubleshooting on this projects github readme!"
        )
    except FileNotFoundError as fnf:
        main_logger.error(f"File not found: {fnf}")
        main_logger.error("Ensure all required files are present in the data folder.")
    except RuntimeError as re:
        main_logger.error(f"Runtime error: {re}")
        main_logger.debug(traceback.format_exc())
    except Exception as e:
        main_logger.exception(f"An unexpected error occurred: {e}")

def main():
    # Create the parser
    parser = argparse.ArgumentParser(description="Application that will automatically search job boards and apply for jobs"
                                                 + " that fit your experience based on what AI thinks you are a good fit for.")
    # Add arguments
    parser.add_argument("--max-applies", type=int, help="How many jobs to apply too.", default=10)
    parser.add_argument("--max-page-depth", type=int, help="How many pages will we search for each position you list.", default=5)
    # Parse the arguments
    args = parser.parse_args()

    config = load_config()

    # In the future set the model based on a config that is passed in.
    global_config.AI_MODEL = OpenAiActionWrapper(
        ChatOpenAI(
            model_name=global_config.LLM_MODEL, openai_api_key=global_config.API_KEY, temperature=global_config.LLM_TEMPERATURE
        ),
        enable_logging=True
    )

    data_folder = Path("data_folder")
    secrets_file, work_prefs, plain_text_resume_file, output_folder = ConfigValidator.validate_data_folder(data_folder)

    # DEVELOPER TOOL SECTION, ENABLE OR DISABLE BY COMMENTING OUT
    most_likely_postings = temp_load_job_postings()
    list_of_urls = [x.url_link for x in most_likely_postings]
    manual_vector_builder = BuildEmbeddedVectorManually(WebDriverFactory().get_chrome_web_driver(),
                                                        global_config.AI_MODEL,
                                                        list_of_urls,
                                                        "test_vector")
    manual_vector_builder.collect_average_vector_over_urls()


    # try:
    #     linked_in_board_browser = LinkedInBoardBrowser(driver=WebDriverFactory().get_chrome_web_driver())
    #     find_job_process = FindJobsForUser(linked_in_board_browser, global_config.AI_MODEL)
    #     find_job_process.configure_for_user(secrets_file, plain_text_resume_file, work_prefs)
    #     job_postings = find_job_process.find_jobs_for_user()
    #
    #     # temp_save_job_postings(job_postings)
    #     most_likely_postings = temp_load_job_postings()
    #     apply_for_jobs = ApplyForJobs(WebDriverFactory().get_chrome_web_driver(),
    #                                   VectorStoreHcmCrawler,
    #                                   most_likely_postings,
    #                                   find_job_process.local_config,
    #                                   find_job_process.ai_model)
    #     apply_for_jobs.validate_should_apply_for_jobs()
    #     apply_for_jobs.apply_for_jobs()
    #     apply_for_jobs.save_jobs_applied_to()
    #     apply_for_jobs.save_jobs_failed_applied_to()
    #
    # except Exception as e:
    #     main_logger.error(e)
    # finally:
    #     VectorStoreHcmCrawler.dump_average_prompt_scores()

    main_logger.info(f"Finished running the applicaiton and spent a total of {LLMLogger.total_run_cost} credits")


def tempt_save_job_postings(jobs_postings):
    postings_file = global_config.LOG_OUTPUT_FILE_PATH / "job_postings.json"
    with open(postings_file, "a") as file:
        file.write("\n\n----------------------------------------\n\n")
        for posting in jobs_postings:
            file.write(posting.url_link + "\n")

def temp_load_job_postings() -> List[JobPosting]:
    postings = []
    postings_file = global_config.LOG_OUTPUT_FILE_PATH / "job_postings.json"
    with open(postings_file, "r") as file:
        for line in file:
            job_url = file.readline()
            postings.append(JobPosting(html_string=line,
                                        url_link= job_url.strip(),
                                        interview_chance=100, hired_chance=100))
    return postings


def tempt_save_job_postings(jobs_postings):
    postings_file = global_config.LOG_OUTPUT_FILE_PATH / "job_postings.json"
    with open(postings_file, "a") as file:
        file.write("\n\n----------------------------------------\n\n")
        for posting in jobs_postings:
            file.write(posting.url_link + "\n")

def temp_load_job_postings() -> List[JobPosting]:
    postings = []
    postings_file = global_config.LOG_OUTPUT_FILE_PATH / "job_postings.json"
    with open(postings_file, "r") as file:
        for line in file:
            job_url = file.readline()
            postings.append(JobPosting(html_string="",
                                      url_link= job_url.strip(),
                                      interview_chance=100, hired_chance=100))
    return postings

if __name__ == "__main__":
    main()
