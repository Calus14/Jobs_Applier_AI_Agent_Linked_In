import openai
import time
from typing import Dict, List

from langchain_community.callbacks import get_openai_callback
from langchain_core.messages.ai import AIMessage
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from loguru import logger
from requests.exceptions import HTTPError as HTTPStatusError
from src.utils.llm_utils.llm_logger import LLMLogger

"""
This module contains a class that wraps the ChatOpenAi object and provides wrapper functions to simplify calling
chat GPT models
"""

class OpenAiActionWrapper:
    # This controls how many times we attempt to contact openAI to get an answer before declaring it an error
    MAX_OPEN_AI_RETRIES = 3

    # This is how long we wait for a 200 response from openAI before declaring it timeout'd
    OPEN_AI_DELAY = 10

    def __init__(self, llm: ChatOpenAI, enable_logging=True):
        self.llm = llm
        self.logging = enable_logging
        self.embedded_dictionary = {}
        self.embeddings = None

    def __call__(self, messages: List[Dict[str, str]]) -> str:
        for attempt in range(OpenAiActionWrapper.MAX_OPEN_AI_RETRIES):
            try:
                #This is calling the open AI api with a
                reply = self.llm.invoke(messages)
                parsed_reply = self.parse_llmresult(reply)
                if self.logging:
                    LLMLogger.log_request(prompts=messages, parsed_reply=parsed_reply)
                return reply
            except (openai.RateLimitError, HTTPStatusError) as err:
                if isinstance(err, HTTPStatusError) and err.response.status_code == 429:
                    logger.warning(f"HTTP 429 Too Many Requests: Waiting for {OpenAiActionWrapper.OPEN_AI_DELAY} seconds before retrying (Attempt {attempt + 1}/{OpenAiActionWrapper.MAX_OPEN_AI_RETRIES})...")
                    time.sleep(OpenAiActionWrapper.OPEN_AI_DELAY)
                else:
                    wait_time = self.parse_wait_time_from_error_message(str(err))
                    logger.warning(f"Rate limit exceeded or API error. Waiting for {wait_time} seconds before retrying (Attempt {attempt + 1}/{OpenAiActionWrapper.MAX_OPEN_AI_RETRIES})...")
                    time.sleep(wait_time)
            except Exception as e:
                logger.error(f"Unexpected error occurred: {str(e)}, retrying in {OpenAiActionWrapper.OPEN_AI_DELAY} seconds... (Attempt {attempt + 1}/{OpenAiActionWrapper.MAX_OPEN_AI_RETRIES})")
                time.sleep(OpenAiActionWrapper.OPEN_AI_DELAY)

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

    def embed_string(self, string_to_embed :str):
        '''
        Utility method that takes a string and converts it to an AI representation so that which is a vector or weights
        that represent what that string represents.

        :param string: The string that we wish to "squish" via embedding
        :return vector embedding of string
        '''
        if not self.embeddings:
            self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small", )

        with get_openai_callback() as cb:
            embedded_vector = self.embeddings.embed_query(string_to_embed)
            LLMLogger.total_run_cost += cb.total_tokens

        return embedded_vector

    def embed_documents(self, documents: list[str]):
        '''
        Wrapper for calling embeddings on multiple documents at a time
        :param documents: the strings you wish to embed
        :return: dictionary of embeddings
        '''
        if not self.embeddings:
            self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small", )

        with get_openai_callback() as cb:
            embedded_vectors = self.embeddings.embed_documents(documents)
            LLMLogger.total_run_cost += cb.total_tokens

        return embedded_vectors