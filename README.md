Before running the example scripts it's needed to:
    - Having py_algorand_sdk installed
    - Deploy the smart contract on testnet and add the testnet application id to "./staking_sdk/v1/app_ids.json"
    - Add MNEMONIC_MANAGER, MNEMONIC_DEPOSITOR and the ASA_ID to NEEDED.json, the manager must be the same as in the deployed contract
    - Tweak the POOL_DURATION, POOL_REWARDS, POOL_START, DEPOSIT_AMOUNT parameters as preferred