import os
import requests
import ckzg
import hashlib
import json
import shutil
import webbrowser 

from web3 import Web3, HTTPProvider
from ens import ENS
from eth_abi import abi
from dotenv import load_dotenv
from pathlib import Path
from flask import Flask, render_template
from threading import Timer

load_dotenv()

#User input
bapp_name_example = 'bapp.eth'
bapp_name = input("ENS name [empty for bapp.eth example]: ")
if bapp_name == "":
    bapp_name = bapp_name_example

# setup enviroment
rpc_url = os.getenv("SEPOLIA_EXECUTION_QUICKNODE")
w3 = Web3(HTTPProvider(rpc_url))
ns = ENS.from_web3(w3)

# setup account
private_key = os.getenv("SEPOLIA_PRIVATE_KEY")
acct = w3.eth.account.from_key(private_key)

# ens retrieve json blob data
bapp = ns.get_text(bapp_name, "bapp")
bapp_json = json.loads(bapp)
block_numbers = list(map(int, bapp_json['block_number']))
identifications = bapp_json['blob_hash']

# auto update on newer version
if not os.path.isdir(f"retrieved/{bapp_name}/{bapp_json['version']}"):                 
    checked_blocks = []
    for block_number in block_numbers:
        if block_number in checked_blocks:
            continue
        else:
            print("downloading bApp blobs")
            # Check if block is already checked
            checked_blocks.append(block_number)

            # Execution layer: retrieve the block and find type 3 transactions
            block = w3.eth.get_block(block_number, full_transactions=True)
            type_3_tx_hashes = [tx.hash.hex() for tx in block.transactions if tx.type == 3]

            # Execution layer: store blob versioned hashes
            blob_versioned_hashes_dict = {}
            for tx_hash in type_3_tx_hashes:
                tx_details = w3.eth.get_transaction(tx_hash)
                blob_versioned_hashes = tx_details.get('blobVersionedHashes', [])
                temp_hash = []
                for hashes in blob_versioned_hashes:
                    blob_versioned_hashes_dict[hashes.hex()] = tx_hash

            # Execution layer: retrieve beacon block data
            parent_beacon_block_root = block['parentBeaconBlockRoot'].hex()
            if not parent_beacon_block_root.startswith('0x'):
                parent_beacon_block_root = '0x' + parent_beacon_block_root

            # Consensus layer: retrieve slot info
            headers_url = f"{os.getenv('SEPOLIA_CONSENSUS_QUICKNODE')}/eth/v1/beacon/headers/{parent_beacon_block_root}"
            header_response = requests.get(headers_url)
            if header_response.status_code != 200:
                print("Failed to fetch data:", header_response.status_code)
                print(header_response.text)
                exit()
            header_data = header_response.json()
            if 'data' not in header_data:
                print("Unexpected response format:", header_data)
                exit()
            slot_number = int(header_data['data']['header']['message']['slot']) + 1

            # Consensus layer: Retrieve blobs
            blobs_url = f"{os.getenv('SEPOLIA_CONSENSUS_QUICKNODE')}/eth/v1/beacon/blob_sidecars/{slot_number}"
            blobs_response = requests.get(blobs_url).json()
            blobs = blobs_response['data']

            # Local: check blob kzg commitment
            results = []
            for i, blob in enumerate(blobs):
                blob_data_hex = blob['blob']
                blob_data = bytes.fromhex(blob_data_hex.replace("0x", ""))

                # calculate kzg commit and hash from blob
                ts = ckzg.load_trusted_setup("shared/trusted_setup.txt", 0)
                calc_commitment = ckzg.blob_to_kzg_commitment(blob_data, ts)
                sha256_hash = hashlib.sha256(calc_commitment).digest()
                versioned_hash = b'\x01' + sha256_hash[1:]
                stored_commitment = blob['kzg_commitment']
                calc_commitment_hex = '0x' + calc_commitment.hex()

                # check kzg and hash - store blob when correct
                Path(f"retrieved/{bapp_name}/{bapp_json['version']}/blobs").mkdir(parents=True, exist_ok=True)
                if(stored_commitment != calc_commitment_hex or blob_versioned_hashes_dict.get(versioned_hash.hex()) == None):
                    continue
                else:
                    for id in identifications:
                        if id == versioned_hash.hex():
                            with open(f"retrieved/{bapp_name}/{bapp_json['version']}/blobs/{id}.txt", "w") as file:
                                file.write(blob_data_hex)
                
                # store summary of blobs in block                
                results.append({
                    'blob': i,
                    'block': block_number,
                    'commitment': stored_commitment,
                    'versioned_hash': versioned_hash.hex(),
                    'commitment_match': stored_commitment == calc_commitment_hex,
                    'versioned_hash_match': blob_versioned_hashes_dict.get(versioned_hash.hex()) != None
                })
            with open(f"retrieved/{bapp_name}/{bapp_json['version']}/blobs/result_block_{block_number}.txt", "w") as file:
                for result in results:   
                    file.write(f"{result}\n")

        #decode blobs
        print("decoding bApp blobs")
        total_bytes = bytearray()
        position = bapp_json['blob_position']
        for i, id in enumerate(identifications):
            with open(f"retrieved/{bapp_name}/{bapp_json['version']}/blobs/{id}.txt", "r") as file:
                blob_hex = file.read().strip()
                blob_data = bytes.fromhex(blob_hex.replace("0x", ""))  
            after_encoded = blob_data[int(position[i][0]):int(position[i][1])]
            after_decoded = abi.decode(["string"], after_encoded) 
            bytes_file = bytes.fromhex(after_decoded[0])
            total_bytes.extend(bytes_file)

        #write full binary file to zip 
        with open(f"retrieved/{bapp_name}/dApp.txt", "wb") as binary_file:
            binary_file.write(total_bytes)

        #unzip full bapp file
        p = Path(f"retrieved/{bapp_name}/dApp.txt")
        p.rename(p.with_suffix('.zip'))
        shutil.unpack_archive(f"retrieved/{bapp_name}/dApp.zip", f"retrieved/{bapp_name}/dApp", "zip") 

        os.remove(f"retrieved/{bapp_name}/dApp.zip")

print("starting bApp")
#Start flask server with dApp
app = Flask(__name__, static_url_path='',
                  static_folder=f"retrieved/{bapp_name}/dApp",
                  template_folder=f"retrieved/{bapp_name}/dApp") 

@app.route("/")
def hello():
    return render_template("index.html")

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000")

if __name__ == "__main__":
    Timer(1, open_browser).start()
    app.run(host="127.0.0.1", port="")

