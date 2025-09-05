import os
import shutil
import io
import json
import idna
import ckzg
import hashlib

from dotenv import load_dotenv
from eth_abi import abi
from eth_utils import to_hex
from web3 import HTTPProvider, Web3
from ens import ENS
from hexbytes import HexBytes
from pathlib import Path

load_dotenv()

#Load rpc
rpc_execution_url = os.getenv("SEPOLIA_EXECUTION_QUICKNODE")
w3 = Web3(HTTPProvider(rpc_execution_url))
ns = ENS.from_web3(w3)

#Input
# blob data
max_blobs_txt = 6

# txt data
private_key = os.getenv("SEPOLIA_PRIVATE_KEY")
chain_id = 11155111 #sepolia id  
maxFeePerGas = 10**9
maxPriorityFeePerGas = 10**9
maxFeePerBlobGas = to_hex(10**9)
to = '0x0000000000000000000000000000000000000000'

# ens data
ens_address = "0x8FADE66B79cC9f707aB26799354482EB93a5B7dD" #sepolia address

#User input
ens_name = input("ENS name: ")
bapp_version = input("bApp version: ")
dApp_location = input("location bApp build: ")

#Setup ENS
# ens connector functions
def normalize_name(name: str) -> str:
    if not name:
        return name
    elif isinstance(name, (bytes, bytearray)):
        name = name.decode("utf-8")
    try:
        return idna.uts46_remap(name, std3_rules=True, transitional=False)
    except idna.IDNAError as exc:
        raise InvalidName(f"{name} is an invalid name, because {exc}") from exc

EMPTY_SHA3_BYTES = HexBytes(b"\0" * 32)

def label_to_hash(label: str) -> HexBytes:
    label = normalize_name(label)
    if "." in label:
        raise ValueError(f"Cannot generate hash for label {label!r} with a '.'")
    return Web3().keccak(text=label)

def normal_name_to_hash(name: str) -> HexBytes:
    node = EMPTY_SHA3_BYTES
    if name:
        labels = name.split(".")
        for label in reversed(labels):
            labelhash = label_to_hash(label)
            assert isinstance(labelhash, bytes)
            assert isinstance(node, bytes)
            node = Web3().keccak(node + labelhash)
    return node

def raw_name_to_hash(name: str) -> HexBytes:
    normalized_name = normalize_name(name)
    return normal_name_to_hash(normalized_name)

# load ens rpc
with open("shared/PublicResolver.json") as f:
    d = json.load(f)

ens_abi = d['abi']
resolver_instance = w3.eth.contract(address=ens_address, abi=ens_abi)

#Deploy dApp to blobs
print("encoding bApp blobs")
# zip dApp folder
shutil.make_archive('dApp', 'zip', dApp_location)

# convert zip to txt
p = Path('./dApp.zip')
p.rename(p.with_suffix('.txt'))

# load txt and create blobs
with io.open("./dApp.txt", 'rb') as f:
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
print("storing bApp blobs")
block_numbers = []
for x, txt in enumerate(SIG_TXT):
    tx_hash = w3.eth.send_raw_transaction(txt.raw_transaction)
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"TransactionHash: {'0x'+tx_receipt.transactionHash.hex()}")
    i = 0
    while i < len(BLOB_DATA[x*max_blobs_txt: (x+1)*max_blobs_txt]):
        block_numbers.append(tx_receipt.blockNumber)
        i += 1   

#Store blob data in ENS
assert len(block_numbers) != 0
assert len(blob_hash) != 0
assert len(blob_positions) != 0
assert len(block_numbers) == len(blob_hash) == len(blob_positions)

# create ens setText txt
print("updating ENS bApp link")
node = raw_name_to_hash(ens_name)
key = "bapp" 
value = {}
value['version'] = bapp_version
value['block_number'] = block_numbers
value['blob_hash'] = blob_hash
value['blob_position'] = blob_positions
json_value = json.dumps(value)

transaction = resolver_instance.functions.setText(node, key, json_value).build_transaction({"from": acct.address})
signed_txn = w3.eth.account.sign_transaction(dict(
    nonce=w3.eth.get_transaction_count(acct.address),
    maxFeePerGas=transaction.get('maxFeePerGas'),
    maxPriorityFeePerGas=transaction.get('maxPriorityFeePerGas'),
    gas=transaction.get('gas'),
    to=transaction.get('to'),
    value=transaction.get('value'),
    data=transaction.get('data'),
    chainId=transaction.get('chainId'),
), private_key)
print("TransactionHash: 0x"+w3.eth.send_raw_transaction(signed_txn.raw_transaction).hex())

os.remove("./dApp.txt")




