import logging
from pathlib import Path
from local_config import global_config
from src.utils.config_validator import ConfigValidator, ConfigError
from test.open_ai_tests import OpenAiTests

logger = logging.getLogger("test_main")
logging.basicConfig()
logging.root.setLevel(logging.DEBUG)

def run_integration_tests():

    try:
        # Define and validate the data folder
        data_folder = Path("data_folder")
        secrets_file, config_file, plain_text_resume_file, output_folder = ConfigValidator.validate_data_folder(data_folder)

        # Validate configuration and secrets
        config = ConfigValidator.validate_config(config_file)
        secrets = ConfigValidator.validate_secrets(secrets_file)
        global_config.API_KEY = secrets["llm_api_key"]
        global_config.LINKEDIN_EMAIL = secrets["linkedin_email"]
        global_config.LINKEDIN_PASSWORD = secrets["linkedin_password"]
    except ConfigError as ce:
        logger.error(f"Configuration error: {ce}")
        logger.error(
            "Refer to the configuration guide for troubleshooting on this projects github readme!"
        )
    except FileNotFoundError as fnf:
        logger.error(f"File not found: {fnf}")
        logger.error("Ensure all required files are present in the data folder.")
    except RuntimeError as re:
        logger.error(f"Runtime error: {re}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")

    """Main entry point for all integration tests that validate our connections to 3rd party apis"""
    OpenAiTests().test_open_ai_wrapper_can_ask_questions()



if __name__ == "__main__":
    run_integration_tests()