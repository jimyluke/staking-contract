from os import path
from json import load
from typing import Dict, List
from algosdk.v2client.indexer import IndexerClient
from algosdk.v2client.algod import AlgodClient
from algosdk.future.transaction import Transaction

my_path = path.abspath(path.dirname(__file__))
INFO_PATH = path.join(my_path, "v1/app_ids.json")

def int_to_bytes(i: int, len: int = 8):
    return i.to_bytes(len, "big")

def bytes_to_int(bytes: str, byteorder: str = 'big') -> int:
    return int.from_bytes(bytes,byteorder)

def get_app_id(chain: str) -> int:
    with open(INFO_PATH, 'r') as file:
        return load(file)[chain]['APP_ID']

def is_opted_in_app(indexer: IndexerClient, address: str, app_id: int) -> bool:
    try:
        for app in indexer.account_info(address)['account']['apps-local-state']:
            if app['id'] == app_id:
                return True
    except KeyError:
        pass

    return False
    
def is_opted_in_asset(indexer: IndexerClient, address: str, asa_id: int) -> bool:
    try:
        for asset in indexer.account_info(address)['account']['assets']:
            if asset['asset-id'] == asa_id:
                return True
    except KeyError:
        pass
    
    return False

def get_suggested_params(algod: AlgodClient):
    params = algod.suggested_params()
    params.flat_fee = True
    params.fee = 1000
    return params

def sign_group(txns: List[Transaction], pk: str) -> list:
    signed = []
    for txn in txns:
        signed.append(txn.sign(pk))
    return signed

def format_state(state) -> Dict[str, 'int | str']:
    formatted = {}
    for item in state:
        key = item['key']
        value = item['value']

        formatted_key = key
        
        if value['type'] == 1:
            formatted[formatted_key] = value['bytes']
        else:
            formatted[formatted_key] = value['uint']
    return formatted

def read_global_state(indexer_client: IndexerClient, app_id: int):
    return format_state(indexer_client.applications(app_id)['application']['params']['global-state'])

def read_local_state(indexer_client: IndexerClient, app_id: int, address: str):
    results = indexer_client.account_info(address)['account']
    try:
        for local_state in results["apps-local-state"]:
            if local_state["id"] == app_id:
                if "key-value" not in local_state:
                    return {}
                return format_state(local_state["key-value"])
    except KeyError:
        pass
    return {}