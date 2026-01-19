from abc import ABC, abstractmethod
from typing import List, Dict, Tuple
import os
from dotenv import load_dotenv
import httpx
import json
import tomli
import time

# Load environment variables
load_dotenv()

# Load configuration
def load_config():
    with open("config.toml", "rb") as f:
        return tomli.load(f)

config = load_config()

class AIRecommender(ABC):
    """
    Abstract base class for AI recommender services.
    Defines the interface for getting game recommendations.
    """
    @abstractmethod
    async def get_recommendations(self, game_data: List[Dict], user_prompt: str, custom_model: str = None, custom_prompt: str = None) -> Tuple[List[Dict], Dict]:
        """
        Generates a ranked list of game recommendations based on user's game data and a prompt.
        Returns the recommendations and performance metrics.
        """
        pass

    @abstractmethod
    async def surprise_me(self, game_data: List[Dict], user_prompt: str, custom_model: str = None, custom_prompt: str = None) -> Tuple[Dict, Dict]:
        """
        Generates a single, top-ranked game recommendation.
        Returns the recommendation and performance metrics.
        """
        pass

class OpenRouterRecommender(AIRecommender):
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY") or config.get('openrouter', {}).get('api_key')
        self.default_model = config.get('openrouter', {}).get('model', 'gryphe/mythomax-l2-13b')
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not set in the .env file or config.toml.")

    async def _call_api(self, messages: List[Dict], model_to_use: str) -> Tuple[Dict, float]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_to_use,
            "messages": messages,
            "response_format": {"type": "json_object"}
        }

        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                start_time = time.time()
                response = await client.post(self.base_url, headers=headers, json=payload)
                end_time = time.time()
                response.raise_for_status()
                response_time = end_time - start_time
                return response.json(), response_time
            except httpx.HTTPStatusError as e:
                print(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
                raise
            except httpx.RequestError as e:
                print(f"An error occurred while requesting {e.request.url!r}: {e}")
                raise

    def _create_system_prompt(self) -> str:
        try:
            with open("src/system_prompt.txt", "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            print("Error: src/system_prompt.txt not found.")
            return "You are a helpful game recommender." # Fallback prompt

    async def get_recommendations(self, game_data: List[Dict], user_prompt: str, custom_model: str = None, custom_prompt: str = None) -> Tuple[List[Dict], Dict]:
        model_to_use = custom_model if custom_model else self.default_model
        system_prompt = custom_prompt if custom_prompt else self._create_system_prompt()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"My game library data: {json.dumps(game_data)}. {user_prompt}"}
        ]
        response_json, response_time = await self._call_api(messages, model_to_use)
        
        metrics = {
            "response_time": response_time,
            "usage": response_json.get("usage", {})
        }
        
        try:
            content = json.loads(response_json['choices'][0]['message']['content'])
            recommendations = content.get('recommendations', [])
            return recommendations, metrics
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"Error parsing LLM response for recommendations: {e}")
            print(f"Raw LLM response: {response_json}")
            return [], metrics

    async def surprise_me(self, game_data: List[Dict], user_prompt: str, custom_model: str = None, custom_prompt: str = None) -> Tuple[Dict, Dict]:
        model_to_use = custom_model if custom_model else self.default_model
        system_prompt = custom_prompt if custom_prompt else self._create_system_prompt()
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"My game library data: {json.dumps(game_data)}. {user_prompt} Please recommend only one game."}
        ]
        response_json, response_time = await self._call_api(messages, model_to_use)

        metrics = {
            "response_time": response_time,
            "usage": response_json.get("usage", {})
        }

        try:
            content = json.loads(response_json['choices'][0]['message']['content'])
            recommendations = content.get('recommendations', [])
            first_rec = recommendations[0] if recommendations else {}
            return first_rec, metrics
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"Error parsing LLM response for surprise me: {e}")
            print(f"Raw LLM response: {response_json}")
            return {}, metrics


class AzureOpenAIRecommender(AIRecommender):
    def __init__(self):
        pass

    async def get_recommendations(self, game_data: List[Dict], user_prompt: str, custom_model: str = None, custom_prompt: str = None) -> Tuple[List[Dict], Dict]:
        print("AzureOpenAIRecommender not yet implemented.")
        return [], {}

    async def surprise_me(self, game_data: List[Dict], user_prompt: str, custom_model: str = None, custom_prompt: str = None) -> Tuple[Dict, Dict]:
        print("AzureOpenAIRecommender not yet implemented.")
        return {}, {}


class OpenAIRecommender(AIRecommender):
    def __init__(self):
        pass

    async def get_recommendations(self, game_data: List[Dict], user_prompt: str, custom_model: str = None, custom_prompt: str = None) -> Tuple[List[Dict], Dict]:
        print("OpenAIRecommender not yet implemented.")
        return [], {}

    async def surprise_me(self, game_data: List[Dict], user_prompt: str, custom_model: str = None, custom_prompt: str = None) -> Tuple[Dict, Dict]:
        print("OpenAIRecommender not yet implemented.")
        return {}, {}


def get_recommender(provider_name: str) -> AIRecommender:
    """
    Factory function to get the appropriate AI recommender instance.
    """
    if provider_name.lower() == "openrouter":
        return OpenRouterRecommender()
    elif provider_name.lower() == "azureopenai":
        return AzureOpenAIRecommender()
    elif provider_name.lower() == "openai":
        return OpenAIRecommender()
    else:
        raise ValueError(f"Unknown AI recommender provider: {provider_name}")
