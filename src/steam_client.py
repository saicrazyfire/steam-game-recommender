from steam.webapi import WebAPI
from dotenv import load_dotenv
import os
import httpx

load_dotenv()

def get_owned_games(steam_id: str):
    """
    Fetches the list of owned games for a given Steam ID.
    """
    api_key = os.getenv("STEAM_API_KEY")
    if not api_key:
        raise ValueError("STEAM_API_KEY is not set in the .env file.")

    # Instantiate the WebAPI object on-demand to avoid slow server startup
    api = WebAPI(key=api_key)

    try:
        # Use the dynamic WebAPI interface
        response = api.IPlayerService.GetOwnedGames(
            steamid=steam_id, 
            include_appinfo=True, 
            include_played_free_games=True,
            appids_filter=[],
            include_free_sub=True,
            language="en",
            include_extended_appinfo=False,
            format='json'  # Explicitly ask for JSON
        )
        
        # The actual game list is usually in response['response']['games']
        if 'response' in response and 'games' in response['response']:
            return response['response']
        else:
            # Handle cases where the library returns the raw response or an unexpected structure
            # Sometimes the game count is zero and 'games' is missing
            if 'response' in response and response['response'].get('game_count', 0) == 0:
                return {'game_count': 0, 'games': []}
            print("Error: 'games' key not found in Steam API response structure.")
            return None
    except Exception as e:
        # The library might raise an exception on HTTP errors (e.g., 403 Forbidden for a bad key)
        print(f"An error occurred while fetching games from Steam API: {e}")
        # The exception object from the library might have more details
        if hasattr(e, 'response') and e.response is not None:
            print(f"HTTP Status Code: {e.response.status_code}")
            print(f"Response Body: {e.response.text}")
        return None

async def get_game_details(appid: int):
    """
    Fetches details for a specific game from the public Steam store API.
    """
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            
            # The API returns a dictionary where the key is the appid as a string
            if str(appid) in data and data[str(appid)]['success']:
                return data[str(appid)]['data']
            else:
                return None
    except Exception as e:
        print(f"An error occurred while fetching game details for appid {appid}: {e}")
        return None

def get_player_summary(steam_id: str):
    """
    Fetches the public profile summary for a given Steam ID.
    """
    api_key = os.getenv("STEAM_API_KEY")
    if not api_key:
        raise ValueError("STEAM_API_KEY is not set in the .env file.")
    
    api = WebAPI(key=api_key)

    try:
        response = api.ISteamUser.GetPlayerSummaries(steamids=steam_id)
        if response['response']['players']:
            return response['response']['players'][0]
        return None
    except Exception as e:
        print(f"An error occurred while fetching player summary: {e}")
        return None
