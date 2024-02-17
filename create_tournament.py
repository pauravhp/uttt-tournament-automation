"""create_tournament.py is used to create a tournament and generate the tournament id."""

import challonge
from settings import auto_config as config

api_key = config.CHALLONGE_API_KEY
challonge.set_credentials(config.CHALLONGE_USERNAME, api_key)

tournament = challonge.tournaments.create(
    name="<tournament_name>",
    url="<desired_tournament_url>",
    tournament_type="double elimination",  # see Challonge's documentation for the available types
    description="<description_for_tournament>",
    accept_attachments=True,
    show_rounds=True,
)
print(tournament)
print(
    f"Save this id and add it to config.py in the settings folder: {tournament['id']}"
)
