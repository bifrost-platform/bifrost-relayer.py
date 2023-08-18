# ![Bifrost Network](media/bifrost_header.jpeg)

# Bifrost Relayer

The Bifrost Relayer is the core implementation that facilitates the Cross-Chain Communication Protocol (CCCP) for the
Bifrost Network. It processes cross-chain transactions and propagates data transfer (e.g. feeding price information)
from one blockchain to another. This project represents the Python implementation of the Bifrost relayer.

## Getting Started

Learn to use the Bifrost network with our [technical docs](https://docs.bifrostnetwork.com/bifrost-network).

### Bifrost Network Testnet (ChainID: 49088)

| Public Endpoints (rpc/ws)                        |
|--------------------------------------------------|
| https://public-01.testnet.bifrostnetwork.com/rpc |
| https://public-02.testnet.bifrostnetwork.com/rpc |
| wss://public-01.testnet.bifrostnetwork.com/wss   |
| wss://public-02.testnet.bifrostnetwork.com/wss   |

### Bifrost Network Mainnet (ChainID: 3068)

| Public Endpoints (rpc/ws)                        |
|--------------------------------------------------|
| https://public-01.mainnet.bifrostnetwork.com/rpc |
| https://public-02.mainnet.bifrostnetwork.com/rpc |
| wss://public-01.mainnet.bifrostnetwork.com/wss   |
| wss://public-02.mainnet.bifrostnetwork.com/wss   |

### Install Requirements

- Tested on Python v3.10.
- chainpy library (https://github.com/bifrost-platform/bifrost-python-lib)
- bridgeconst library (https://github.com/bifrost-platform/solidity-contract-configs)

### Configuration Setup

Next, the configuration JSON file contains certain parameters that the operator has to set. For instance, variables such as the relayer private key and each EVM provider's RPC endpoints depend on the operator, thus these values should be manuall input.

You should prepare RPC endpoints for the following blockchain networks. There are two options for this: 1) operating your own nodes for the blockchains, or 2) utilizing services that offer RPC endpoints, such as Infura or NodeReal. It’s crucial that each node must be archive-mode enabled.

- Bifrost (**Must be priorly self-operating and fully synced**)
- Ethereum
- Binance Smart Chain
- Polygon

You should also prepare an EVM account that will act as your relayer account. This account should have enough balance for transaction fees used in operations. The configuration JSON file of the Mainnet Relayer is provided in the [entity.relayer.json](configs/entity.relayer.json) file. And the configuration file containing 3 properties: [_entity, each_chain_config, oracle_]

##### Entity config

```json
{
        "entity": {
        "role": "slow-relayer",
        "account_name": "mainnet-relayer-launched-on-console",
        "slow_relayer_delay_sec": 1000,
        "supporting_chains": [
            "BFC_MAIN",
            "ETH_MAIN",
            "BNB_MAIN",
            "MATIC_MAIN"
        ]
    },
    // ...
}
```

##### Chain config

A config is required for each supported chain. The following is an example configuration for the Bifrost Network.

```json
{
    "BFC_MAIN": {
        "chain_name": "BFC_MAIN",
        "block_period_sec": 3,
        "bootstrap_latest_height": 141648,
        "block_aging_period": 2,
        "transaction_block_delay": 5,
        "receipt_max_try": 20,
        "max_log_num": 1000,
        "rpc_server_downtime_allow_sec": 180,
        "fee_config": {
            "type": 2,
            "max_gas_price": 2000000000000,
            "max_priority_price": 1000000000000
        },
        "abi_dir": "configs/",
        "contracts": [
            {
                "name": "authority",
                "address": "0x0000000000000000000000000000000000000400",
                "abi_file": "abi.authority.bifrost.json",
                "deploy_height": 0
            },
            // ...
        ],
        "events": [
            {
                "contract_name": "socket",
                "event_name": "Socket"
            },
            {
                "contract_name": "socket",
                "event_name": "RoundUp"
            }
        ]
    }
}
```

##### Oracle config

Use the oracle_config provided.

```json
{
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
            "collection_period_sec": 300
        }
    },
    // ...
}
```

### Private configuration

[entity.relayer.json](configs/entity.relayer.json)
and [entity.relayer.private.json](configs/entity.relayer.private.json)
are merged and injected into the relayer. This is useful to prevent sensitive personal information from being stored in
a public repository. The content of [entity.relayer.private.json](configs/entity.relayer.private.json) is prioritized
when combined.

```json
{
    "entity": {
        // OPTIONAL; If none, this MUST be provided by the CLI.
        "secret_hex": "<RELAYER_ACCOUNT_PRIVATE_KEY>"
    },
    "oracle_config": {
        "bitcoin_block_hash": {
            "url": "<BITCOIN_MAINNET_RPC_ENDPOINT>"
        },
        "asset_prices": {
            "urls": {
                "Coingecko": "https://api.coingecko.com/api/v3/",
                "Upbit": "https://api.upbit.com/v1/",
                "Chainlink": "<ETHEREUM_MAINNET_RPC_ENDPOINT>",
                "Binance": "https://api.binance.com/api/v3/",
                "GateIo": "https://api.gateio.ws/api/v4/"
            }
        }
    },
    "BFC_MAIN": {
        "url_with_access_key": "http://127.0.0.1:9933"
    },
    "ETH_MAIN": {
        "url_with_access_key": "<ETHEREUM_MAINNET_RPC_ENDPOINT>"
    },
    "BNB_MAIN": {
        "url_with_access_key": "<BINANCE_MAINNET_RPC_ENDPOINT>"
    },
    "MATIC_MAIN": {
        "url_with_access_key": "<POLYGON_MAINNET_RPC_ENDPOINT>"
    }
}

```

### Launch relayer
```sh
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
