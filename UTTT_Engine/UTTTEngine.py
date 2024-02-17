"""All credit for this file goes to 
Finn Archinuk - https://github.com/finnarchinuk/UTTT
The only added methods are ones that cater to running matches using multiprocessing and following tournament standards"""

import numpy as np
import matplotlib.pyplot as plt

""" visualization imports """
from matplotlib.colors import LinearSegmentedColormap

cmap = LinearSegmentedColormap.from_list("mycmap", ["lightgrey", "white"])
import matplotlib.colors as mcolors

""" Time restriction imports"""
import signal
import time
import random

import concurrent.futures
import logging

"""board_obj imports"""
from board import board_obj
from operations import ops

logger = logging.getLogger("ftpuploader")

tab10_names = list(mcolors.TABLEAU_COLORS)  # create a list of colours


def checkerboard(shape):
    # from https://stackoverflow.com/questions/2169478/how-to-make-a-checkerboard-in-numpy
    return np.indices(shape).sum(axis=0) % 2


class bot_template:
    """
    demonstrates the two minimal functions for an agent
    """

    def __init__(self, name: str = "bot_template"):
        self.name = name

    def move(self, board_dict: dict) -> tuple:
        """
        the keywords for board_dict are:
        board_state: a 9x9 np.array showing which squares have which markers.
                     your markers at +1 and your opponent markers are -1.
                     open squares are 0
        active_box:  the coordinate for the active mini-board (indicates which 3x3 is currently playable)
                     a value of (-1, -1) is used if the whole board is valid
        valid_moves: a list of tuples indicating which positions are valid (in the 9x9 format)
        """
        pass


