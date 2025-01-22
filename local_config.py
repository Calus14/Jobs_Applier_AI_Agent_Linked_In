# In this file, you can set the configurations of the app.
from pathlib import Path
from src.utils.constants import DEBUG, ERROR, LLM_MODEL, OPENAI

#TODO Label all configs with comments/block of related comments to explain what they all do.

#config related to logging must have prefix LOG_
LOG_LEVEL = ERROR
LOG_SELENIUM_LEVEL = ERROR
LOG_TO_FILE = False
LOG_TO_CONSOLE = False

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

        #User Specific configuration
        self.RESUME = None

        # AI Configuration
        self.API_KEY: str = ''
        self.LLM_MODEL_TYPE = 'openai'
        self.LLM_MODEL = 'gpt-4o'
        # Variable that controls the randomness of the model's outputs, going from 0.0-2.0
        self.LLM_TEMPERATURE = 0.7
        # Only required for OLLAMA models
        self.LLM_API_URL = ''

        self.AI_MODEL = None

        # This controls how many times we attempt to contact openAI to get an answer before declaring it an error
        self.MAX_OPEN_AI_RETRIES = 15
        # This is how long we wait for a 200 response from openAI before declaring it timeout'd
        self.OPEN_AI_DELAY = 10

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

global_config = GlobalConfig()
