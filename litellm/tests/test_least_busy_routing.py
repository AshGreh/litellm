#### What this tests ####
#    This tests the router's ability to identify the least busy deployment

import sys, os, asyncio, time
import traceback
from dotenv import load_dotenv

load_dotenv()
import os

sys.path.insert(
    0, os.path.abspath("../..")
)  # Adds the parent directory to the system path
import pytest
from litellm import Router
import litellm
from litellm.router_strategy.least_busy import LeastBusyLoggingHandler
from litellm.caching import DualCache

### UNIT TESTS FOR LEAST BUSY LOGGING ###


def test_model_added():
    test_cache = DualCache()
    least_busy_logger = LeastBusyLoggingHandler(router_cache=test_cache)
    kwargs = {
        "litellm_params": {
            "metadata": {
                "model_group": "gpt-3.5-turbo",
                "deployment": "azure/chatgpt-v-2",
            },
            "model_info": {"id": "1234"},
        }
    }
    least_busy_logger.log_pre_api_call(model="test", messages=[], kwargs=kwargs)
    request_count_api_key = f"gpt-3.5-turbo_request_count"
    assert test_cache.get_cache(key=request_count_api_key) is not None


def test_get_available_deployments():
    test_cache = DualCache()
    least_busy_logger = LeastBusyLoggingHandler(router_cache=test_cache)
    model_group = "gpt-3.5-turbo"
    deployment = "azure/chatgpt-v-2"
    kwargs = {
        "litellm_params": {
            "metadata": {
                "model_group": model_group,
                "deployment": deployment,
            },
            "model_info": {"id": "1234"},
        }
    }
    least_busy_logger.log_pre_api_call(model="test", messages=[], kwargs=kwargs)
    request_count_api_key = f"{model_group}_request_count"
    assert test_cache.get_cache(key=request_count_api_key) is not None
    print(least_busy_logger.get_available_deployments(model_group=model_group))


# test_get_available_deployments()


def test_router_get_available_deployments():
    """
    Tests if 'get_available_deployments' returns the least busy deployment
    """
    model_list = [
        {
            "model_name": "azure-model",
            "litellm_params": {
                "model": "azure/gpt-turbo",
                "api_key": "os.environ/AZURE_FRANCE_API_KEY",
                "api_base": "https://openai-france-1234.openai.azure.com",
                "rpm": 1440,
            },
            "model_info": {"id": 1},
        },
        {
            "model_name": "azure-model",
            "litellm_params": {
                "model": "azure/gpt-35-turbo",
                "api_key": "os.environ/AZURE_EUROPE_API_KEY",
                "api_base": "https://my-endpoint-europe-berri-992.openai.azure.com",
                "rpm": 6,
            },
            "model_info": {"id": 2},
        },
        {
            "model_name": "azure-model",
            "litellm_params": {
                "model": "azure/gpt-35-turbo",
                "api_key": "os.environ/AZURE_CANADA_API_KEY",
                "api_base": "https://my-endpoint-canada-berri992.openai.azure.com",
                "rpm": 6,
            },
            "model_info": {"id": 3},
        },
    ]
    router = Router(
        model_list=model_list,
        routing_strategy="least-busy",
        set_verbose=False,
        num_retries=3,
    )  # type: ignore

    router.leastbusy_logger.test_flag = True

    model_group = "azure-model"
    deployment = "azure/chatgpt-v-2"
    request_count_dict = {1: 10, 2: 54, 3: 100}
    cache_key = f"{model_group}_request_count"
    router.cache.set_cache(key=cache_key, value=request_count_dict)

    deployment = router.get_available_deployment(model=model_group, messages=None)
    print(f"deployment: {deployment}")
    assert deployment["model_info"]["id"] == 1

    ## run router completion - assert completion event, no change in 'busy'ness once calls are complete

    router.completion(
        model=model_group,
        messages=[{"role": "user", "content": "Hey, how's it going?"}],
    )

    return_dict = router.cache.get_cache(key=cache_key)

    assert router.leastbusy_logger.logged_success == 1
    assert return_dict[1] == 10
    assert return_dict[2] == 54
    assert return_dict[3] == 100


# test_router_get_available_deployments()
