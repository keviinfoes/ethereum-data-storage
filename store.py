import json
import store_ens

#User input
folder_location = input("location ENS storage file: ")

with open(folder_location) as f:
    link_data = json.load(f)

store_ens.ens_store(link_data)