# Ethereum data storage
Deploy and retrieve files from permanent (calldata) storage or temporary (blob) storage. 

>[!WARNING]
Network: ethereum sepolia testnet.

## Getting started
Add private key and rpc urls to environment variables, for reference check .env_example file. 

### Install Dependencies
```python3 -m pip install -r requirements.txt```

### Deploy data
Only use ENS names owned by the private key. Deploy tested with local and quicknodes rpc. 

```python3 deploy.py```

### Store ENS link
Only use ENS names owned by the private key.

```python3 store.py```

### Retrieve data
Retrieve tested with local and quicknodes rpc. 

```python3 retrieve.py```

### Run app build
Flask server that runs downloaded build folders. Tested with reactjs builds. 

```python3 run.py```
