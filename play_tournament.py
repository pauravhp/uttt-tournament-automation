"""play_tournament.py is used to run the tournmanent, using multiprocessing to run all games in the same round simultaneously"""

import challonge
import play_two_bots
from queue import Queue
import concurrent.futures

# MongoDB connection
from pymongo.mongo_client import MongoClient
import certifi

from settings import auto_config as config

api_key = config.CHALLONGE_API_KEY

challonge.set_credentials(config.CHALLONGE_USERNAME, api_key)

tournament_id = config.TOURNAMENT_ID

tournament = challonge.tournaments.start(tournament=tournament_id)

# TODO: Add the tier (Can only run one tier of the tournament at a time). Make sure the spelling is the same
# as what is in the google form/sheets
tournament_tier = ""

participants = challonge.participants.index(tournament=tournament_id)


def getAllMatches():
    return challonge.matches.index(tournament=tournament_id)


def getOpenMatches(matches_dict):
    matches_li = []
    for x in matches_dict:
        if x["state"] == "open":
            p1 = challonge.participants.show(
                tournament=tournament_id, participant_id=x["player1_id"]
            )
            p2 = challonge.participants.show(
                tournament=tournament_id, participant_id=x["player2_id"]
            )
            matches_li.append(
                {
                    "id": x["id"],
                    "identifier": x["identifier"],
                    "round": x["round"],
                    "player1_name": p1["name"],
                    "player1_file": p1["misc"],
                    "player1_id": x["player1_id"],
                    "player1_seed": p1["seed"],
                    "player2_name": p2["name"],
                    "player2_file": p2["misc"],
                    "player2_id": x["player2_id"],
                    "player2_seed": p2["seed"],
                }
            )
    return matches_li


def create_MongoDb_document(
    match_id,
    match_identifier,
    round,
    player1_id,
    player2_id,
    winner_id,
    match_score,
    match_log,
):
    uri = config.MONGODB_URI

    # Create a new client and connect to the server
    client = MongoClient(uri, tlsCAFile=certifi.where())
    mydb = client["UTTTBracket"]
    matchesMongoDb = mydb["Matches"]

    dictToCreate = {
        "match_id": match_id,
        "identifier": match_identifier,
        "round": round,
        "player1_id": player1_id,
        "player2_id": player2_id,
        "winner_id": winner_id,
        "match_score": match_score,
        "match_log": match_log,
    }

    matchesMongoDb.insert_one(dictToCreate)


def playMatch(match, tournament_tier):
    match_result = play_two_bots.play(
        match["player1_file"].split(".")[0],
        match["player2_file"].split(".")[0],
        tournament_tier,
    )
    if match_result[1] == match["player1_file"].split(".")[0]:
        create_MongoDb_document(
            match_id=match["id"],
            match_identifier=match["identifier"],
            round=match["round"],
            player1_id=match["player1_id"],
            player2_id=match["player2_id"],
            winner_id=match["player1_id"],
            match_score=match_result[0],
            match_log=match_result[2],
        )
        return (match_result[0], match["player1_id"])
    create_MongoDb_document(
        match_id=match["id"],
        match_identifier=match["identifier"],
        round=match["round"],
        player1_id=match["player1_id"],
        player2_id=match["player2_id"],
        winner_id=match["player2_id"],
        match_score=match_result[0],
        match_log=match_result[2],
    )
    return (match_result[0], match["player2_id"])


def playAndUpdateMatch(cur_match, tournament_tier, match_no):
    match_result = playMatch(cur_match, tournament_tier)
    try:
        update_match = challonge.matches.update(
            tournament=tournament_id,
            match_id=cur_match["id"],
            scores_csv=match_result[0],
            winner_id=match_result[1],
        )
        print(f"Successfully updated match no. {match_no}")
        return update_match
    except:
        print(f"Failed to update match no. {match_no}")
        return None


# These need to be within this if loop to be able to run multi processing (concurrent.futures)
if __name__ == "__main__":
    matches_dict = getAllMatches()

    match_queue = Queue(
        maxsize=len(matches_dict)
    )  # max size should actually be number of particpants / 2

    i = 0

    while i < len(matches_dict):
        matches_dict = getAllMatches()
        open_matches = getOpenMatches(matches_dict)

        if open_matches == []:
            print("No more matches to be played!")
            break

        for x in open_matches:
            match_queue.put(x)

        while match_queue.empty() != True:
            with concurrent.futures.ProcessPoolExecutor() as executor:
                futures = [
                    executor.submit(
                        playAndUpdateMatch,
                        match_queue.get(),
                        tournament_tier,
                        i + _ + 1,
                    )
                    for _ in range(match_queue.qsize())
                ]

                # Collect results
                results = [
                    future.result()
                    for future in concurrent.futures.as_completed(futures)
                ]
            i = i + len(results)
