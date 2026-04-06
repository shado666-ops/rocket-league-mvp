import sys
import os

# Mocking a bit as we just want to test the math
def calculate_performance_rating(winrate: float, score: float, goals: float, saves: float, assists: float, shots: float, playlist: str | None = None) -> int:
    playlist = (playlist or "").lower()
    
    # Defaults (3v3 bases)
    base_score = 400.0
    base_goals = 2.0
    base_saves = 2.0
    base_shots = 3.0
    base_assists = 1.0
    
    if "2v2" in playlist or "doubles" in playlist:
        base_score = 600.0
        base_goals = 3.0
        base_saves = 3.0
        base_shots = 4.0
        base_assists = 1.0
    elif "3v3" in playlist or "standard" in playlist:
        base_score = 400.0
        base_goals = 2.0
        base_saves = 2.0
        base_shots = 3.0
        base_assists = 1.0

    norm_score = min((score / base_score) * 100, 100.0)
    norm_goals = min((goals / base_goals) * 100, 100.0)
    norm_saves = min((saves / base_saves) * 100, 100.0)
    norm_assists = min((assists / base_assists) * 100, 100.0)
    norm_shots = min((shots / base_shots) * 100, 100.0)
    
    # Weighted formula (15% Win, 25% Score, 20% Goals, 10% Shots, 10% Assists, 20% Saves)
    rating = (winrate * 0.15) + (norm_score * 0.25) + (norm_goals * 0.20) + (norm_saves * 0.20) + (norm_shots * 0.10) + (norm_assists * 0.10)
    return int(round(rating))

def test():
    print("--- Testing 2v2 Rating ---")
    # Perfect 2v2
    r2_perf = calculate_performance_rating(100, 600, 3, 3, 1, 4, "Ranked Doubles 2v2")
    print(f"2v2 Perfect (Expected 100): {r2_perf}")
    
    # Average 2v2
    r2_avg = calculate_performance_rating(100, 300, 1.5, 1.5, 0.5, 2, "Ranked Doubles 2v2")
    print(f"2v2 Average (Expected ~58): {r2_avg}")

    print("\n--- Testing 3v3 Rating ---")
    # Perfect 3v3
    r3_perf = calculate_performance_rating(100, 400, 2, 2, 1, 3, "Ranked Standard 3v3")
    print(f"3v3 Perfect (Expected 100): {r3_perf}")
    
    # Average 3v3
    r3_avg = calculate_performance_rating(100, 200, 1, 1, 0.5, 1.5, "Ranked Standard 3v3")
    print(f"3v3 Average (Expected ~58): {r3_avg}")

    print("\n--- Testing Default (should be 3v3) ---")
    r_def = calculate_performance_rating(100, 400, 2, 2, 1, 3, "Unknown Mode")
    print(f"Default Perfect (Expected 100): {r_def}")

if __name__ == "__main__":
    test()
