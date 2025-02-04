import time
import openai
from colorama import Fore
from config import Config

cfg = Config()

openai.api_key = cfg.openai_api_key


# Overly simple abstraction until we create something better
# simple retry mechanism when getting a rate error or a bad gateway
def create_chat_completion(messages, model=None, temperature=cfg.temperature, max_tokens=None)->str:
    """Create a chat completion using the OpenAI API"""
    response = None
    num_retries = 5
    for attempt in range(num_retries):
        try:
            if cfg.use_azure:
                response = openai.ChatCompletion.create(
                    deployment_id=cfg.get_azure_deployment_id_for_model(model),
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            else:
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            break
        except openai.error.RateLimitError:
            if cfg.debug_mode:
                print(Fore.RED + "Error: ", "API Rate Limit Reached. Waiting 20 seconds..." + Fore.RESET)
            time.sleep(20)
        except openai.error.APIError as e:
            if e.http_status == 502:
                if cfg.debug_mode:
                    print(Fore.RED + "Error: ", "API Bad gateway. Waiting 20 seconds..." + Fore.RESET)
                time.sleep(20)
            else:
                raise
            if attempt == num_retries - 1:
                raise

    if response is None:
        raise RuntimeError("Failed to get response after 5 retries")
    
    tokens = response["usage"]["total_tokens"]
    if model == cfg.fast_llm_model:
        cost = tokens * (0.002 / 1000)
    else:
        cost = tokens * (0.045 / 1000)

    print("Approximate cost of current operation: ${:.4f}".format(cost))

    return response.choices[0].message["content"]
