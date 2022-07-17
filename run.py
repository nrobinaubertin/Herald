#!/usr/bin/env python3

import sys
import time
import multiprocessing
from engine.constants import COLOR
from engine.board import Board
from engine.search import search
from engine.transposition_table import TranspositionTable
from engine.evaluation import eval_board
from engine.data_structures import to_uci
from engine.best_move import best_move

NAME = "Herald"
VERSION = "{} 0.11.1".format(NAME)
AUTHOR = "nrobinaubertin"
CURRENT_BOARD = Board("startpos")
CURRENT_PROCESS = None
TRANSPOSITION_TABLE = None


def stop_calculating():
    global CURRENT_PROCESS
    if CURRENT_PROCESS is not None:
        CURRENT_PROCESS.terminate()


def uci_parser(line):
    global CURRENT_BOARD
    tokens = line.strip().split()

    if not tokens:
        return []

    if tokens[0] == "eval":
        return [f"board: {eval_board(CURRENT_BOARD)}"]

    if tokens[0] == "print":
        return [str(CURRENT_BOARD)]

    if len(tokens) > 1 and tokens[0] == "tt" and tokens[1] == "stats":
        stats = TRANSPOSITION_TABLE.stats()
        stats_str = (
            f"SHALLOW_HITS: {stats['SHALLOW_HITS']}, "
            f"HITS: {stats['HITS']}, "
            f"REQ: {stats['REQ']}, "
            f"LEN: {stats['LEN']}, "
            f"ADD: {stats['ADD']}, "
            f"ADD_BETTER: {stats['ADD_BETTER']}"
        )
        return [stats_str]

    if len(tokens) > 1 and tokens[0] == "tt" and tokens[1] == "export":
        output = TRANSPOSITION_TABLE.export()
        return [output]

    if len(tokens) == 1 and tokens[0] == "uci":
        return [
            f"{VERSION} by {AUTHOR}",
            f"id name {NAME}",
            f"id author {AUTHOR}",
            # fake some options
            "option name Hash type spin default 16 min 1 max 33554432",
            "option name Move Overhead type spin default 10 min 0 max 5000",
            "option name Threads type spin default 1 min 1 max 1",
            "uciok",
        ]

    if tokens[0] == "stop":
        stop_calculating()

    if tokens[0] == "quit":
        stop_calculating()
        sys.exit()

    if tokens[0] == "ucinewgame":
        CURRENT_BOARD = Board(
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        )
        return []

    if tokens[0] == "isready":
        return [
            "readyok",
        ]

    if len(tokens) > 1 and tokens[0] == "position":
        if tokens[1] == "startpos":
            fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            next_token = 2
        else:
            fen = f"{tokens[1]} "
            + f"{tokens[2]} {tokens[3]} {tokens[4]} "
            + f"{tokens[5] if len(tokens) > 5 else 0} "
            + f"{tokens[6] if len(tokens) > 6 else 0}"
            next_token = 7
        board = Board(fen)
        if len(tokens) > next_token and tokens[next_token] == "moves":
            for move in tokens[next_token + 1:]:
                board.push(board.from_uci(move))
        CURRENT_BOARD = board

    if len(tokens) > 1 and tokens[0] == "go":

        depth = None

        if len(tokens) > 8:
            if tokens[1] == "wtime":
                wtime = int(tokens[2])
            if tokens[3] == "btime":
                btime = int(tokens[4])
            if tokens[5] == "winc":
                winc = int(tokens[6])
            if tokens[7] == "binc":
                binc = int(tokens[8])

        if tokens[1] == "movetime":
            wtime = int(tokens[2])
            btime = int(tokens[2])
            winc = 0
            binc = 0

        if tokens[1] == "depth":
            depth = int(tokens[2])

        current_eval = eval_board(CURRENT_BOARD)

        global CURRENT_PROCESS
        if CURRENT_PROCESS is not None:
            CURRENT_PROCESS.terminate()

        if depth is None:
            max_time = wtime
            inc_time = winc
            if CURRENT_BOARD.turn == COLOR.BLACK:
                max_time = btime
                inc_time = binc
            process = multiprocessing.Process(
                target=best_move,
                args=(CURRENT_BOARD,),
                kwargs={
                    "max_time": max_time // 1000,
                    "inc_time": inc_time // 1000,
                    "eval_guess": current_eval,
                    "rand_count": max(1, 2 * (5 - CURRENT_BOARD.full_move)),
                    "transposition_table": TRANSPOSITION_TABLE,
                },
                daemon=False,
            )
        else:
            process = multiprocessing.Process(
                target=best_move,
                args=(CURRENT_BOARD,),
                kwargs={
                    "max_depth": depth,
                    "eval_guess": current_eval,
                    "transposition_table": TRANSPOSITION_TABLE,
                },
                daemon=False,
            )
        process.start()
        CURRENT_PROCESS = process
    return []


if __name__ == "__main__":

    if len(sys.argv) == 1:
        with multiprocessing.Manager() as manager:
            TRANSPOSITION_TABLE = TranspositionTable(manager.dict())
            while True:
                line = input()
                for line in uci_parser(line):
                    print(line)
        sys.exit()

    if sys.argv[1] == "-h" or sys.argv[1] == "--help":
        print((
            "Usage:\n"
            "   run.py\n"
            "   run.py (-h | --help | --version)\n"
        ))
        sys.exit()

    if sys.argv[1] == "--version":
        print(f"{VERSION}")
        sys.exit()
