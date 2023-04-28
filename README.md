# The Relayer of the BIFROST

Implementation of a BIFROST's Relayer in Python to enables interoperability between blockchains. This repository
contains information about BIFROST's bridge contract. (configs of Testnet and Mainnet contract). The README contains
information on how to run the relayer or use it as a library.

## Requirement

- Tested on python 3.10.
- chainpy library (https://github.com/bifrost-platform/bifrost-python-lib)
- bridgeconst library (https://github.com/bifrost-platform/solidity-contract-configs)

## Configuration

- Web3 rpc endpoints for each blockchain
    - Currently, BIFROST Bridge supports BIFROST Network, Ethereum, BNB chain and Polygon
    - Every end-point MUST be archive-mode
- API for "Oracle Sources"
    - price oracle: Binance API, GateIo API, Upbit API, Coingecko API, Ethereum RPC endpoint (contract oracle by
      ChainLink)
    - block hash oracle: Bitcoin RPC endpoint
- Configuration of System contracts
    - The addresses and ABIs of Socket, Vault and BIFROST's Authority contract
    - The addresses and ABIs of the supported ERC20 contracts
    - This repo contains every information for contract related to the BIFROST's Bridge service
- Relayer Account
    - a multichain-account (ethereum-style)

### Configuration json

The configuration of the Mainnet Relayer is provided in the [entity.relayer.json](configs/entity.relayer.json) file.

And the configuration file containing 3 properties: [_entity, each_chain_config, oracle_]

##### Entity config

```python
"entity": {
    # REQUIRED; select in ["User", "Relayer", "Fast-relayer", "Slow-relayer"]
    "role": "Slow-Relayer",

    # OPTIONAL
    "account_name": "default",

    # REQUIRED for slow-relayer
    "slow_relayer_delay_sec": 1000,

    # REQUIRED
    "supporting_chains": ["BFC_MAIN", "ETH_MAIN", "BNB_MAIN", "MATIC_MAIN"]
}
```

##### Chain config

A config is required for each supported chain. The following is an example of BIFROST Network config.

```python
"BFC_MAIN": {
    # REQUIRED
    "chain_name": "BFC_MAIN",
    "block_period_sec": 3,  # block time in seconds

    # OPTIONAL
    "transaction_block_delay": 2,  # The blocks it takes for transaction to be included in the blockchain
    "block_aging_period": 2,  # block finalization in blocks
    "bootstrap_latest_height": 141648,  # block height to start bootstrap
    "receipt_max_try": 20,
    "max_log_num": 1000,  # block-range to read events at once
    "rpc_server_downtime_allow_sec": 180,
    "fee_config": {
        "type": 2,
        "max_gas_price": 1000000000000,  # Maximum gas price that the relayer can pay 
        "max_priority_price": 2500000000
    },

    # REQUIRED, Use the config provided.
    "abi_dir": "configs/",
    "contracts": [
        ...
    ],
    "events": [
        ...
    ]
}
```

##### Oracle config

Use the oracle_config provided.

```python
"oracle_config": {
    "bitcoin_block_hash": {
        "name": "BITCOIN_BLOCK_HASH",
        "collection_period_sec": 300
    },

    "asset_prices": {
        "names": [
            "BFC_ON_ETH_MAIN",
            "ETH_ON_ETH_MAIN",
            "BNB_ON_BNB_MAIN",
            "MATIC_ON_MATIC_MAIN",
            "USDC_ON_ETH_MAIN",
            "USDT_ON_ETH_MAIN",
            "BIFI_ON_ETH_MAIN"
        ],
        "collection_period_sec": 120
    }
}
```

### Private configuration

[entity.relayer.json](configs/entity.relayer.json)
and [entity.relayer.private.json](configs/entity.relayer.private.json)
are merged and injected into the relayer. This is useful to prevent sensitive personal information from being stored in
a public repository. The content of [entity.relayer.private.json](configs/entity.relayer.private.json) is prioritized
when combined.

```jsons
{
    "entity": {
       # OPTIONAL; If none, this MUST be entered as console.
       "secret_hex": ""  # secret key as a hex-string
    },

    "oracle_config": {
      "asset_prices": {
        "urls": {
          "Coingecko": "https://api.coingecko.com/api/v3/",
          "Upbit": "https://api.upbit.com/v1/",
          "Chainlink": "<Ethereum Mainnet Endpoint URL>",
          "Binance": "https://api.binance.com/api/v3/",
          "GateIo": "https://api.gateio.ws/api/v4/"
        }
      }
    },

   "BFC_MAIN": {"url_with_access_key": "http://127.0.0.1:9933",
   "ETH_MAIN": {"url_with_access_key": "<Endpoint URL>"},
   "BNB_MAIN": {"url_with_access_key": "<Endpoint URL>"},
   "MATIC_MAIN": {"url_with_access_key": "<Endpoint URL>"}
}
```

### Launch relayer
```shell
# git clone repository
$ git clone git@github.com:bifrost-platform/bifrost-relayer.git@0.7.10

# generate virtual environment at repository root 
$ cd bifrost-relayer
$ virtualenv venv --python=python3.10
$ source venv/bin/activate
$ pip install -r requirements.txt

# launch a relayer with private-key
$ python3 relayer-launcher.py -k <private_key_hex_with_0x_prefix> --slow-relayer

# Use the --prometheus option to connect with Grafana.
$ python3 relayer-launcher.py -k <private_key_hex_with_0x_prefix> --slow-relayer --prometheus

# Use the --log-file-name option to output logs to a file.
$ python3 relayer-launcher.py -k <private_key_hex_with_0x_prefix> --slow-relayer --log-file-name relayer.log

```
