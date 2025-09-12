import os
import shutil

from web3 import Web3, HTTPProvider
from eth_abi import abi
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

def retrieve_calldata(ens_name, calldata_json):
    #Load rpc
    rpc_url = os.getenv("SEPOLIA_EXECUTION_QUICKNODE")
    w3 = Web3(HTTPProvider(rpc_url))    

    #Storage link
    txt_hash = calldata_json['tx_hash']

    # auto update on newer version
    if not os.path.isdir(f"retrieved/{ens_name}/{calldata_json['version']}"):
        print("downloading calldata")     
        Path(f"retrieved/{ens_name}/{calldata_json['version']}").mkdir(parents=True, exist_ok=True)            
        total_bytes = bytearray()
        for x, hash in enumerate(txt_hash):
            receipt = w3.eth.get_transaction(hash)
            total_bytes.extend(receipt.input[68:])

        print("decoding calldata")
        decoded_data = abi.decode(["bytes"], total_bytes)
        with open(f"retrieved/{ens_name}/{calldata_json['version']}/calldata.txt", "wb") as binary_file:
                binary_file.write(decoded_data[0])
        with open(f"retrieved/{ens_name}/latest.txt", "wb") as binary_file:
                binary_file.write(decoded_data[0])

        print("storing latest")
        p = Path(f"retrieved/{ens_name}/latest.txt")
        p.rename(p.with_suffix('.zip'))
        shutil.unpack_archive(f"retrieved/{ens_name}/latest.zip", f"retrieved/{ens_name}/latest", "zip") 

        os.remove(f"retrieved/{ens_name}/latest.zip")