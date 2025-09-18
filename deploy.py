import os
import io
import shutil
import deploy_blobs
import deploy_calldata

from pathlib import Path

from web3 import HTTPProvider, Web3
from eth_abi import abi

#Env input
rpc_execution_url = os.getenv("EXECUTION_QUICKNODE")
w3 = Web3(HTTPProvider(rpc_execution_url))

#Calldata storage contract
text = "Calldata storage"
storage_address = w3.to_checksum_address("0x00000000"+text.encode().hex())
storage_abi = '[{"inputs":[{"internalType":"bytes","name":"data","type":"bytes"}],"name":"store","outputs":[],"stateMutability":"nonpayable","type":"function"}]'
storage = w3.eth.contract(address=storage_address, abi=storage_abi)

#User input
current_directory = os.getcwd()
folder_location_example = current_directory + "/example"
folder_location = input("Folder location [empty for /example]: ")
if folder_location == "":
    folder_location = folder_location_example

#Get gasprice
base_gas_price = w3.eth.fee_history(1, 'latest')

#Generate data
shutil.make_archive('folder', 'zip', folder_location)
p = Path('./folder.zip')
p.rename(p.with_suffix('.txt'))

with io.open("./folder.txt", 'rb') as f:
    file = f.read()
    hex_file = file.hex()

#Estimate gascost calldata
DATA = []
i = 0
split = 128000
encoded_calldata = abi.encode(["bytes"], [file])
while i < (len(encoded_calldata) // split):
    DATA.append(encoded_calldata[i*split : (i+1) * split])
    i += 1
if (len(encoded_calldata) % split != 0):
    DATA.append(encoded_calldata[i*split : ])

gas_estimate = 0
nonce = w3.eth.get_transaction_count("0x0000000000000000000000000000000000000000")
for x, data in enumerate(DATA):
    storage_txt = storage.functions.store(data).build_transaction({
        "from": "0x0000000000000000000000000000000000000000",
        "nonce": nonce + x,
    })
    gas_estimate += w3.eth.estimate_gas(storage_txt)

gas_cost_calldata = gas_estimate * base_gas_price.baseFeePerGas[1]
print(f"\nbase gascost estimate permanent: ~{w3.from_wei(gas_cost_calldata, 'ether')} ETH")

#Estimate gascost blobs
BLOB_DATA = []
blob_size = 131072
split = 131008
i = 0
while i < (len(hex_file) // split):
    encoded = abi.encode(["string"], [hex_file[i*split : (i+1) * split]])
    BLOB_DATA.append(encoded)
    i += 1
if (len(hex_file) % split != 0):
    encoded = abi.encode(["string"], [hex_file[i*split : ]])
    required_padding = blob_size - (len(encoded) % blob_size)
    BLOB_DATA.append((b"\x00" * required_padding) + encoded)

number_blobs = len(BLOB_DATA)
blob_gas = 131072 * number_blobs 
txt_cost = 21000 * base_gas_price.baseFeePerGas[1]
blob_cost = blob_gas * int(base_gas_price.baseFeePerBlobGas[1], 16)
print(f"base gascost estimate temporary: ~{w3.from_wei(blob_cost + txt_cost, 'ether')} ETH")
 
ratio = gas_cost_calldata / (blob_cost + txt_cost) 
if ratio > 1:
    print(f"current temporary storage is: ~{round(ratio)}x cheaper")
else:
    print(f"current temporary storage is: ~{round(1/ratio)}x more expensive")

print("\nDo you want to store the data:\n [1] permanent\n [2] temporary (~18 days)\n")
response = None
while response not in {"1", "2"}:
    response = input("Please type 1 or 2: ")

if response == "1":
    deploy_calldata.deploy_calldata()
elif response == "2":
    deploy_blobs.deploy_blobs()
