# Blob storage dApp
Deploy and retrieve dApps from blob storage (bApp). 

>[!WARNING]
Network: ethereum sepolia testnet.

## Getting started
Add private key and quicknode rpc urls to environment variables, for reference check .env_example file. 

### Install Dependencies
```python3 -m pip install -r requirements.txt```

### Deploy dApp
Only use ENS names owned by the private key.

```python3 deploy.py```

### Retrieve dApp
The retrieve script starts the downloaded bApp from a flask server, only tested with reactjs builds and quicknodes rpc. 

```python3 retrieve.py```
