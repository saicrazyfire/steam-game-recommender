import os
import time
from typing import Dict, List

import httpx
import tomli
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from src import database
from src.hltb_client import get_hltb_stats
from src.recommender import AIRecommender, get_recommender

# Local imports
from src.steam_client import get_game_details, get_owned_games, get_player_summary

# --- Caches ---
hltb_cache = {}
steam_cache = {}
app_details_cache = {}
CACHE_EXPIRATION = 3600  # Cache for 1 hour

load_dotenv()

# Load main config
with open("config.toml", "rb") as f:
    config = tomli.load(f)

app = FastAPI()


@app.on_event("startup")
async def startup_event():
    """Initializes the database on application startup."""
    database.initialize_db()


# --- App Setup ---
app.add_middleware(
    SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "my_secret_key")
)
templates = Jinja2Templates(directory="src/templates")
recommender_provider = config["recommender"]["provider"]
ai_recommender: AIRecommender = get_recommender(recommender_provider)


# --- Pydantic Models ---
class GameExclusionRequest(BaseModel):
    appid: int


# --- HTML Endpoints ---
@app.get("/")
async def home(request: Request):
    user = request.session.get("user")
    last_refreshed = "Never"
    if user and (steam_id := user.get("steam_id")):
        cached_data = steam_cache.get(steam_id)
        if cached_data:
            ts = cached_data["timestamp"]
            last_refreshed = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))

    default_model = config.get("openrouter", {}).get("model", "gryphe/mythomax-l2-13b")
    try:
        with open("src/system_prompt.txt", "r", encoding="utf-8") as f:
            default_prompt = f.read()
    except FileNotFoundError:
        default_prompt = "You are a helpful game recommender."

    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "user": user,
            "default_model": default_model,
            "default_prompt": default_prompt,
            "last_refreshed": last_refreshed,
        },
    )

@app.get("/health")
async def health(request: Request):
    return JSONResponse(status_code=200, content={"ok": True})


# --- Auth Endpoints ---
@app.get("/login")
async def login_with_steam():
    # ... (implementation is correct, keeping it short for brevity)
    steam_login_url = "https://steamcommunity.com/openid/login"
    app_url = os.getenv("APP_URL", "http://127.0.0.1:8000")
    params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "checkid_setup",
        "openid.return_to": f"{app_url}/auth/steam/callback",
        "openid.realm": f"{app_url}",
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
    }
    redirect_url = (
        f"{steam_login_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    )
    return RedirectResponse(url=redirect_url)


@app.get("/auth/steam/callback")
async def auth_steam_callback(request: Request):
    # ... (implementation is correct, keeping it short for brevity)
    params = dict(request.query_params)
    params["openid.mode"] = "check_authentication"
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://steamcommunity.com/openid/login", data=params
        )
    if "is_valid:true" in response.text:
        steam_id = params["openid.claimed_id"].split("/")[-1]

        # Fetch user summary to get persona name
        summary = get_player_summary(steam_id)
        persona_name = (
            summary.get("personaname", "Unknown User") if summary else "Unknown User"
        )

        request.session["user"] = {"steam_id": steam_id, "persona_name": persona_name}
        return RedirectResponse(url="/")
    else:
        return JSONResponse(
            {"status": "error", "message": "Steam authentication failed."}
        )


@app.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/")


# --- Game Data and Filtering Endpoints ---
@app.get("/api/games")
async def api_get_games(request: Request):
    user = request.session.get("user")
    if not user or not (steam_id := user.get("steam_id")):
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    cached_steam_data = steam_cache.get(steam_id)
    if (
        cached_steam_data
        and (time.time() - cached_steam_data["timestamp"]) < CACHE_EXPIRATION
    ):
        steam_data = cached_steam_data["data"]
    else:
        steam_data = get_owned_games(steam_id)
        if steam_data:
            steam_cache[steam_id] = {"timestamp": time.time(), "data": steam_data}

    if not steam_data:
        return JSONResponse(
            status_code=500, content={"detail": "Could not fetch games from Steam API"}
        )

    games = steam_data.get("games", [])
    manually_excluded_appids = database.get_excluded_games(steam_id)

    for game in games:
        game["is_excluded"] = game.get("appid") in manually_excluded_appids

    games.sort(key=lambda g: g.get("playtime_forever", 0), reverse=True)

    GAMES_LIMIT = 50
    games_to_return = games[:GAMES_LIMIT]

    return JSONResponse(content={"games": games_to_return})


@app.post("/api/games/exclude")
async def exclude_game_api(request: Request, payload: GameExclusionRequest):
    user = request.session.get("user")
    if not user or not (steam_id := user.get("steam_id")):
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
    database.add_exclusion(steam_id, payload.appid)
    return {"status": "success", "appid": payload.appid, "action": "excluded"}


@app.post("/api/games/include")
async def include_game_api(request: Request, payload: GameExclusionRequest):
    user = request.session.get("user")
    if not user or not (steam_id := user.get("steam_id")):
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
    database.remove_exclusion(steam_id, payload.appid)
    return {"status": "success", "appid": payload.appid, "action": "included"}


