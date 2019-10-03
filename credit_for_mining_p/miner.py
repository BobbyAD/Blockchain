import hashlib
import requests
import json

from uuid import uuid4

import sys

import os.path
from os import path

# TODO: Implement functionality to search for a proof 
def valid_proof(block_string, proof):
    """
    Validates the Proof:  Does hash(block_string, proof) contain 6
    leading zeroes?  Return true if the proof is valid
    :param block_string: <string> The stringified block to use to
    check in combination with `proof`
    :param proof: <int?> The value that when combined with the
    stringified previous block results in a hash that has the
    correct number of leading zeroes.
    :return: True if the resulting hash is a valid proof, False otherwise
    """
    guess = f'{block_string}{proof}'.encode()
    guess_hash = hashlib.sha256(guess).hexdigest()

    #Change back to 6 zeroes
    return guess_hash[:3] == "000"


def proof_of_work(block):
    """
    Simple Proof of Work Algorithm
    Find a number p such that hash(last_block_string, p) contains 6 leading
    zeroes
    :return: A valid proof for the provided block
    """
    block_string = json.dumps(block, sort_keys=True).encode()

    proof = 0
    while valid_proof(block_string, proof) is False:
        proof += 1
    print("Wow!")
    return proof

if __name__ == '__main__':
    # What node are we interacting with?
    if len(sys.argv) > 1:
        node = sys.argv[1]
    else:
        node = "http://localhost:5000"

    if path.exists("my_id.txt"):
        pass
    else:
        with open("my_id.txt", "w") as text:
            new_id = str(uuid4()).replace('-', '')
            text.write(new_id)
            text.close()

    coins_mined = 0
    # Run forever until interrupted
    while True:
        # TODO: Get the last proof from the server and look for a new one
        # TODO: When found, POST it to the server {"proof": new_proof}
        # TODO: We're going to have to research how to do a POST in Python
        # HINT: Research `requests` and remember we're sending our data as JSON
        # TODO: If the server responds with 'New Block Forged'
        # add 1 to the number of coins mined and print it.  Otherwise,
        # print the message from the server.
        get = requests.get(url = f"{node}/last_block")
        last_block = get.json()['last_block']
        proof = proof_of_work(last_block)

        block_string = json.dumps(last_block, sort_keys=True).encode()
        guess = f'{block_string}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()

        # print(block_string)
        # print(guess_hash)

        data = {
            "proof": proof
        }
        post = requests.post(url = f"{node}/mine", json=data)
        print(post.json())
        if post.json()['message'] == "New Block Forged":
            coins_mined += 1
            print(coins_mined)