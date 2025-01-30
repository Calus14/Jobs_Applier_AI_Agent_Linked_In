import json
import os.path
from datetime import datetime
from typing import Dict
from langchain_core.prompt_values import StringPromptValue
from langchain_openai import ChatOpenAI
from pathlib import Path

'''
Custom logger class so that all communications with 3rd party api's / OLLAMA models will have their own distinct logs.
'''
class LLMLogger:

    #Used so we can report how much we are costing per run
    total_run_cost = 0
    LOG_OUTPUT_FILE_PATH: Path = Path("data_folder/output")

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    @staticmethod
    def log_request(prompts, parsed_reply: Dict[str, Dict]):
        calls_log = LLMLogger.LOG_OUTPUT_FILE_PATH / "open_ai_calls.json"

        # Make the directory for logging if it does not exist yet.
        if not os.path.exists(LLMLogger.LOG_OUTPUT_FILE_PATH):
            os.makedirs("./"+LLMLogger.LOG_OUTPUT_FILE_PATH, exist_ok=True)

        if isinstance(prompts, StringPromptValue):
            prompts = prompts.text
        elif isinstance(prompts, Dict):
            # Convert prompts to a dictionary if they are not in the expected format
            prompts = {
                f"prompt_{i + 1}": prompt.content
                for i, prompt in enumerate(prompts.messages)
            }
        else:
            prompts = {
                f"prompt_{i + 1}": prompt.content
                for i, prompt in enumerate(prompts.messages)
            }

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Extract token usage details from the response
        token_usage = parsed_reply["usage_metadata"]
        output_tokens = token_usage["output_tokens"]
        input_tokens = token_usage["input_tokens"]
        total_tokens = token_usage["total_tokens"]

        LLMLogger.total_run_cost += total_tokens

        # Extract model details from the response
        model_name = parsed_reply["response_metadata"]["model_name"]

        # Create a log entry with all relevant information
        log_entry = {
            "model": model_name,
            "time": current_time,
            "prompts": prompts,
            "replies": parsed_reply["content"],  # Response content
            "total_tokens": total_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }

        # Write the log entry to the log file in JSON format
        with open(calls_log, "a", encoding="utf-8") as f:
            json_string = json.dumps(log_entry, ensure_ascii=False, indent=4)
            f.write(json_string + "\n")
