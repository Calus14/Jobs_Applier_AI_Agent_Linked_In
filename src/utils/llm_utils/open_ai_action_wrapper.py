import openai
import time
from typing import Dict, List
from langchain_core.messages.ai import AIMessage
from langchain_openai import ChatOpenAI
from local_config import global_config
from loguru import logger
from requests.exceptions import HTTPError as HTTPStatusError
from src.utils.llm_utils.llm_logger import LLMLogger

"""
This module contains a class that wraps the ChatOpenAi object and provides wrapper functions to simplify calling
chat GPT models
"""

class OpenAiActionWrapper:

    def __init__(self, llm: ChatOpenAI, enable_logging=True):
        self.llm = llm
        self.logging = enable_logging

    def __call__(self, messages: List[Dict[str, str]]) -> str:
        for attempt in range(global_config.MAX_OPEN_AI_RETRIES):
            try:
                reply = self.llm.invoke(messages)
                parsed_reply = self.parse_llmresult(reply)
                if self.logging:
                    LLMLogger.log_request(prompts=messages, parsed_reply=parsed_reply)
                return reply
            except (openai.RateLimitError, HTTPStatusError) as err:
                if isinstance(err, HTTPStatusError) and err.response.status_code == 429:
                    logger.warning(f"HTTP 429 Too Many Requests: Waiting for {global_config.OPEN_AI_DELAY} seconds before retrying (Attempt {attempt + 1}/{global_config.MAX_OPEN_AI_RETRIES})...")
                    time.sleep(global_config.OPEN_AI_DELAY)
                else:
                    wait_time = self.parse_wait_time_from_error_message(str(err))
                    logger.warning(f"Rate limit exceeded or API error. Waiting for {wait_time} seconds before retrying (Attempt {attempt + 1}/{global_config.MAX_OPEN_AI_RETRIES})...")
                    time.sleep(wait_time)
            except Exception as e:
                logger.error(f"Unexpected error occurred: {str(e)}, retrying in {global_config.OPEN_AI_DELAY} seconds... (Attempt {attempt + 1}/{global_config.MAX_OPEN_AI_RETRIES})")
                time.sleep(global_config.OPEN_AI_DELAY)

        logger.critical("Failed to get a response from the model after multiple attempts.")
        raise Exception("Failed to get a response from the model after multiple attempts.")

    def parse_llmresult(self, llmresult: AIMessage) -> Dict[str, Dict]:
        # Parse the LLM result into a structured format.
        content = llmresult.content
        response_metadata = llmresult.response_metadata
        id_ = llmresult.id
        usage_metadata = llmresult.usage_metadata

        parsed_result = {
            "content": content,
            "response_metadata": {
                "model_name": response_metadata.get("model_name", ""),
                "system_fingerprint": response_metadata.get("system_fingerprint", ""),
                "finish_reason": response_metadata.get("finish_reason", ""),
                "logprobs": response_metadata.get("logprobs", None),
            },
            "id": id_,
            "usage_metadata": {
                "input_tokens": usage_metadata.get("input_tokens", 0),
                "output_tokens": usage_metadata.get("output_tokens", 0),
                "total_tokens": usage_metadata.get("total_tokens", 0),
            },
        }
        return parsed_result