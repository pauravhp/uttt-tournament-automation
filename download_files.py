"""download_files.py is used to collect all files submitted via the Google Form from Google Drive, and then add them accordingly into the Challonge bracket and 
    MongoDB"""

import os
import io
import math

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

from settings import auto_config as config

# Load credentials from JSON file
credentials_file = config.GOOGLE_CREDENTIALS_FILE
credentials = service_account.Credentials.from_service_account_file(
    credentials_file, scopes=["https://www.googleapis.com/auth/drive"]
)

# TODO: Specify the folder ID in Google Drive
folder_id = ""

# Google Drive API
drive_service = build("drive", "v3", credentials=credentials)


def download_file(file_id, file_name):
    try:
        request_file = drive_service.files().get_media(fileId=file_id)
        file = io.FileIO(file_name, "wb")
        downloader = MediaIoBaseDownload(file, request_file)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print(f"Download {int(status.progress() * 100)}.")
    except HttpError as error:
        print(f"An error occurred: {error}")


def create_MongoDb_document(player_name, player_file_name, player_id, player_emoji):
    mydb = client["UTTTBracket"]
    participantsMongoDb = mydb["Participants"]
    dictToCreate = {
        "player_id": player_id,
        "name": player_file_name,
        "file_name": player_name,
        "player_emoji": player_emoji,
    }
    participantsMongoDb.insert_one(dictToCreate)


# Google Sheet
# TODO: Add url to Google Form Response Sheet
form_response_sheet_url = ""
response_sheet_id = form_response_sheet_url.split("/")[-2]
sheets_service = build("sheets", "v4", credentials=credentials)
sheets = sheets_service.spreadsheets()

# Get all responses from the Google Form Response Sheet
# TODO: Add the columns you want to get from the sheet (for example: A:F)
response_range = ""
response_values = (
    sheets.values()
    .get(spreadsheetId=response_sheet_id, range=response_range)
    .execute()
    .get("values", [])
)

# Challonge API
import challonge

api_key = config.CHALLONGE_API_KEY
challonge.set_credentials(config.CHALLONGE_USERNAME, api_key)

tournament_id = config.TOURNAMENT_ID

# MongoDB connection
from pymongo.mongo_client import MongoClient
import certifi

uri = config.MONGODB_URI
# Create a new client and connect to the server
client = MongoClient(uri, tlsCAFile=certifi.where())

mydb = client["UTTTBracket"]
participantsMongoDb = mydb["Participants"]

""" Download files based on the file IDs in the responses and add them to the MongoDB collection
x[2] means the third column in the Google Sheet. This is what the code below assumes - 
x[2] is the participant's name
x[-2] is the file_id
x[-3] is the tier_name"""
for x in response_values[1:]:
    file_metadata = (
        drive_service.files()
        .get(fileId=x[-2].split("=")[-1], fields="id,name,mimeType,fileExtension")
        .execute()
    )
    file_path = os.path.join(
        f"aboslute_path_to_folder_storing_downloaded_files/{x[-3]}",
        file_metadata["name"].replace(" ", "_").replace("-", "_"),
    )
    download_file(file_metadata["id"], file_path)
    # TODO: Add tier name
    if x[-3] == "":
        try:
            print("Creating participant")
            participant = challonge.participants.create(
                tournament=tournament_id,
                name=x[2],
                misc=file_metadata["name"].replace(" ", "_").replace("-", "_"),
            )
            print(
                f"Successfully Created Participant: {participant['name']} - {participant['id']}"
            )
        except:
            print(f"Participation adding failed!")
            break
        try:
            print("Adding participant to MongoDb")
            # Need to add bot name as well into documents
            create_MongoDb_document(
                player_id=participant["id"],
                player_name=participant["name"],
                player_file_name=participant["misc"],
                player_emoji=x[-1],
            )
        except:
            print(
                f"Failed to create document for participant: {participant['name']} - {participant['id']}"
            )
            break

print("Files downloaded successfully!")

# To help with visualization, randomly assign each bot a background color
pcs = challonge.participants.index(tournament=tournament_id)
num_of_pcs = len(pcs)
bg_split = math.floor(256 / num_of_pcs)
for index, val in enumerate(pcs):
    participantsMongoDb.update_one(
        {"player_id": val["id"]}, {"$set": {"player_bg_color": index * bg_split}}
    )

print("These are all the participants stored in MongoDB -")
print(participantsMongoDb.find())

# Randomize player seeding
challonge.participants.randomize(tournament=tournament_id)