@app.post("/api/games/refresh")
async def refresh_games_api(request: Request):
    """
    Clears all caches for the user and refetches their game list from Steam.
    """
    user = request.session.get("user")
    if not user or not (steam_id := user.get("steam_id")):
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    # Clear all caches
    if steam_id in steam_cache:
        del steam_cache[steam_id]

    # For simplicity, we're clearing the entire hltb and app_details cache.
    # A more advanced implementation might only clear entries for this user's games.
    hltb_cache.clear()
    app_details_cache.clear()

    # Re-fetch the data to populate the cache
    steam_data = get_owned_games(steam_id)
    if steam_data:
        steam_cache[steam_id] = {"timestamp": time.time(), "data": steam_data}
        return {
            "status": "success",
            "message": "Game list refreshed and cache updated.",
        }
    else:
        return JSONResponse(
            status_code=500,
            content={"detail": "Could not fetch games from Steam API during refresh."},
        )


# --- AI Recommendation Endpoints ---
async def _get_and_process_games(
    steam_id: str, exclude_by_hltb: bool, playtime_threshold_hours: int | None
) -> List[Dict] | None:
    cached_steam_data = steam_cache.get(steam_id)
    if (
        cached_steam_data
        and (time.time() - cached_steam_data["timestamp"]) < CACHE_EXPIRATION
    ):
        steam_data = cached_steam_data["data"]
    else:
        steam_data = get_owned_games(steam_id)
        if steam_data:
            steam_cache[steam_id] = {"timestamp": time.time(), "data": steam_data}

    if not steam_data:
        return None

    games = steam_data.get("games", [])
    manually_excluded_appids = database.get_excluded_games(steam_id)

    # --- Filtering Logic ---
    filtered_games = [
        g for g in games if g.get("appid") not in manually_excluded_appids
    ]
    filtered_games = [g for g in filtered_games if g.get("playtime_forever", 0) > 0]
    if playtime_threshold_hours is not None and playtime_threshold_hours > 0:
        threshold_minutes = playtime_threshold_hours * 60
        filtered_games = [
            g
            for g in filtered_games
            if g.get("playtime_forever", 0) <= threshold_minutes
        ]

    filtered_games.sort(key=lambda g: g.get("playtime_forever", 0), reverse=True)

    GAMES_LIMIT = 10
    games_to_process = filtered_games[:GAMES_LIMIT]

    sanitized_games_for_llm = []
    for game in games_to_process:
        appid = game.get("appid")
        game_name = game.get("name")
        if not (appid and game_name):
            continue

        # --- HLTB Data ---
        cached_hltb = hltb_cache.get(game_name)
        hltb_stats = None
        if cached_hltb and (time.time() - cached_hltb["timestamp"]) < CACHE_EXPIRATION:
            hltb_stats = cached_hltb["data"]
        else:
            fetched_hltb = get_hltb_stats(game_name)
            if fetched_hltb:
                hltb_stats = fetched_hltb
                hltb_cache[game_name] = {"timestamp": time.time(), "data": hltb_stats}

        # --- Game Details (Genres/Categories) ---
        cached_details = app_details_cache.get(appid)
        game_details = None
        if (
            cached_details
            and (time.time() - cached_details["timestamp"]) < CACHE_EXPIRATION
        ):
            game_details = cached_details["data"]
        else:
            fetched_details = await get_game_details(appid)
            if fetched_details:
                game_details = fetched_details
                app_details_cache[appid] = {
                    "timestamp": time.time(),
                    "data": game_details,
                }

        # Filter by HLTB completion
        if exclude_by_hltb and hltb_stats and hltb_stats.get("main_story", 0) > 0:
            if (game.get("playtime_forever", 0) / 60) > hltb_stats["main_story"]:
                continue

        # Create sanitized object for LLM
        sanitized_games_for_llm.append(
            {
                "name": game_name,
                "playtime_hours": round(game.get("playtime_forever", 0) / 60, 1),
                "hltb": hltb_stats,
                "genres": [g["description"] for g in game_details.get("genres", [])]
                if game_details
                else [],
                "categories": [
                    c["description"] for c in game_details.get("categories", [])
                ]
                if game_details
                else [],
            }
        )
    return sanitized_games_for_llm


@app.post("/api/recommendations")
async def get_game_recommendations(
    request: Request,
    user_prompt: str = Form(...),
    custom_model: str = Form(None),
    custom_prompt: str = Form(None),
    playtime_threshold_hours: int = Form(None),
    exclude_by_hltb: bool = Form(False),
):
    user = request.session.get("user")
    if not user or not (steam_id := user.get("steam_id")):
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    games_for_llm = await _get_and_process_games(
        steam_id, exclude_by_hltb, playtime_threshold_hours
    )
    if games_for_llm is None:
        return JSONResponse(
            status_code=500, content={"detail": "Could not fetch games from Steam API"}
        )

    recs, metrics = await ai_recommender.get_recommendations(
        games_for_llm, user_prompt, custom_model, custom_prompt
    )
    return JSONResponse(content={"recommendations": recs, "metrics": metrics})


@app.post("/api/recommendations/surprise-me")
async def get_surprise_recommendation(
    request: Request,
    user_prompt: str = Form("Surprise me!"),
    custom_model: str = Form(None),
    custom_prompt: str = Form(None),
    playtime_threshold_hours: int = Form(None),
    exclude_by_hltb: bool = Form(False),
):
    user = request.session.get("user")
    if not user or not (steam_id := user.get("steam_id")):
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    games_for_llm = await _get_and_process_games(
        steam_id, exclude_by_hltb, playtime_threshold_hours
    )
    if games_for_llm is None:
        return JSONResponse(
            status_code=500, content={"detail": "Could not fetch games from Steam API"}
        )

    rec, metrics = await ai_recommender.surprise_me(
        games_for_llm, user_prompt, custom_model, custom_prompt
    )
    return JSONResponse(content={"recommendation": rec, "metrics": metrics})
