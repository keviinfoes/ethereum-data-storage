import os
import json

import retrieve_blobs
import retrieve_calldata

from web3 import Web3, HTTPProvider
from ens import ENS

#Env input
rpc_url = os.getenv("SEPOLIA_EXECUTION_QUICKNODE")
w3 = Web3(HTTPProvider(rpc_url))
ns = ENS.from_web3(w3)

#User input
ens_name_example = 'hellosepolia.eth'
ens_name = input("ENS name [empty for hellosepolia.eth example]: ")
if ens_name == "":
    ens_name = ens_name_example

#Get calldata and blob location
locations = []
location_calldata = ns.get_text(ens_name, "EDSc")
location_blobs = ns.get_text(ens_name, "EDSb")

if(location_calldata != "" and location_blobs != ""):
    calldata_json = json.loads(location_calldata)
    blobs_json = json.loads(location_blobs)
    print(f"\nDo you want to retrieve the:\n [1] permanent data v{calldata_json['version']}\n [2] temporary data v{blobs_json['version']}\n")
    response = None
    while response not in {"1", "2"}:
        response = input("Please type 1 or 2: ")
    if(response == "1"):
        retrieve_calldata.retrieve_calldata(ens_name, calldata_json)
    elif(response == "2"):
        retrieve_blobs.retrieve_blobs(ens_name, blobs_json)
    else:
        print("error: false response")
elif(location_calldata != "" and location_blobs == ""):
    calldata_json = json.loads(location_calldata)
    print(f"\nDo you want to retrieve permanent storage v{calldata_json['version']}")
    response = None
    while response not in {"yes", "no"}:
        response = input("Please type yes or no: ")
    if(response == "yes"):
        retrieve_calldata.retrieve_calldata(ens_name, calldata_json)
    elif(response == "no"):
        print("aborted retrieve")
    else:
        print("error: false response")
elif(location_blobs != "" and location_calldata == ""):
    blobs_json = json.loads(location_blobs)
    print(f"\nDo you want to retrieve temporary storage v{blobs_json['version']}")
    response = None
    while response not in {"yes", "no"}:
        response = input("Please type yes or no: ")
    if(response == "yes"):
        retrieve_blobs.retrieve_blobs(ens_name, blobs_json)
    elif(response == "no"):
        print("aborted retrieve")
    else:
        print("error: false response")
else:
    print("\nNo storage link available")