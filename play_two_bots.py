"""play_two_bots.py is used as a middle-man with the UTTTEngine, the code to score and play a match between 2 bots is written here"""

import importlib
from UTTT_Engine import UTTTEngine as UTTT
import inspect
import sys


def calculate_match_score(results_li):
    P1 = 0
    P2 = 0
    """ Scoring system - There are 10 games played, where every 2 games
    had the same initialized board, in which the agent that is P1 in game 1/2 is swapped to P2 in game 2/2.
    If an agent wins a game where they were P1, they get +1
    If an agent wins a game where they were P2, they get +1.5
    If the game results in a tie, both agents get +0.5 """
    for i in range(len(results_li)):
        if i % 2 == 0:
            # if 1 wins, P1 gets +1
            # if -1 wins, P2 gets +1.5
            if results_li[i] > 0:
                P1 = P1 + 1
            elif results_li[i] < 0:
                P2 = P2 + 1.5
            else:
                P1 = P1 + 0.5
                P2 = P2 + 0.5
        else:
            # if 1 wins, P1 gets +1.5
            # if -1 wins, P2 gets +1
            if results_li[i] > 0:
                P1 = P1 + 1.5
            elif results_li[i] < 0:
                P2 = P2 + 1
            else:
                P1 = P1 + 0.5
                P2 = P2 + 0.5
    return (P1 == P2, f"{int(P1*2)}-{int(P2*2)}", P1 > P2)


def getPlayerInstance(player_file: str, log: bool) -> tuple[bool, any]:
    # TODO: Might need to add the global/absolute path here using sys.path.insert()
    player_module = importlib.import_module(player_file)
    player_classname_li = [
        cls_name
        for cls_name, cls_obj in inspect.getmembers(sys.modules[player_file])
        if inspect.isclass(cls_obj) and cls_name != "board_obj" and cls_name != "ops"
    ]
    for player_classname in player_classname_li:
        player_class = getattr(player_module, player_classname)
        player = player_class()
        # Check if the class has a 'move' method
        if hasattr(player, "move") and inspect.ismethod(getattr(player, "move")):
            # Get information about the 'move' method
            move_method = getattr(player, "move")
            move_signature = inspect.signature(move_method)

            # Check if 'move' method has expected parameters
            expected_parameters = [
                "board_dict",
            ]
            actual_parameters = list(move_signature.parameters.keys())

            if actual_parameters == expected_parameters:
                # Check if 'move' method has expected return type
                expected_return_annotation = tuple
                actual_return_annotation = move_signature.return_annotation
                if actual_return_annotation == expected_return_annotation:
                    if log:
                        print(
                            "Class has a 'move' method with the expected parameters and return type."
                        )
                    return (True, player)
                else:
                    if log:
                        print(
                            f"Class has a 'move' method with unexpected return type '{actual_return_annotation}'."
                        )
                    return (False, None)
            else:
                if log:
                    print(
                        f"Class has a 'move' method with unexpected parameters {actual_parameters}."
                    )
                return (False, None)
        else:
            if log:
                print("Class does not have a 'move' method.")
            return (False, None)


def crashTest(player_file):
    player2 = ""  # Add the file name of a bot you want all bots to play a test game with, without the .py in the end

    player1 = getPlayerInstance(player_file, True)
    player2 = getPlayerInstance(player2, True)

    try:
        match_res = UTTT.play_game(agent1=player1, agent2=player2, n_init_moves=4)
        print("Your bot passed the crash test!")
        print(match_res)
    except Exception as e:
        print(f"Your bot failed to play a game because: {e}")


def play(player1_file: str, player2_file: str, tier: str):
    # TODO: Might need to add the global/absolute path here using sys.path.insert()
    player1 = getPlayerInstance(player1_file, False)
    player2 = getPlayerInstance(player2_file, False)
    games_li = UTTT.run_threaded_games(
        agent1=player1, agent2=player2, n_games=5, n_init_moves=4
    )
    match_result = calculate_match_score(games_li[0])
    if match_result[0] == False:
        if match_result[2]:
            return (match_result[1], player1_file, games_li[1])
        else:
            return (match_result[1], player2_file, games_li[1])
    else:
        print("Starting match again")
        return play(player1_file=player1_file, player2_file=player2_file, tier=tier)


# Used to test and run crash tests on files one by one
if __name__ == "__main__":
    crashTest("")
