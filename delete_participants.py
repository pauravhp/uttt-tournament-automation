"""delete_participants.py is used to wipe any progress saved to Challonge and MongoDB"""

# Erase data on Challonge

import challonge
from settings import auto_config as config

api_key = config.CHALLONGE_API_KEY

tournament_id = config.TOURNAMENT_ID

participants_li = challonge.participants.index(tournament=tournament_id)

# Resetting to ensure participants can be deleted
try:
    reset = challonge.tournaments.reset(tournament=tournament_id)
except challonge.ChallongeException as err:
    print(err)

for p in participants_li:
    try:
        res = challonge.participants.destroy(
            tournament=tournament_id, participant_id=p["id"]
        )
    except:
        print(f"Failed to delete participant {p['id']} - {p['name']}")

# Erase data on MongoDB
# MongoDB connection
from pymongo.mongo_client import MongoClient
import certifi

uri = config.MONGODB_URI

# Create a new client and connect to the server
client = MongoClient(uri, tlsCAFile=certifi.where())

mydb = client["UTTTBracket"]
participantsMongoDb = mydb["Participants"]
participantsMongoDb.delete_many({})
matchesMongoDb = mydb["Matches"]
matchesMongoDb.delete_many({})
