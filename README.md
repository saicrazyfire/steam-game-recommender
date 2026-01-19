# Steam Game Recommender

This project helps you analyze your Steam library, see your gaming habits, and get AI-powered recommendations for what to play next.

## Features

*   **Steam Library Analysis:** Connect your Steam account to see detailed stats about your games, including playtime, last played dates, and more.
*   **HowLongToBeat Integration:** Compare your playtime with average completion times from HowLongToBeat.
*   **AI-Powered Recommendations:** Get personalized game recommendations from your library based on your gaming style.
*   **Data Export:** Export your game data to CSV or JSON for your own analysis.

## Getting Started

1.  **Installation:**
    ```bash
    # Clone the repository
    git clone <repository-url>
    cd steam-game-recommender

    # Sync dependencies from pyproject.toml
    uv sync
    ```

2.  **Configuration:**
    *   Rename `.env.example` to `.env` and fill in your Steam API key and a secret key for the web server.
    *   Review `config.toml` to configure the AI provider and other settings.

3.  **Running the Application:**
    ```bash
    # On Windows
    .\scripts\start_server.bat
    ```
    Then open your browser to `http://127.0.0.1:8000`.

*(More detailed setup instructions will be added as the project progresses)*