"""
war card game client and server
"""
import asyncio
from collections import namedtuple
from enum import Enum
import logging
import random
import socket
import socketserver
import threading
import sys
from threading import Thread 

"""
Namedtuples work like classes, but are much more lightweight so they end
up being faster. It would be a good idea to keep objects in each of these
for each game which contain the game's state, for instance things like the
socket, the cards given, the cards still available, etc.
"""
Game = namedtuple("Game", ["p1", "p2"])
Array_of_players = []
Array_of_Games = []
counter = 1
class Command(Enum):
    """
    The byte values sent as the first byte of any message in the war protocol.
    """
    WANTGAME = 0
    GAMESTART = 1
    PLAYCARD = 2
    PLAYRESULT = 3


class Result(Enum):
    """
    The byte values sent as the payload byte of a PLAYRESULT message.
    """
    WIN = 0
    DRAW = 1
    LOSE = 2

def readexactly(sock, numbytes):
    """
    Accumulate exactly `numbytes` from `sock` and return those. If EOF is found
    before numbytes have been received, be sure to account for that here or in
    the caller.
    """
    pass

def kill_game(p1_writer, p2_writer):
    """
    TODO: If either client sends a bad message, immediately nuke the game.
    """
    p1_writer.close()
    p2_writer.close()
    pass

def get_card_value(card):
    return (card % 13)

def if_valid_move(card, deck):
    if card in deck:
        del deck[deck.index(card)]
        return (True, deck)
    else:
        return (False, deck)

def compare_cards(card1, card2, p1_deck, p2_deck):
    """
    TODO: Given an integer card representation, return -1 for card1 < card2,
    0 for card1 = card2, and 1 for card1 > card2
    return 2 if fails valid move condition
    """
    (state, p1_deck) = if_valid_move(card1, p1_deck)
    if state== False:
        return (2, p1_deck, p2_deck)
    (state, p2_deck) = if_valid_move(card2, p2_deck)
    if state == False:
        return (2, p1_deck, p2_deck)

    card1_value = get_card_value(card1)
    card2_value = get_card_value(card2)
    if card1 < card2:
        return (-1, p1_deck, p2_deck)
    elif card1 > card2:
        return (1, p1_deck, p2_deck)
    else:
        return (0, p1_deck, p2_deck)

def deal_cards():
    """
    TODO: Randomize a deck of cards (list of ints 0..51), and return two
    26 card "hands."
    """
    cardDeck = [x for x in range(52)]
    random.shuffle(cardDeck)
    return splitter(cardDeck)

def splitter(A):
    B = A[0:len(A)//2]
    C = A[len(A)//2:]
    return (B,C)

def convertDeckToPayload(list):
    payload = bytes([1])
    for x in list:
        payload += bytes([x])
    return payload

async def start_game(p1_reader,p1_writer, p2_reader, p2_writer):
    wantgame_check = bytes([Command.WANTGAME.value, 0])
    p1_data = await p1_reader.read(2)
    p2_data = await p2_reader.read(2)
    if p1_data == wantgame_check and p2_data == wantgame_check:
        (p1_deck, p2_deck) = deal_cards()
        payload = convertDeckToPayload(p1_deck)
        p1_writer.write(convertDeckToPayload(p1_deck))
        p2_writer.write(convertDeckToPayload(p2_deck))
        for i in range(26):
            p1_data = await p1_reader.readexactly(2)
            p2_data = await p2_reader.readexactly(2)
            if p1_data[0] == Command.PLAYCARD.value and p2_data[0] == Command.PLAYCARD.value:
                (round_result, p1_deck, p2_deck) = compare_cards(p1_data[1], p2_data[1], p1_deck, p2_deck)
                if round_result == 2:
                    kill_game(p1_writer, p2_writer)
                    break
                if round_result == -1:
                    p1_writer.write(bytes([Command.PLAYRESULT.value, Result.LOSE.value]))
                    p2_writer.write(bytes([Command.PLAYRESULT.value, Result.WIN.value]))
                elif round_result == 1:
                    p1_writer.write(bytes([Command.PLAYRESULT.value, Result.WIN.value]))
                    p2_writer.write(bytes([Command.PLAYRESULT.value, Result.LOSE.value]))
                else:
                    p1_writer.write(bytes([Command.PLAYRESULT.value, Result.DRAW.value]))
                    p2_writer.write(bytes([Command.PLAYRESULT.value, Result.DRAW.value]))
            else:
                break
        kill_game(p1_writer, p2_writer)
    pass

async def wait_for_clients(reader, writer):
    if not Array_of_players:
        Array_of_players.append((reader, writer))
    else:
        (p1_reader, p1_writer) = Array_of_players[0]
        Array_of_players.pop(0)
        await start_game(p1_reader, p1_writer, reader, writer)
    pass

def serve_game(host, port):
    """
    TODO: Open a socket for listening for new connections on host:port, and
    perform the war protocol to serve a game of war between each client.
    This function should run forever, continually serving clients.
    """
    loop = asyncio.get_event_loop()
    coro = asyncio.start_server(wait_for_clients, host, port, loop=loop)
    server = loop.run_until_complete(coro)
    # Serve requests until Ctrl+C is pressed
    print('Serving on {}'.format(server.sockets[0].getsockname()))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()

    pass

async def limit_client(host, port, loop, sem):
    """
    Limit the number of clients currently executing.
    You do not need to change this function.
    """
    async with sem:
        return await client(host, port, loop)

async def client(host, port, loop):
    """
    Run an individual client on a given event loop.
    You do not need to change this function.
    """
    try:
        reader, writer = await asyncio.open_connection(host, port, loop=loop)
        # send want game
        writer.write(b"\0\0")
        card_msg = await reader.readexactly(27)
        myscore = 0
        for card in card_msg[1:]:
            writer.write(bytes([Command.PLAYCARD.value, card]))
            result = await reader.readexactly(2)
            if result[1] == Result.WIN.value:
                myscore += 1
            elif result[1] == Result.LOSE.value:
                myscore -= 1
        if myscore > 0:
            result = "won"
        elif myscore < 0:
            result = "lost"
        else:
            result = "drew"
        logging.debug("Game complete, I %s", result)
        writer.close()
        return 1
    except ConnectionResetError:
        logging.error("ConnectionResetError")
        return 0
    except asyncio.streams.IncompleteReadError:
        logging.error("asyncio.streams.IncompleteReadError")
        return 0
    except OSError:
        logging.error("OSError")
        return 0

def main(args):
    """
    launch a client/server
    """
    host = args[1]
    port = int(args[2])
    if args[0] == "server":
        try:
            # your server should serve clients until the user presses ctrl+c
            serve_game(host, port)
        except KeyboardInterrupt:
            pass
        return
    else:
        loop = asyncio.get_event_loop()

    if args[0] == "client":
        loop.run_until_complete(client(host, port, loop))
    elif args[0] == "clients":
        sem = asyncio.Semaphore(1000)
        num_clients = int(args[3])
        clients = [limit_client(host, port, loop, sem)
                   for x in range(num_clients)]
        async def run_all_clients():
            """
            use `as_completed` to spawn all clients simultaneously
            and collect their results in arbitrary order.
            """
            completed_clients = 0
            for client_result in asyncio.as_completed(clients):
                completed_clients += await client_result
            return completed_clients
        res = loop.run_until_complete(
            asyncio.Task(run_all_clients(), loop=loop))
        logging.info("%d completed clients", res)

    loop.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main(sys.argv[1:])
