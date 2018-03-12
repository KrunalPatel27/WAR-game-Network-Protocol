import random
def deal_cards():
    """
    TODO: Randomize a deck of cards (list of ints 0..51), and return two
    26 card "hands."
    """
    cardDeck = [x for x in range(52)]
    random.shuffle(cardDeck)
    splitter(cardDeck)
    return splitter(cardDeck)

def splitter(A):
    B = A[0:len(A)//2]
    C = A[len(A)//2:]
    return (B,C)

print(deal_cards())