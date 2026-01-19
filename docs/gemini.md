### Project Plan: Steam Game Recommender

This document outlines the plan for creating a Python application to get game details and playtime from Steam, integrate with HowLongToBeat, and provide AI-powered game recommendations.

**Project Structure**

```
/
|-- .gitignore
|-- config.toml         # Main configuration file
|-- README.md
|-- .venv/              # Virtual environment
|-- docs/
|   |-- gemini.md       # This plan
|-- output/             # For exported data (e.g., CSV, JSON)
|-- logs/               # For application logs
|-- scripts/            # Helper scripts (e.g., start_server.bat)
|-- pyproject.toml      # Project configuration and dependencies
|-- src/                # Main application source code
|   |-- __init__.py
```

**User Interface (UI)**

*   A simple, modern web interface will be created using **FastAPI's Jinja2Templates** for server-side rendering of HTML.
*   **Tailwind CSS** will be used for styling to create a clean and modern look.
*   The UI will be served from the `src/templates` and `src/static` directories.
*   The UI will provide:
    *   A "Sign in with Steam" button.
    *   A page to display the user's game library and stats.
    *   Buttons to trigger the AI recommendation features.

**Phase 1: Data Collection and Integration**

1.  **Project Setup:**
    *   Initialize a Python project using `uv` for package management.
    *   Create the directory structure as defined above.
    *   Set up a FastAPI web server in `src/main.py`.
    *   Install initial dependencies: `fastapi`, `uvicorn`, `python-dotenv`, `howlongtobeatpy`, `jinja2`, a Python Steam API library, and `tomli`.

2.  **Configuration:**
    *   All settings will be managed through `config.toml`. A `.env` file will be used for sensitive data like API keys, which `config.toml` can read from.

3.  **Steam Authentication:**
    *   Implement Steam's OpenID for user authentication.
    *   Create a `/login` endpoint to redirect the user to the Steam login page.
    *   Create a `/auth/steam/callback` endpoint to handle the return from Steam, verify the user's identity, and store their Steam ID in a session.

4.  **Steam API Data Fetching:**
    *   Create a `src/steam_client.py` module to encapsulate all interactions with the Steam Web API.
    *   Implement functions to fetch:
        *   The user's owned games, including playtime and last played timestamp (`IPlayerService/GetOwnedGames`).
        *   Details for each game, such as name, genres, and categories (using the `appdetails` endpoint).

5.  **HowLongToBeat Integration:**
    *   Create a `src/hltb_client.py` module.
    *   Use the `howlongtobeatpy` library to search for games by name and retrieve completion time statistics.

6.  **Data Consolidation and API:**
    *   Create a `/api/games` endpoint in `src/main.py`.
    *   This endpoint will ensure the user is authenticated, fetch data from both APIs, and return a consolidated JSON response.
    *   Define Pydantic models for the data structures.

7.  **Data Export:**
    *   Create a `/api/export` endpoint that generates a CSV or JSON file of the user's consolidated game data and saves it to the `output/` directory.

**Phase 2: AI-Powered Recommendations**

1.  **AI Service Abstraction:**
    *   Create a `src/recommender.py` module with a base `AIRecommender` class.
    *   Implement concrete subclasses for different AI providers as configured in `config.toml`.
    *   API keys will be loaded from the `.env` file.

2.  **Prompt Engineering:**
    *   Develop a system prompt that instructs the LLM to act as a game recommendation expert.
    *   The prompt will guide the LLM to analyze the provided game data and suggest games from the user's library.
    *   It will ask the LLM to return a ranked list in a specific JSON format.

3.  **Data Handling for LLM:**
    *   The consolidated game data from Phase 1 will be the primary input.
    *   To manage large game libraries, a data summarization/filtering strategy will be implemented (e.g., filter by most recent or most played games).

4.  **Recommendation API Endpoints:**
    *   **/api/recommendations**: Takes game data, sends it to the AI service, and returns a ranked list of recommendations.
    *   **/api/recommendations/surprise-me**: Calls the above endpoint and returns only the top recommended game.