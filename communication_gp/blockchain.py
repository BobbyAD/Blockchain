# Paste your version of blockchain.py from the client_mining_p
# folder here

import sys

import hashlib
import json
from time import time
from uuid import uuid4
import requests

from flask import Flask, jsonify, request

from urllib.parse import urlparse


class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()

        self.genesis_block()
    
    def genesis_block(self):
        """
        Create a new Block in the Blockchain

        Hardcoding stuff
        """

        block = {
            'index': 1,
            'timestamp': 1,
            'transactions': [],
            'proof': 1,
            'previous_hash': 1,
        }

        # Reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block)
        return block

    def new_block(self, proof, previous_hash=None):
        """
        Create a new Block in the Blockchain

        :param proof: <int> The proof given by the Proof of Work algorithm
        :param previous_hash: (Optional) <str> Hash of previous Block
        :return: <dict> New Block
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # Reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block)
        self.broadcast_new_block(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        """
        Creates a new transaction to go into the next mined Block

        :param sender: <str> Address of the Recipient
        :param recipient: <str> Address of the Recipient
        :param amount: <int> Amount
        :return: <int> The index of the BLock that will hold this transaction
        """

        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.last_block['index'] + 1

    def register_node(self, node):
        parsed_url = urlparse(node)
        self.nodes.add(parsed_url.netloc)

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block

        :param block": <dict> Block
        "return": <str>
        """


        # json.dumps converts json into a string
        # hashlib.sha246 is used to createa hash
        # It requires a `bytes-like` object, which is what
        # .encode() does.  It convertes the string to bytes.
        # We must make sure that the Dictionary is Ordered,
        # or we'll have inconsistent hashes

        block_string = json.dumps(block, sort_keys=True).encode()

        # By itself, this function returns the hash in a raw string
        # that will likely include escaped characters.
        # This can be hard to read, but .hexdigest() converts the
        # hash to a string using hexadecimal characters, which is
        # easer to work with and understand.  
        return hashlib.sha256(block_string).hexdigest()
    
    def broadcast_new_block(self, block):
        """
            Alert neighbors that a new block ahs been mined and should be added to their chain
        """

        neighbors = self.nodes

        post_data = {"block": block}

        for node in neighbors:
            response = requests.post(f'http://{node}/block/new', json=post_data)

            if response.status_code != 200:
                #TODO: error
                print("error with neighbors")
            
    def add_block(self, block):
        """
            Add a validated received block
        """

        # Reset our pending transactions
        self.current_transactions = []

        self.chain.append(block)

    @property
    def last_block(self):
        return self.chain[-1]



    @staticmethod
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

        #Change back to six zeroes
        return guess_hash[:3] == "000"

    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid.  We'll need this
        later when we are a part of a network.

        :param chain: <list> A blockchain
        :return: <bool> True if valid, False if not
        """

        prev_block = chain[0]
        current_index = 1

        # TODO: test when possible, can't test it yet.

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{prev_block}')
            print(f'{block}')
            print("\n-------------------\n")
            # Check that the hash of the block is correct
            if block['previous_hash'] != self.hash(prev_block):
                print(f"Invalid previous hash on block {current_index}")
                return False

            block_string = json.dumps(prev_block, sort_keys=True).encode()
            if not self.valid_proof(block_string, block['proof']):
                print("Found invalid proof on block {current_index}")
                return False

            prev_block = block
            current_index += 1

        return True


# Instantiate our Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain()


@app.route('/mine', methods=['POST'])
def mine():
    # We run the proof of work algorithm to get the next proof...
    proof = request.get_json()
    block_string = json.dumps(blockchain.last_block, sort_keys=True).encode()

    print(proof)
    print(proof['proof'])
    guess = f'{block_string}{proof["proof"]}'.encode()
    guess_hash = hashlib.sha256(guess).hexdigest()
    print(block_string)
    print(guess_hash)

    if not proof['proof']:
        response = {
            'message': 'INVALID JSON'
        }
        return jsonify(response), 400

    if blockchain.valid_proof(block_string, proof['proof']) is not True:
        response = {
            'message': 'INVALID PROOF'
        }
        return jsonify(response), 400

    # We must receive a reward for finding the proof.
    # The sender is "0" to signify that this node has mine a new coin
    # The recipient is the current node, it did the mining!
    # The amount is 1 coin as a reward for mining the next block
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1
    )

    # Forge the new Block by adding it to the chain
    previous_hash = blockchain.hash(blockchain.last_block)
    block = blockchain.new_block(proof['proof'], previous_hash)

    blockchain.broadcast_new_block(block)

    # Send a response with the new block
    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing Values', 400

    # Create a new Transaction
    index = blockchain.new_transaction(values['sender'],
                                        values['recipient'],
                                        values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain
    }
    return jsonify(response), 200

@app.route('/validchain', methods=['GET'])
def validate_chain():
    result = blockchain.valid_chain(blockchain.chain)

    response = {
        'validity': result
    }

    return jsonify(response), 200

@app.route('/last_block', methods=['GET'])
def get_last_block():
    response = {
        'last_block': blockchain.last_block
    }

    return jsonify(response), 200


#############Additional Code Added by our Colleagues################

# @app.route('/block/new', methods=['POST'])
# def new_block():
#     values = request.get_json()

#     # Check that the required fields are in the POST'ed data
#     required = ['block']
#     if not all(k in values for k in required):
#         return 'Missing Values', 400

#     # TODO: Verify that the sender is one of our peers

#     # TODO: Check that the new block index is 1 higher than our last block
#     # that it has a valid proof

#     # TODO: Otherwise, check for consensus
#     # Don't forget to send a response before asking for the full
#     # chain from a server awaiting a response.

#     return response, 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():

    values = request.get_json()
    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201

@app.route('/block/new', methods=['POST'])
def receive_block():
    values = request.get_json()

    new_block = values['block']
    old_block = blockchain.last_block

    if new_block['index'] == old_block['index'] + 1:
        #Index is correct
        if new_block['previous_hash'] == blockchain.hash(old_block):
            #Hashes are correct
            block_string = json.dumps(old_block, sort_keys=True).encode()
            if blockchain.valid_proof(block_string, new_block['proof']):
                #Proof is valid
                blockchain.add_block(new_block)
                return "block Accepted"
            else:
                #Bad  proof, handle
                pass
        else:
            #Hashes don't match, handle later
            pass
    else:
        # Their index is greater
        # Block could be invalid
        # We could be behind
        
        # Do consensus process
        # Poll all nodes in our  chain, get biggest one
        pass


# TODO: Get rid of the previous if __main__ and use this so we can change
# ports via the command line.  Note that this is not robust and will
# not catch errors
if __name__ == '__main__':
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 5000
    app.run(host='0.0.0.0', port=port)