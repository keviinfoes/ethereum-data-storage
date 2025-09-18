import os
import requests
import ckzg
import hashlib
import shutil

from web3 import Web3, HTTPProvider
from eth_abi import abi
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

def retrieve_blobs(ens_name, blobs_json):
    #Load rpc
    rpc_url = os.getenv("SEPOLIA_EXECUTION_QUICKNODE")
    w3 = Web3(HTTPProvider(rpc_url))

    block_numbers = list(map(int, blobs_json['block_number']))
    identifications = blobs_json['blob_hash']

    # auto update on newer version
    if not os.path.isdir(f"retrieved/{ens_name}/{blobs_json['version']}"):                 
        checked_blocks = []
        for block_number in block_numbers:
            if block_number in checked_blocks:
                continue
            else:
                print("downloading blobs")
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
                blobs_response = requests.get(blobs_url)
                if blobs_response.status_code != 200:
                    print("Failed to fetch data:", blobs_response.status_code)
                    print(blobs_response.text)
                    exit()
                blobs_data = blobs_response.json()
                blobs = blobs_data['data']

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
                    Path(f"retrieved/{ens_name}/{blobs_json['version']}").mkdir(parents=True, exist_ok=True)
                    if(stored_commitment != calc_commitment_hex or blob_versioned_hashes_dict.get(versioned_hash.hex()) == None):
                        continue
                    else:
                        for id in identifications:
                            if id == versioned_hash.hex():
                                with open(f"retrieved/{ens_name}/{blobs_json['version']}/{id}.txt", "w") as file:
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
                with open(f"retrieved/{ens_name}/{blobs_json['version']}/result_block_{block_number}.txt", "w") as file:
                    for result in results:   
                        file.write(f"{result}\n")

            #decode blobs
            print("decoding blobs")
            total_bytes = bytearray()
            position = blobs_json['blob_position']
            for i, id in enumerate(identifications):
                with open(f"retrieved/{ens_name}/{blobs_json['version']}/{id}.txt", "r") as file:
                    blob_hex = file.read().strip()
                    blob_data = bytes.fromhex(blob_hex.replace("0x", ""))  
                after_encoded = blob_data[int(position[i][0]):int(position[i][1])]
                after_decoded = abi.decode(["string"], after_encoded) 
                bytes_file = bytes.fromhex(after_decoded[0])
                total_bytes.extend(bytes_file)

            print("storing latest")
            #write full binary file to zip 
            with open(f"retrieved/{ens_name}/latest.txt", "wb") as binary_file:
                binary_file.write(total_bytes)

            #unzip file
            p = Path(f"retrieved/{ens_name}/latest.txt")
            p.rename(p.with_suffix('.zip'))
            shutil.unpack_archive(f"retrieved/{ens_name}/latest.zip", f"retrieved/{ens_name}/latest", "zip") 

            os.remove(f"retrieved/{ens_name}/latest.zip")