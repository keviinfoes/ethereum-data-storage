import os
import io
import json
import ckzg
import hashlib
import store_ens

from dotenv import load_dotenv
from eth_abi import abi
from eth_utils import to_hex, to_int
from web3 import HTTPProvider, Web3
from pathlib import Path

load_dotenv()

def deploy_blobs():
    #Load rpc
    rpc_execution_url = os.getenv("EXECUTION_QUICKNODE")
    w3 = Web3(HTTPProvider(rpc_execution_url))

    #Input
    # blob data
    max_blobs_txt = 6

    # txt data
    private_key = os.getenv("PRIVATE_KEY")
    chain_id = w3.eth.chain_id  
    maxFeePerGas = 10**9
    maxPriorityFeePerGas = 10**9
    maxFeePerBlobGas = to_hex(10**12)
    
    text = "Blob storage"
    to = w3.to_checksum_address("0x0000000000000000"+text.encode().hex())
    #User input
    ens_name = input("\nENS name: ")
    version = input("version: ")

    #Deploy folder to blobs
    print("encoding blobs")

    # load txt and create blobs
    # Notice: conversion to hex() doubles size. blob_to_kzg_commitment() fails when not converted!
    with io.open("./folder.txt", 'rb') as f:
        file = f.read()
        hex_file = file.hex()

    ts = ckzg.load_trusted_setup("shared/trusted_setup.txt", 0)
    blob_hash = []
    blob_positions = []
    BLOB_DATA = []
    blob_size = 131072
    split = 131008
    i = 0
    while i < (len(hex_file) // split):
        encoded = abi.encode(["string"], [hex_file[i*split : (i+1) * split]])
        BLOB_DATA.append(encoded)
        # store blob meta
        calc_commitment = ckzg.blob_to_kzg_commitment(encoded, ts)
        sha256_hash = hashlib.sha256(calc_commitment).digest()
        versioned_hash = b'\x01' + sha256_hash[1:]
        blob_hash.append(versioned_hash.hex())
        blob_positions.append(["0", str(blob_size)])
        i += 1
    if (len(hex_file) % split != 0):
        encoded = abi.encode(["string"], [hex_file[i*split : ]])
        required_padding = blob_size - (len(encoded) % blob_size)
        BLOB_DATA.append((b"\x00" * required_padding) + encoded)
        # store blob meta
        calc_commitment = ckzg.blob_to_kzg_commitment((b"\x00" * required_padding) + encoded, ts)
        sha256_hash = hashlib.sha256(calc_commitment).digest()
        versioned_hash = b'\x01' + sha256_hash[1:]
        blob_hash.append(versioned_hash.hex())
        blob_positions.append([str(required_padding) , str(blob_size)])

    # create blob txt
    acct = w3.eth.account.from_key(private_key)
    nonce = w3.eth.get_transaction_count(acct.address)
    SIG_TXT = []
    i = 0
    while i < (len(BLOB_DATA) // max_blobs_txt):
        print(f"\ntxt {i} max priority fee: {maxPriorityFeePerGas} wei per gas")
        print(f"txt {i} max txt fee: {maxFeePerGas} wei per gas")
        print(f"txt {i} max blob fee: {to_int(hexstr=maxFeePerBlobGas)} wei per gas")
        print("\nDo you accept the max per gas fees")
        response = None
        while response not in {"yes", "no"}:
            response = input("Please type yes or no: ")
        if response == "yes":
            tx = {
                "type": 3,
                "chainId": chain_id,  
                "from": acct.address,
                "to": to,
                "value": 0,
                "maxFeePerGas": maxFeePerGas,
                "maxPriorityFeePerGas": maxPriorityFeePerGas,
                "maxFeePerBlobGas": maxFeePerBlobGas,
                "nonce": nonce + i,
            }
        elif response == "no":
            maxPriority = input("new max priority fee in wei: ")
            maxPriorityFeePerGas = int(maxPriority)
            maxFee = input("new max txt fee in wei: ")
            maxFeePerGas = int(maxFee)
            maxBlob = input("new max blob fee in wei: ")
            maxFeePerBlobGas = to_hex(int(maxBlob))
            tx = {
                "type": 3,
                "chainId": chain_id,  
                "from": acct.address,
                "to": to,
                "value": 0,
                "maxFeePerGas": maxFeePerGas,
                "maxPriorityFeePerGas": maxPriorityFeePerGas,
                "maxFeePerBlobGas": maxFeePerBlobGas,
                "nonce": nonce + i,
            }
        blob_input = BLOB_DATA[i*max : (i+1)*max_blobs_txt]
        gas_estimate = w3.eth.estimate_gas(tx)
        tx["gas"] = gas_estimate
        signed = acct.sign_transaction(tx, blobs=blob_input)
        SIG_TXT.append(signed)
        i += 1
    if (len(BLOB_DATA) % max_blobs_txt != 0):
        print(f"\ntxt {i} max priority fee: {maxPriorityFeePerGas} wei per gas")
        print(f"txt {i} max txt fee: {maxFeePerGas} wei per gas")
        print(f"txt {i} max blob fee: {to_int(hexstr=maxFeePerBlobGas)} wei per gas")
        print("\nDo you accept the max per gas fees")
        response = None
        while response not in {"yes", "no"}:
            response = input("Please type yes or no: ")
        if response == "yes":
            tx = {
                "type": 3,
                "chainId": chain_id,  
                "from": acct.address,
                "to": to,
                "value": 0,
                "maxFeePerGas": maxFeePerGas,
                "maxPriorityFeePerGas": maxPriorityFeePerGas,
                "maxFeePerBlobGas": maxFeePerBlobGas,
                "nonce": nonce + i,
            }
        elif response == "no":
            maxPriority = input("new max priority fee in wei: ")
            maxPriorityFeePerGas = int(maxPriority)
            maxFee = input("new max txt fee in wei: ")
            maxFeePerGas = int(maxFee)
            maxBlob = input("new max blob fee in wei: ")
            maxFeePerBlobGas = to_hex(int(maxBlob))
            tx = {
                "type": 3,
                "chainId": chain_id,  
                "from": acct.address,
                "to": to,
                "value": 0,
                "maxFeePerGas": maxFeePerGas,
                "maxPriorityFeePerGas": maxPriorityFeePerGas,
                "maxFeePerBlobGas": maxFeePerBlobGas,
                "nonce": nonce + i,
            }
        blob_input = BLOB_DATA[i*max_blobs_txt : (i+1)*max_blobs_txt]
        gas_estimate = w3.eth.estimate_gas(tx)
        tx["gas"] = gas_estimate
        signed = acct.sign_transaction(tx, blobs=blob_input)
        SIG_TXT.append(signed)

    # send blobs txt to network
    print("storing blobs")
    block_numbers = []
    for x, txt in enumerate(SIG_TXT):
        tx_hash = w3.eth.send_raw_transaction(txt.raw_transaction)
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"TransactionHash: {'0x'+tx_receipt.transactionHash.hex()}")
        i = 0
        while i < len(BLOB_DATA[x*max_blobs_txt: (x+1)*max_blobs_txt]):
            block_numbers.append(tx_receipt.blockNumber)
            i += 1   
    
    os.remove("./folder.txt")

    #Create link file
    assert len(block_numbers) != 0
    assert len(blob_hash) != 0
    assert len(blob_positions) != 0
    assert len(block_numbers) == len(blob_hash) == len(blob_positions)

    # create ens setText txt
    print("storing blob links")

    value = {}
    value['type'] = "blobs"
    value['name'] = ens_name
    value['version'] = version
    value['block_number'] = block_numbers
    value['blob_hash'] = blob_hash
    value['blob_position'] = blob_positions
    json_value = json.dumps(value)

    Path(f"deployed/{ens_name}/{version}").mkdir(parents=True, exist_ok=True)
    with open(f"deployed/{ens_name}/{version}/blob_storage.txt", "w") as file: 
        file.write(json_value)

    print(f"\nDo you want to update the ENS link")
    response = None
    while response not in {"yes", "no"}:
        response = input("Please type yes or no: ")

    if(response == "yes"):
        store_ens.ens_store(value)
    else:
        print("please update ENS link later")