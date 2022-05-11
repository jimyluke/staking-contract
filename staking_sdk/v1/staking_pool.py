from typing import List
from algosdk.v2client.algod import AlgodClient
from algosdk.v2client.indexer import IndexerClient
from algosdk.future.transaction import Transaction, assign_group_id
from base64 import b64decode
from ..utils import bytes_to_int, get_suggested_params
from .delete_pool import delete_pool
from .deposit import deposit
from .claim import claim
from .withdraw import withdraw

class StakingPool:
    def __init__(self, algod_client: AlgodClient, indexer_client: IndexerClient, key: str, value: str) -> None:
        self.algod_client = algod_client
        self.indexer_client = indexer_client

        self.update_pool_state(key, value)
    
    def update_pool_state(self, key: str, value: str) -> None:
        self.id = bytes_to_int(b64decode(key))
        self.total_rewards = bytes_to_int(b64decode(value)[:8])
        self.users_number = bytes_to_int(b64decode(value)[8:16])
        self.to_be_claimed = bytes_to_int(b64decode(value)[16:24])
        self.total_staked = bytes_to_int(b64decode(value)[24:32])
        self.total_score = bytes_to_int(b64decode(value)[32:40])
        self.start_time = bytes_to_int(b64decode(value)[40:48])
        self.time_delta = bytes_to_int(b64decode(value)[48:56])
        self.staked_asa_id = bytes_to_int(b64decode(value)[56:])

    def prepare_delete_pool_group(self, sender: str, staking_app_id: int) -> Transaction:
        params = get_suggested_params(self.algod_client)
        params.fee = 2000

        txn = delete_pool(sender, params, self.staked_asa_id, staking_app_id, self.id)

        return txn
    
    def prepare_deposit_group(self, sender: str, amount: int, staking_app_id: int) -> List[Transaction]:
        params = get_suggested_params(self.algod_client)

        txns = deposit(sender, params, amount, self.staked_asa_id, staking_app_id, self.id)
        
        group = assign_group_id(txns)

        return group

    def prepare_claim_group(self, sender: str, staking_app_id: int) -> Transaction:
        params = get_suggested_params(self.algod_client)
        params.fee = 2000

        txn = claim(sender, params, self.staked_asa_id, staking_app_id, self.id)

        return txn

    def prepare_withdraw_group(self, sender: str, staking_app_id: int) -> Transaction:
        params = get_suggested_params(self.algod_client)
        params.fee = 2000

        txn = withdraw(sender, params, self.staked_asa_id, staking_app_id, self.id)

        return txn

    def prepare_withdraw_group_from_info(algod_client: AlgodClient, sender: str, staking_app_id: int, pool_id: int, staking_asa_id: int) -> Transaction:
        params = get_suggested_params(algod_client)
        params.fee = 2000

        txn = withdraw(sender, params, staking_asa_id, staking_app_id, pool_id)
    
        return txn

    def json(self) -> dict:
        return {'POOL_ID': self.id,
                'TOTAL_REWARDS': self.total_rewards,
                'USERS_NUMBER': self.users_number,
                'TO_BE_CLAIMED': self.to_be_claimed,
                'TOTAL_STAKED': self.total_staked,
                'TOTAL_SCORE': self.total_score,
                'START_TIME': self.start_time,
                'TIME_DELTA': self.time_delta,
                'STAKED_ASA_ID': self.staked_asa_id}

    def __repr__(self) -> str:
        return str(self.json())

    def __str__(self) -> str:
        return str(self.json())