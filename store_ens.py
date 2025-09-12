import os
import idna
import json

from dotenv import load_dotenv
from hexbytes import HexBytes
from web3 import HTTPProvider, Web3

load_dotenv()

def ens_store(link_data):
    #Load rpc
    rpc_execution_url = os.getenv("SEPOLIA_EXECUTION_QUICKNODE")
    w3 = Web3(HTTPProvider(rpc_execution_url))

    private_key = os.getenv("SEPOLIA_PRIVATE_KEY")
    acct = w3.eth.account.from_key(private_key)

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
    ens_address = "0x8FADE66B79cC9f707aB26799354482EB93a5B7dD" #sepolia address
    ens_abi = d['abi']
    resolver_instance = w3.eth.contract(address=ens_address, abi=ens_abi)

    node = raw_name_to_hash(link_data['name'])
    if(link_data['type'] == "calldata"):
        key = "EDSc"
    elif(link_data['type'] == "blobs"):
        key = "EDSb"
    else:
        exit()

    del link_data['type']
    del link_data['name']

    json_value = json.dumps(link_data)

    #ENS setText   
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