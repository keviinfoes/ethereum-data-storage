import os
import io
import json
import store_ens

from dotenv import load_dotenv
from eth_abi import abi
from web3 import HTTPProvider, Web3

from pathlib import Path

load_dotenv()

def deploy_calldata():
    #Load rpc
    rpc_execution_url = os.getenv("SEPOLIA_EXECUTION_QUICKNODE")
    w3 = Web3(HTTPProvider(rpc_execution_url))

    private_key = os.getenv("SEPOLIA_PRIVATE_KEY")
    acct = w3.eth.account.from_key(private_key)

    # storage contract data
    text = "Calldata storage"
    storage_address = w3.to_checksum_address("0x00000000"+text.encode().hex())
    storage_abi = '[{"inputs":[{"internalType":"bytes","name":"data","type":"bytes"}],"name":"store","outputs":[],"stateMutability":"nonpayable","type":"function"}]'
    storage = w3.eth.contract(address=storage_address, abi=storage_abi)

    #User input
    ens_name = input("\nENS name: ")
    version = input("version: ")

    #Deploy folder to calldata
    print("encoding calldata")

    # load txt and create blobs
    with io.open("./folder.txt", 'rb') as f:
        file = f.read()
    encode = abi.encode(["bytes"], [file])

    DATA = []
    i = 0
    split = 128000
    while i < (len(encode) // split):
        DATA.append(encode[i*split : (i+1) * split])
        i += 1
    if (len(encode) % split != 0):
        DATA.append(encode[i*split : ])

    # send calldata
    print("storing calldata")
    txt_hash = []
    nonce = w3.eth.get_transaction_count(acct.address)
    for x, data in enumerate(DATA):
        storage_txt = storage.functions.store(data).build_transaction({
            "from": acct.address,
            "nonce": nonce + x,
        })
        print(f"\ntxt {x} max priority fee: {storage_txt['maxPriorityFeePerGas']} wei per gas")
        print(f"txt {x} max total fee: {storage_txt['maxFeePerGas']} wei per gas")
        print("\nDo you accept the max per gas fees")
        response = None
        while response not in {"yes", "no"}:
            response = input("Please type yes or no: ")
        if response == "yes":
            signed = w3.eth.account.sign_transaction(storage_txt, private_key=acct.key)
            hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            w3.eth.wait_for_transaction_receipt(hash)
            txt_hash.append(hash.hex())
            print(f"TransactionHash {x}: {'0x'+hash.hex()}")
        elif response == "no":
            maxPriority = input("new max priority fee in wei: ")
            maxFee = input("new max total fee in wei: ")
            storage_txt = storage.functions.store(data).build_transaction({
                "from": acct.address,
                "nonce": nonce + x,
                "maxPriorityFeePerGas": int(maxPriority),
                "maxFeePerGas": int(maxFee),

            })
            signed = w3.eth.account.sign_transaction(storage_txt, private_key=acct.key)
            hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            w3.eth.wait_for_transaction_receipt(hash)
            txt_hash.append(hash.hex())
            print(f"TransactionHash {x}: {'0x'+hash.hex()}")

    os.remove("./folder.txt")   

    #Create link file
    assert len(txt_hash) != 0

    print("storing calldata links")
    value = {}
    value['type'] = "calldata"
    value['name'] = ens_name
    value['version'] = version
    value['tx_hash'] = txt_hash
    json_value = json.dumps(value)

    Path(f"deployed/{ens_name}/{version}").mkdir(parents=True, exist_ok=True)
    with open(f"deployed/{ens_name}/{version}/calldata_storage.txt", "w") as file: 
        file.write(json_value)

    print(f"\nDo you want to update the ENS link")
    response = None
    while response not in {"yes", "no"}:
        response = input("Please type yes or no: ")

    if(response == "yes"):
        store_ens.ens_store(value)
    else:
        print("please update ENS link later")