class uttt_engine:
    def __init__(self):
        self.active_box = (-1, -1)  # (-1,-1) means any box can be played in
        self.board_state = np.zeros((9, 9))
        self.finished_boxes = np.zeros(
            (3, 3)
        )  # 1 for agent1, -1 for agent2. "6" indicates stalemate
        self.finished = False
        self.finished_win = False
        self.finished_stale = False
        self.current_player = 1  # starting player
        self.game_log = ""
        self.board_object = board_obj()

    """ -------------- Initialization ------"""

    def load_agents(self, agent1: bot_template, agent2: bot_template) -> None:
        """agent1 and agent2 are uttt agents"""
        self.agents = [agent1, agent2]

    """ --------------- Logging ----------- """

    def get_game_log(self) -> str:
        """returns the current game encoding (for visualization)"""
        return self.game_log

    def log_move(self, position: tuple) -> None:
        # convert tuple to string, append character to existing game code
        offset = 32
        self.game_log += chr(position[0] * 9 + position[1] + offset)

    def load_game(self, game_string: str) -> None:
        """assumes the game string is valid (this is not strictly enforced)"""
        for encoded_position in game_string:
            # update game board
            self.move(self.unconvert(encoded_position), log=False)

    def unconvert(self, symbol):
        """part of loading a game from a string"""
        offset = 32
        int_position = ord(symbol) - offset
        return (int_position // 9, int_position % 9)

    """ ------------- Logic --------------- """

    def get_query_dict(self) -> dict:
        """can be used in development to understand what the bot is being provided for logic"""
        return ops.pull_dictionary(self.board_object)

    def move_handler(self, signum, frame):
        raise TimeoutError("Move timed out")

    def move_with_timeout(self, agent, query_dict, temp_valid_moves, timeout):
        # Set the move_handler as the signal handler for SIGALRM (alarm signal)
        signal.signal(signal.SIGALRM, self.move_handler)
        # Set the timeout for the alarm signal
        signal.setitimer(signal.ITIMER_REAL, timeout)

        try:
            # Call the move function
            result = tuple(agent.move(query_dict))
        except TimeoutError as e:
            # If the move function times out, set desired_move to temp_valid_moves[0]
            result = temp_valid_moves[random.randint(0, len(temp_valid_moves))]
        finally:
            # Cancel the alarm
            signal.setitimer(signal.ITIMER_REAL, 0)

        return result

    def query_player(self, loud: bool = False) -> None:
        """
        send a request to a player instance for a move
        updates the game board with the desired move
        if no valid move is returned, a random move is played for that agent
        the "loud" argument can be used to hear/silence warnings
        """
        # check agents are loaded
        if not hasattr(self, "agents"):
            print("must load agents")
            return

        # check game is not finished
        if self.finished:
            print("no valid moves in terminal state")
            return

        # send the request with board information in the form of a dictionary
        temp_valid_moves = self.get_valid_moves()
        temp_valid_moves = [tuple(x) for x in temp_valid_moves]

        try:
            # desired_move = tuple(self.agents[0].move(self.get_query_dict()))
            desired_move = self.move_with_timeout(
                self.agents[0],
                self.get_query_dict(),
                temp_valid_moves=temp_valid_moves,
                timeout=0.5,
            )
            if desired_move not in temp_valid_moves:
                random_index = np.random.choice(np.arange(len(temp_valid_moves)))
                desired_move = tuple(temp_valid_moves[random_index])
                if loud:
                    print(
                        f"warning: {self.agents[0].name} played an invalid move. converting to random valid alternative"
                    )
            # update board
            self.move(position=desired_move)
            ops.make_move(self.board_object, desired_move)

        except Exception as e:
            # shouldn't get here, but this chunk of code exists for safety
            if loud:
                logger.exception(e)
            random_index = np.random.choice(np.arange(len(temp_valid_moves)))
            desired_move = tuple(temp_valid_moves[random_index])

            # update board
            self.move(position=desired_move)
            ops.make_move(self.board_object, desired_move)

    def switch_active_player(self) -> None:
        """switch the current player value and the agent list"""
        # this is called at the end of .move()
        self.agents = self.agents[::-1]
        self.current_player *= -1

    def getwinner(self) -> int:
        """new method
        returns the integer indicating the winning player
        (subject to change)
        """
        if self.finished:
            if self.finished_win:
                return self.current_player
            else:
                return 0

    def check_validity(self, position: tuple) -> bool:
        """check whether position - a tuple - is valid"""
        box_validity = (self.active_box == self.map_to_major(position)) or (
            self.active_box == (-1, -1)
        )
        open_validity = self.board_state[position] == 0
        return box_validity and open_validity

    def check_line(self, box: np.array) -> bool:
        """
        box is a (3,3) array (typically a mini-board)
        returns True if a line is found
        """
        for i in range(3):
            if abs(sum(box[:, i])) == 3:
                return True  # horizontal
            if abs(sum(box[i, :])) == 3:
                return True  # vertical

        # diagonals
        if abs(box.trace()) == 3:
            return True
        if abs(np.rot90(box).trace()) == 3:
            return True

    def map_to_major(self, position: tuple) -> tuple:
        """
        converts position to major coordinates
        eg: (5,3) -> (1,1)
        """
        return (position[0] // 3, position[1] // 3)

    def map_to_minor(self, position: tuple) -> tuple:
        """
        converts position into mini coordinates
        eg: (5,3) -> (2,0)
        """
        return (position[0] % 3, position[1] % 3)

    def check_full_stale(self) -> None:
        """this might be impossible?"""
        # get number of invalid boxes

        if (self.finished_boxes == 0).sum() == 0:
            self.finished_stale = True
            self.finished = True

    def move(self, position: tuple, log: bool = True) -> None:
        """
        the main game logic. board updates and logic checks.
        """
        if self.finished:
            print("no move played, game is finished")
            return

        if self.check_validity(position):
            # log move
            if log:
                self.log_move(position)

            # place marker
            self.board_state[position] = self.current_player

            # select both scales
            temp_box = self.map_to_major(position)
            temp_minor_box = self.board_state[
                3 * temp_box[0] : 3 * temp_box[0] + 3,
                3 * temp_box[1] : 3 * temp_box[1] + 3,
            ]

            """ check line at minor scale """
            if self.check_line(temp_minor_box):
                self.finished_boxes[self.map_to_major(position)] = self.current_player

                # check line at major scale
                if self.check_line(self.finished_boxes):
                    self.finished_win = True
                    self.finished = True
                    return  # end the whole thing immediately (will cause stalemate bug without this !)

            # if no squares are open, mark as stale
            elif (temp_minor_box == 0).sum() == 0:
                self.finished_boxes[self.map_to_major(position)] = (
                    6  # indicates stalemate in that box
                )

            """ is the whole game board stale? """
            # if it's stale, set the appropriate flags
            self.check_full_stale()

            """ calculate active box """
            self.active_box = self.map_to_minor(position)
            # if that box is won or stale flag it
            if self.finished_boxes[self.active_box] != 0:
                self.active_box = (-1, -1)

            # switch player
            self.switch_active_player()

    def get_valid_moves(self) -> np.array:
        """
        returns an array (N,2) of valid moves
        """

        if self.finished:
            print("no valid moves in terminal state")
            return np.empty(0)
        # define masks that cover the board
        # across the whole board
        full_board_mask = self.board_state == 0
        # active square
        active_box_mask = np.zeros((9, 9), dtype=bool)
        # identifies finished major boxes
        a = np.repeat(self.finished_boxes, 3).reshape(3, 9)
        b = np.tile(a, 3).reshape(9, 9)
        finished_box_mask = b == 0

        if self.active_box == (-1, -1):
            active_box_mask[:] = True
            active_box_mask *= finished_box_mask
        else:
            active_box_mask[
                3 * self.active_box[0] : 3 * self.active_box[0] + 3,
                3 * self.active_box[1] : 3 * self.active_box[1] + 3,
            ] = True

        # return get union of maps
        return np.array(np.where(active_box_mask * full_board_mask)).T

    """ ------------- Visualization ------- """

    def draw_valid_moves(self) -> None:
        """visualization tool
        plots the valid moves as purple squares
        to be called after the .draw_board() method
        """
        moves = self.get_valid_moves()
        plt.scatter(moves[:, 0], moves[:, 1], marker="s", c="purple", alpha=0.3, s=50)

    def draw_board(self, marker_size: int = 100, ticks: str = "off") -> None:
        """visualization tool
        plots a checkerboard and markers for all plays.
        lines distinguish mini-boards and finished boards are coloured in
        """
        plt.imshow(checkerboard((9, 9)), cmap=cmap, origin="lower")
        for i in [-0.5, 2.5, 5.5, 8.5]:
            plt.axvline(i, c="k")
            plt.axhline(i, c="k")

        if ticks == "off":
            plt.axis("off")
        else:
            plt.xticks(np.arange(9))

        plt.scatter(
            *np.where(self.board_state == -1), marker="x", s=marker_size, c="tab:blue"
        )
        plt.scatter(
            *np.where(self.board_state == 1), marker="o", s=marker_size, c="tab:orange"
        )

        x_boxes = np.where(self.finished_boxes == -1)
        o_boxes = np.where(self.finished_boxes == 1)
        plt.scatter(
            x_boxes[0] * 3 + 1,
            x_boxes[1] * 3 + 1,
            marker="s",
            s=marker_size * 50,
            alpha=0.6,
            c="tab:blue",
        )
        plt.scatter(
            o_boxes[0] * 3 + 1,
            o_boxes[1] * 3 + 1,
            marker="s",
            s=marker_size * 50,
            alpha=0.6,
            c="tab:orange",
        )

        stale_boxes = np.where(self.finished_boxes == 6)
        plt.scatter(
            stale_boxes[0] * 3 + 1,
            stale_boxes[1] * 3 + 1,
            marker="s",
            s=marker_size * 50,
            alpha=0.3,
            c="k",
        )


def initialize(engine_instance, n_moves: int) -> None:
    """plays some number of random moves to initialize a game"""
    if n_moves % 2 != 0:
        print("warning: number of moves should be even!")

    for i in range(n_moves):
        valid_moves = engine_instance.get_valid_moves()
        random_index = np.random.choice(len(valid_moves))
        engine_instance.move(tuple(valid_moves[random_index]))


def get_initialized_board(engine_instance, n_moves: int):
    valid_moves = engine_instance.get_valid_moves()
    initialized_board = []
    for i in range(n_moves):
        random_index = np.random.choice(len(valid_moves))
        engine_instance.move(tuple(valid_moves[random_index]))
        initialized_board.append(tuple(valid_moves[random_index]))

    return initialized_board


def play_initialized_board(engine_instance, n_moves: int, initialized_board):
    for i in range(n_moves):
        engine_instance.move(initialized_board[i])


def play_with_initialized_board(
    board_state: list[any],
    n_init_moves: int,
    agent1: bot_template,
    agent2: bot_template,
    isFlipped: int,
):
    print("Starting game")
    finished_flag = False
    engine_instance = uttt_engine()
    if isFlipped % 2 == 0:
        engine_instance.load_agents(agent1, agent2)
    else:
        engine_instance.load_agents(agent1=agent2, agent2=agent1)
    play_initialized_board(
        engine_instance, n_moves=n_init_moves, initialized_board=board_state
    )
    while not finished_flag:
        engine_instance.query_player()
        if engine_instance.finished:
            finished_flag = True
    winner = engine_instance.getwinner()
    if isFlipped % 2 != 0:
        winner = engine_instance.getwinner() * (-1)
    print("Finishing game")
    return (winner, engine_instance.get_game_log())


def play_threaded_game(agent1: bot_template, agent2: bot_template, n_init_moves: int):
    match_log = []
    wins = []
    engine1 = uttt_engine()
    engine1.load_agents(agent1, agent2)
    board = get_initialized_board(engine1, n_moves=n_init_moves)

    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = [
            executor.submit(
                play_with_initialized_board, board, n_init_moves, agent1, agent2, _
            )
            for _ in range(2)
        ]
        # Collect results
        results = [
            future.result() for future in concurrent.futures.as_completed(futures)
        ]

    for res in results:
        wins.append(res[0])
        match_log.append(res[1])

    return (wins, match_log)


def play_game(agent1: bot_template, agent2: bot_template, n_init_moves: int):
    match_log = []
    wins = []
    for i in range(2):
        finished_flag = False
        engine = uttt_engine()
        if i % 2 == 0:
            engine.load_agents(agent1, agent2)
            board = get_initialized_board(engine, n_moves=n_init_moves)
        else:
            engine.load_agents(agent1=agent2, agent2=agent1)
            play_initialized_board(
                engine, n_moves=n_init_moves, initialized_board=board
            )
        while not finished_flag:
            engine.query_player(loud=True)
            if engine.finished:
                finished_flag = True
        match_log.append(engine.get_game_log())
        if i % 2 != 0:
            wins.append(engine.getwinner() * (-1))
        else:
            wins.append(engine.getwinner())
    print("Finishing game")
    return (wins, match_log)


def run_threaded_games(
    agent1: bot_template,
    agent2: bot_template,
    n_games: int = 5,
    n_init_moves: int = 4,
):
    match_log = []
    wins = list()
    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = [
            executor.submit(play_threaded_game, agent1, agent2, n_init_moves)
            for _ in range(n_games)
        ]

        # Collect results
        results = [
            future.result() for future in concurrent.futures.as_completed(futures)
        ]

    for res in results:
        wins.extend(res[0])
        match_log.extend(res[1])

    return (np.array(wins), match_log)


def run_many_games(
    agent1: bot_template,
    agent2: bot_template,
    n_games: int = 1000,
    n_init_moves: int = 4,
):
    """repeatedly plays games between two bots to evaluate their fraction of wins"""
    match_log = []
    wins = list()
    board = []
    for i in range(n_games * 2):
        finished_flag = False
        engine = uttt_engine()
        if i % 2 == 0:
            engine.load_agents(agent1, agent2)
            board = get_initialized_board(engine, n_moves=n_init_moves)
        else:
            engine.load_agents(agent1=agent2, agent2=agent1)
            play_initialized_board(
                engine, n_moves=n_init_moves, initialized_board=board
            )
        while not finished_flag:
            engine.query_player()
            if engine.finished:
                finished_flag = True
        match_log.append(engine.get_game_log())
        if i % 2 != 0:
            wins.append(engine.getwinner() * (-1))
        else:
            wins.append(engine.getwinner())
    return (np.array(wins), match_log)
