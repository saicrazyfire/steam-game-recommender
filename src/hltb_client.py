from howlongtobeatpy import HowLongToBeat

def get_hltb_stats(game_name: str):
    """
    Fetches HowLongToBeat stats for a given game name.
    """
    try:
        results = HowLongToBeat().search(game_name)
        if results:
            # Assume the first result is the most relevant
            best_match = results[0]
            return {
                "name": best_match.game_name,
                "main_story": best_match.main_story,
                "main_extra": best_match.main_extra,
                "completionist": best_match.completionist,
                "url": best_match.game_web_link,
            }
        else:
            return None
    except Exception as e:
        print(f"An error occurred while fetching HLTB stats for '{game_name}': {e}")
        return None
