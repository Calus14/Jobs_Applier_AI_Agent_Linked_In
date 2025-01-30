# In this file, you can set the configurations of the app.
import logging
from pathlib import Path

#TODO Label all configs with comments/block of related comments to explain what they all do.

#config related to logging must have prefix LOG_
from src.utils.llm_utils.open_ai_action_wrapper import OpenAiActionWrapper
from src.utils.pydantic_utils import PydanticUtils

LOG_TO_FILE = True
LOG_TO_CONSOLE = True
LOG_LEVEL = logging.INFO

class LocalLogging():
    @staticmethod
    def get_local_logger(logger_name: str):
        logger = logging.getLogger(logger_name)
        logger.setLevel(LOG_LEVEL)  # Set the logging level to INFO

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        if LOG_TO_FILE:
            file_handler = logging.FileHandler('local_logs.log', 'w')  # Log to a file named 'app.log'
            file_handler.setLevel(LOG_LEVEL)  # Set the file handler level to INFO
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        if LOG_TO_CONSOLE:
            console_handler = logging.StreamHandler()  # Log to the console
            console_handler.setLevel(logging.INFO)  # Set the console handler level to INFO
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        return logger


class GlobalConfig:
    def __init__(self):
        # File directory configuration paths
        base_directory = Path(__file__).resolve().parent
        self.ASSETS_DIRECTORY: Path = base_directory / "assets"
        self.STYLES_RESUME_DIRECTORY: Path = self.ASSETS_DIRECTORY / "styles" / "resumes"
        self.STYLES_RESUME_DIRECTORY: Path = self.ASSETS_DIRECTORY / "styles" / "cover_letters"
        self.PROMPTS_DIRECTORY: Path = base_directory / "src" / "utils" / "llm_utils" / "prompts"
        self.LOG_OUTPUT_FILE_PATH: Path = Path("data_folder/output")

        # Job board specific configurations
        self.LINKEDIN_EMAIL: str = ''
        self.LINKEDIN_PASSWORD: str = ''

        self.DEFAULT_EMAIL: str = ''
        self.DEFAULT_PASSWORD: str = ''

        #User Specific configuration
        self.RESUME = None
        self.RESUME_FLATTENED_MAP = None
        self.RESUME_EMBEDDED_VECTOR_MAP = None

        # AI Configuration
        self.API_KEY: str = ''
        self.LLM_MODEL_TYPE = 'openai'
        self.LLM_MODEL = 'gpt-4o-mini'
        # Variable that controls the randomness of the model's outputs, going from 0.0-2.0
        self.LLM_TEMPERATURE = 0.7
        # Only required for OLLAMA models
        self.LLM_API_URL = ''

        self.AI_MODEL = None



        self.html_template = """
                            <!DOCTYPE html>
                            <html lang="en">
                            <head>
                                <meta charset="UTF-8">
                                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                                <title>Resume</title>
                                <link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;600&display=swap" rel="stylesheet" />
                                <link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;600&display=swap" rel="stylesheet" /> 
                                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css" /> 
                                    <style>
                                        $style_css
                                    </style>
                            </head>
                            <body>
                            $body
                            </body>
                            </html>
                            """

    def get_user_resume_as_embedded_vector_map(self, model):
        if type(self.AI_MODEL) is not OpenAiActionWrapper:
            raise Exception("Unable to get user resume as embedded vector map. This is because we were expecting an AI "
                            + " model of type OpenAiEmbeddings! Configured AI Model is - "
                            + str(type(global_config.AI_MODEL)))
        if not self.RESUME:
            raise Exception("Unable to get user resume as embedded vector map because there is no resume configured on global configs for the application!")

        # Only get the resume one time
        if not self.RESUME_FLATTENED_MAP:
            self.RESUME_FLATTENED_MAP = PydanticUtils.flatten_model(self.RESUME)

        # Only embedd the resume keys one time:
        if not self.RESUME_EMBEDDED_VECTOR_MAP:
            resume_info_keys = list(self.RESUME_FLATTENED_MAP.keys())
            keys_as_embedded_vectors = self.AI_MODEL.embed_documents(resume_info_keys)
            self.RESUME_EMBEDDED_VECTOR_MAP = {
                key : vector for key, vector in zip(resume_info_keys, keys_as_embedded_vectors)
            }

        return self.RESUME_EMBEDDED_VECTOR_MAP


global_config = GlobalConfig()
