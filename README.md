# Ethereum data storage
Deploy and retrieve files from permanent (calldata) storage or temporary (blob) storage. 

## Getting started
Add private key and RPC to environment variables, for reference check .env_example. Tested with local and QuickNodes RPC. 

>[!CAUTION]
The private key is ONLY required for deployment. It is unencryped and exposed to your machine, be extremely careful. 

### Install Dependencies
```python3 -m pip install -r requirements.txt```

### Deploy data
Only use ENS names owned by the private key. 

```python3 deploy.py```

### Store ENS link
Only use ENS names owned by the private key.

```python3 store.py```

### Retrieve data
```python3 retrieve.py```

### Run app build
Flask server that runs downloaded build folders. Tested with ReactJS builds. 

```python3 run.py```
