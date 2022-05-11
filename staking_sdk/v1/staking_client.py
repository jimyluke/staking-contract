from typing import Dict, List
from base64 import b64encode, b64decode
from algosdk.v2client.algod import AlgodClient
from algosdk.v2client.indexer import IndexerClient
from algosdk.encoding import encode_address
from algosdk.future.transaction import wait_for_confirmation, assign_group_id
from algosdk.logic import get_application_address
from ..utils import get_app_id, int_to_bytes, is_opted_in_app, is_opted_in_asset, read_global_state, bytes_to_int, get_suggested_params, read_local_state, sign_group
from ..contract_strings import GlobalKey
from .typed_dict import UserStakedState
from .staking_pool import StakingPool
from .create_pool import create_pool
from .escrow_opt_in import escrow_opt_in
from .staking_app_close_out import staking_app_close_out
from .staking_app_opt_in import staking_app_opt_in

INFO_KEY = b64encode(GlobalKey.info.encode()).decode()

class StakingClient:
    def __init__(self, algod_client: AlgodClient, indexer_client: IndexerClient, chain: str, user_address: str = None) -> None:
        '''Instatiate a new StakingClient object, loading from the global state all the data needed'''

        self.algod_client = algod_client
        self.indexer_client = indexer_client
        self.chain = chain
        self.user_address = user_address

        self.app_id = get_app_id(self.chain)
        self.escrow = get_application_address(self.app_id)

        global_state = self.get_unformatted_global_state()
        self.manager = self.get_manager(global_state)
        self.pools_number = self.get_pools_number(global_state)
        global_state.pop(INFO_KEY)
        
        self.pools = [StakingPool(self.algod_client, self.indexer_client, key, value) for key, value in global_state.items()]
    
    def update_global_state(self) -> None:
        global_state = self.get_unformatted_global_state()
        self.manager = self.get_manager(global_state)
        self.pools_number = self.get_pools_number(global_state)
        global_state.pop(INFO_KEY)

        for pool in list(self.pools):
            if b64encode(int_to_bytes(pool.id)) not in global_state.keys():
                self.pools.remove(pool)

        for key, value in global_state.items():
            try:
                self.get_pool_from_id(bytes_to_int(b64decode(key))).update_pool_state(key, value)
            except Exception:
                self.pools.append(StakingPool(self.algod_client, self.indexer_client, key, value))

    def get_manager(self, unformatted_gloabal_state) -> str:
        '''Extract the manager address from an unformatted global state'''
        return encode_address(b64decode(unformatted_gloabal_state[INFO_KEY])[:32])
    
    def get_pools_number(self, unformatted_gloabal_state) -> int:
        '''Extract the pools number from an unformatted global state'''
        return bytes_to_int(b64decode(unformatted_gloabal_state[INFO_KEY])[-8:])

    def submit_create_pool(self, staking_rewards: int, start_time: int, time_delta: int, staking_asa_id: int, pk: str, sender: str = None) -> None:
        '''Sumbmits to the network a create_pool transaction group'''

        params = get_suggested_params(self.algod_client)

        if self.user_address != None and sender == None:
            sender = self.user_address

        txns = create_pool(sender, params, staking_rewards, start_time, time_delta, staking_asa_id, self.app_id)
        
        group = assign_group_id(txns)

        signed_group = sign_group(group, pk)

        self.submit_group(signed_group, True)

    def submit_delete_pool(self, pool_id: int, pk: str, sender: str = None) -> None:
        '''Sumbmits to the network a delete_pool transaction group'''

        if self.user_address != None:
            sender = self.user_address

        txn = self.get_pool_from_id(pool_id).prepare_delete_pool_group(sender, self.app_id)

        signed_txn = txn.sign(pk)

        self.submit_txn(signed_txn, True)

    def submit_deposit_in_pool(self, pool_id: int, amount: int, pk: str, sender: str = None) -> None:
        '''Sumbmits to the network a deposit transaction group'''

        if self.user_address != None and sender == None:
            sender = self.user_address

        group = self.get_pool_from_id(pool_id).prepare_deposit_group(sender, amount, self.app_id)

        signed_group = sign_group(group, pk)

        self.submit_group(signed_group, True)

    def submit_claim_from_pool(self, pool_id: int, pk: str, sender: str = None) -> None:
        '''Sumbmits to the network a claim transaction group
           Raises Exception if the pool has been deleted'''
        
        if self.user_address != None and sender == None:
            sender = self.user_address

        try:
            txn = self.get_pool_from_id(pool_id).prepare_claim_group(sender, self.app_id)
        except Exception:
            raise Exception("Pool deleted, try with withdraw call")

        signed_txn = txn.sign(pk)

        self.submit_txn(signed_txn, True)
    
    def submit_withdraw_from_pool(self, pool_id: int, pk: str, sender: str = None) -> None:
        '''Sumbmits to the network a withdraw transaction group\n
           Raises Exception if the sender has not staked in pool_id'''
        if self.user_address != None and sender == None:
            sender = self.user_address
        try:
            txn = self.get_pool_from_id(pool_id).prepare_withdraw_group(sender, self.app_id)
        except Exception:
            txn = None
            for state in self.get_formatted_local_state(sender):
                if state["POOL_ID"] == pool_id:
                    txn = StakingPool.prepare_withdraw_group_from_info(
                        self.algod_client, sender, self.app_id, state["POOL_ID"], state["STAKING_ASA_ID"])
            if txn == None:
                raise Exception("Sender seems not have been staked in the pool")

        signed_txn = txn.sign(pk)

        self.submit_txn(signed_txn, True)
    
    def submit_escrow_opt_in(self, staking_asa_id: int, pk: str, sender: str = None) -> None:
        '''Sumbmits to the network a escrow_opt_in transaction group\n
           Raises Exception if the escrow is alredy opted in'''
        
        if is_opted_in_asset(self.indexer_client, self.escrow, staking_asa_id):
            raise Exception("Escrow alredy opted in asset {}".format(staking_asa_id))
        
        params = get_suggested_params(self.algod_client)

        if self.user_address != None and sender == None:
            sender = self.user_address

        txns = escrow_opt_in(sender, params, staking_asa_id, self.app_id)

        group = assign_group_id(txns)

        signed_group = sign_group(group, pk)

        self.submit_group(signed_group, True)
    
    def submit_staking_app_opt_in(self, pk, sender: str = None) -> None:
        '''Sumbmits to the network an application opt in transaction to the staking appplication\n
           Raises Exception if the sender is alredy opted in'''
        
        if self.user_address != None and sender == None:
            sender = self.user_address
        if is_opted_in_app(self.indexer_client, sender, self.app_id):
            raise Exception(f"{sender} is alredy opted in {self.app_id}")

        params = get_suggested_params(self.algod_client)
        
        self.submit_txn(staking_app_opt_in(sender, params, self.app_id).sign(pk), True)
    
    def submit_staking_app_close_out(self, pk, sender: str = None) -> None:
        '''Sumbmits to the network an application close out transaction from the staking appplication\n
           Raises Exception if the sender is not opted in'''

        if self.user_address != None and sender == None:
            sender = self.user_address
        if not is_opted_in_app(self.indexer_client, sender, self.app_id):
            raise Exception(f"{sender} is not opted in {self.app_id}")

        params = get_suggested_params(self.algod_client)
        
        self.submit_txn(staking_app_close_out(sender, params, self.app_id).sign(pk), True)

    def get_unformatted_global_state(self) -> Dict[str, 'int | str']:
        return read_global_state(self.indexer_client, self.app_id)
    
    def get_unformatted_local_state(self, address: str) -> Dict[str, 'int | str']:
        return read_local_state(self.indexer_client, self.app_id, address)

    def get_formatted_local_state(self, address: str = None) ->List[UserStakedState]:
        if address == None and self.user_address != None:
            address = self.user_address

        unformatted = self.get_unformatted_local_state(address)
        formatted = []
        for value in unformatted.values():
            formatted.append(
                dict(POOL_ID = bytes_to_int(b64decode(value)[:8]),
                     user_staked = bytes_to_int(b64decode(value)[8:16]),
                     user_score = bytes_to_int(b64decode(value)[16:24]),
                     STAKING_ASA_ID = bytes_to_int(b64decode(value)[24:])))

        return formatted

    def get_pool_from_id(self, pool_id: int) -> StakingPool:
        '''Returns the StakingPool object for the specific pool_id\n
           The global state should be updated to get reliable results\n
           Raises Exception if the pool_id is not found'''
        
        for pool in self.pools:
            if pool.id == pool_id:
                return pool
        raise Exception("Pool {} not found".format(pool_id))

    def get_staking_asa_id_from_pool(self, pool_id: int) -> int:
        for pool in self.pools:
            if pool.id == pool_id:
                return pool.staked_asa_id
        raise Exception("Pool {} not found".format(pool_id))

    def get_latest_pool_created(self) -> StakingPool:
        '''Get the latest pool created id\n
           The global state should be updated to get reliable results\n
           Raises Exception if no latest pool is found'''
           
        latest = 0
        for pool in self.pools:
            if latest < pool.id:
                latest = pool.id

        if latest == 0:
            raise Exception("No latest pool found")

        return self.get_pool_from_id(latest)

    def submit_group(self, transaction_group, wait: bool = False) -> str:
        txid = self.algod_client.send_transactions(transaction_group)

        if wait:
            wait_for_confirmation(self.algod_client, txid)

        return txid
        
    def submit_txn(self, txn, wait: bool = False) -> str:
        txid = self.algod_client.send_transaction(txn)

        if wait:
            wait_for_confirmation(self.algod_client, txid)

        return txid
    
class MainnetStakingClient(StakingClient):
    def __init__(self, algod_client: AlgodClient = None, indexer_client: IndexerClient = None, user_address: str = None) -> None:

        if algod_client is None:
            algod_client = AlgodClient("", "https://node.algoexplorerapi.io", headers={"User-Agent": "algosdk"})
        if indexer_client is None:
            indexer_client = IndexerClient("", "https://algoindexer.algoexplorerapi.io", headers={"User-Agent": "algosdk"})

        super().__init__(algod_client, indexer_client, "mainnet", user_address)

class TestnetStakingClient(StakingClient):
    def __init__(self, algod_client: AlgodClient = None, indexer_client: IndexerClient = None, user_address: str = None) -> None:

        if algod_client is None:
            algod_client = AlgodClient("", "https://node.testnet.algoexplorerapi.io", headers={"User-Agent": "algosdk"})

        if indexer_client is None:
            indexer_client = IndexerClient("", "https://algoindexer.testnet.algoexplorerapi.io", headers={"User-Agent": "algosdk"})

        super().__init__(algod_client, indexer_client, "testnet", user_address)