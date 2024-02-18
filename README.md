# 👾👾 UTTT Tournament Automation Suite 👾👾

This project was created in order to facilitate [UVicAI](uvicai.ca)'s Spring 2024 Ultimate Tic Tac Toe hackathon. This suite of automation scripts takes care of a multitude of aspects when it comes to running the tournament, from registering participants to playing all matches between bots in a quick and efficient manner.
The game engine was written by [Finn Archinuk](https://github.com/finnarchinuk/UTTT) and the tournament games were visualized using [Nathan Pannell's Vis Tool](https://github.com/NathanPannell/uttt-visual)

## Introduction

All scripts were written in Python 3. The main technologies used were [Challonge API](https://challonge.com/), Google Form/Sheet/Drive and MongoDB Atlas.

## Installation & Configuration

Necessary libraries to install -

- [py-challonge] (https://github.com/ZEDGR/pychallonge)
- google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
- pymongo
- certifi

## Usage

How to run the tournament using this automation suite. **Make sure config.py is set up before starting** -

1. Run create_tournament.py with the appropriate details (save the printed tournament_id in config.py)
2. Run download_files.py (Make sure you have ensure all files are safe to run and have run the crash test on each one)
   - If there were any issues so far, you can run delete_participants.py to remove any progress made and start over
3. Run play_tournament.py (Make sure to put the right tier being played).

## Troubleshooting

- The crash test in play_two_bots.py can be difficult to debug a participant's bot file. Make sure you give enough time for this step.
- The Challonge API can some times not execute the final games of the bracket due to some connection issues, so make sure the connection is working by running a test on pulling some tournament details.

## Future Work/Features

This repository will see a more generalized version created soon, fit to run with any "game_engine", so stay tuned to my github for that!

Some future features that would be nice for this automation suite -

- Automated bot crash testing
- Bot file sanitization (checking if python files are safe to run)
- Automatically deleting any files downloaded in delete_participants.py
- Run all scripts together in one file
