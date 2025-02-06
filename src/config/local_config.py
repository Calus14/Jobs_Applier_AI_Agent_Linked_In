from pathlib import Path

#TODO Label all configs with comments/block of related comments to explain what they all do.

#config related to logging must have prefix LOG_
from src.utils.llm_utils.open_ai_action_wrapper import OpenAiActionWrapper
from src.utils.pydantic_utils import PydanticUtils

class LocalConfig:
    '''
    Class that allows a configuration to be set on a specific context. So that this application can easily scale horizontally
    if i ever make this work ubiquitosly and throw it on a app_service or eks

    NOTE: there is a global_config set that we are using to setup local tests and things... THIS IS NOT HOW IT WILL WORK
    IF WE SCALE.
    '''

    def __init__(self):
        # File directory configuration paths
        base_directory = Path(__file__).resolve().parent.parent.parent
        self.PROMPTS_DIRECTORY: Path = base_directory / "src" / "utils" / "llm_utils" / "prompts"
        self.LOG_OUTPUT_FILE_PATH: Path = Path("data_folder/output")
        self.VECTOR_OUTPUT_FILE_PATH: Path = Path("data_folder/query_vectors")

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


global_config = LocalConfig()
