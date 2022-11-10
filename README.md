# bifrost-relayer

## Requirement
 - python 3.8 ~ 3.10

## Configuration
 - blockchain configurations and web3 end-points of each blockchain
   - routing-chain: BIFROST network
   - external-chains: Goerli, BNB-test, Mumbai
   - every end-point MUST support achive-mode
 - end-points of oracle sources
   - Upbit, Coingecko, ChainLink (on Ethereum)
 - System contracts
   - socket, vault and authority contract addresses
   - supported erc20 contracts addresses
   - abi.json of each contracts
   -
 - Relayer account
   - a multichain-account (ethereum-style)

### Configuration json
The configuration of relayer is provided in the [entity.relayer.json](configs/entity.relayer.json) file.
And the configuration file containing 4 properties: [_entity, multichain_config, each_chain_config, oracle_]

```python
"entity": {
   # OPTIONAL
   "role": "relayer",
   "account_name": "default",

   # PRIVATE, OPTIONAL
   "secret_hex": "",  # secret key as a hex-string

   # REQUIRED
   "supporting_chains": ["BIFROST", "ETHEREUM", "BINANCE", "POLYGON"]  # capitalized chain names
}
```
```python
 "multichain_config": {
   # REQUIRED
   "chain_monitor_period_sec": 3  # How often the relayer collects events from every chains
 }
```
```python
"bifrost": {
   # PRIVATE, OPTIONAL
   "url_with_access_key": "",  # rpc node access key (url)

   # REQUIRED
   "chain_name": "BIFROST",
   "block_period_sec": 3,  # how often the blockchain generate a block
   "bootstrap_latest_height": 1147843,  # height to start bootstrap
   "block_aging_period": 3,  # how long a block is confirmed (in number of blocks).
   "transaction_commit_multiplier": 2,
   "receipt_max_try": 12,
   "max_log_num": 1000,  # eth_getLogs queries events by max_log_num.
   "rpc_server_downtime_allow_sec": 180,
   "tx_fee_type": {"type": 2, "max_gas_price": 1000000000000, "max_priority_price": 2500000000},

   # REQUIRED, FIXED
   "abi_base_path": "configs/",
   "contracts": [
      {"name": "vault", "address":  "<contract_address_hexstring>", "abi_file": "<abi_file_name>"},
      {"name": "socket", "address": "<contract_address_hexstring>", "abi_file": "<abi_file_name>"},
      {"name": "authority", "address": "<contract_address_hexstring>", "abi_file": "<abi_file_name>"},
      {"name": "oracle", "address":  "<contract_address_hexstring>", "abi_file":  "<abi_file_name>"},
      {"name": "DAI_ETHEREUM", "address": "<contract_address_hexstring>", "abi_file": "<abi_file_name>"}
   ],
   "events": [
      {"contract_name": "socket", "event_name": "Socket"},
      {"contract_name": "socket", "event_name": "RoundUp"}
   ]
}
```
```python
"oracle_config": {
    "asset_prices": {
       # REQUIRED
       "names": ["ETH", "BFC", "MATIC", "BNB", "USDC", "USDT", "BUSD"],
       "source_names": ["Coingecko", "Upbit", "Chainlink"],
       "collection_period_sec": 120,

       # PRIVATE, OPTIONAL
       # access information to each oracle sources
       "urls": {
          "Coingecko": "",
          "Upbit": "",
          "Chainlink": ""
        }
    }
}
```

### Private configuration
[entity.relayer.json](configs/entity.relayer.json) is merged with [entity.relayer.private.json](configs/entity.relayer.private.json)
to be provided to the relayer. This is useful to prevent sensitive personal information from being stored in a public repository.
The content of [entity.relayer.private.json](configs/entity.relayer.private.json) is prioritized when combined.
```jsons
{
    "entity": {
       # OPTIONAL
       "secret_hex": ""  # secret key as a hex-string
    },

    "oracle_config": {
      "asset_prices": {
        "urls": {
          "Coingecko": "<coingecko price api url>",
          "Upbit": "<upbit price api url>",
          "Chainlink": "<ethereum mainnet access url>",
        }
      }
    },

   "bifrost": {"url_with_access_key": "<chain access url>"},
   "ethereum": {"url_with_access_key": "<chain access url>"},
   "binance": {"url_with_access_key": "<chain access url>"},
   "polygon": {"url_with_access_key": "<chain access url>"}
}

```

## launch relayer
```shell
# git clone and update submodule
$ git clone git@github.com:bifrost-platform/bifrost-relayer.git
$ cd bifrost-relayer

# 1. change directory to project root, then generate virtual environment.
$ virtualenv venv --python=python3.8 # or 3.9 or 3.10
$ source venv/bin/activate
$ pip install -r requirements.txt

# 2. launch a relayer with private-key
$ python relayer-launcher.py launch -k <private_key_in_hex_with_0x> --no-heartbeat
```
