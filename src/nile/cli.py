#!/usr/bin/env python
"""Nile CLI entry point."""
import logging

import asyncclick as click

from nile.core.account import get_or_create_account
from nile.core.call_or_invoke import call_or_invoke as call_or_invoke_command
from nile.core.clean import clean as clean_command
from nile.core.compile import compile as compile_command
from nile.core.declare import declare as declare_command
from nile.core.deploy import deploy as deploy_command
from nile.core.init import init as init_command
from nile.core.install import install as install_command
from nile.core.node import node as node_command
from nile.core.plugins import load_plugins
from nile.core.run import run as run_command
from nile.core.test import test as test_command
from nile.core.version import version as version_command
from nile.utils.debug import debug as debug_command

logging.basicConfig(level=logging.DEBUG, format="%(message)s")

NETWORKS = ("localhost", "goerli", "mainnet")


def network_option(f):
    """Configure NETWORK option for the cli."""
    return click.option(  # noqa: E731
        "--network",
        envvar="STARKNET_NETWORK",
        default="localhost",
        help=f"Select network, one of {NETWORKS}",
        callback=_validate_network,
    )(f)


def _validate_network(_ctx, _param, value):
    """Normalize network values."""
    # normalize goerli
    if "goerli" in value or "testnet" in value:
        return "goerli"
    # normalize localhost
    if "localhost" in value or "127.0.0.1" in value:
        return "localhost"
    # check if value is accepted
    if value in NETWORKS:
        return value
    # raise if value is invalid
    raise click.BadParameter(f"'{value}'. Use one of {NETWORKS}")


@click.group()
def cli():
    """Nile CLI group."""
    pass


@cli.command()
def init():
    """Nile CLI group."""
    init_command()


@cli.command()
def install():
    """Install Cairo."""
    install_command()


@cli.command()
@click.argument("path", nargs=1)
@network_option
async def run(path, network):
    """Run Nile scripts with NileRuntimeEnvironment."""
    await run_command(path, network)


@cli.command()
@click.argument("artifact", nargs=1)
@click.argument("arguments", nargs=-1)
@network_option
@click.option("--alias")
@click.option("--salt")
@click.option("--token")
async def deploy(artifact, arguments, network, alias, salt, token):
    """Deploy StarkNet smart contract."""
    return await deploy_command(artifact, arguments, network, alias, salt, token)


@cli.command()
@click.argument("artifact", nargs=1)
@network_option
@click.option("--alias")
@click.option("--signature", nargs=2)
@click.option("--token")
async def declare(artifact, network, alias, signature, token):
    """Declare StarkNet smart contract."""
    return await declare_command(artifact, network, alias, signature, token)


@cli.command()
@click.argument("signer", nargs=1)
@network_option
async def setup(signer, network):
    """Set up an Account contract."""
    await get_or_create_account(signer, network)


@cli.command()
@click.argument("signer", nargs=1)
@click.argument("contract_name", nargs=1)
@click.argument("method", nargs=1)
@click.argument("params", nargs=-1)
@click.option("--nonce", nargs=1)
@click.option("--max_fee", nargs=1)
@network_option
async def send(signer, contract_name, method, params, network, nonce, max_fee):
    """Invoke a contract's method through an Account. Same usage as nile invoke."""
    account = await get_or_create_account(signer, network)
    print(
        "Calling {} on {} with params: {}".format(
            method, contract_name, [x for x in params]
        )
    )
    address, tx_hash = await account.send(
        contract_name, method, params, nonce=nonce, max_fee=max_fee
    )
    logging.info("Invoke transaction was sent.")
    logging.info(f"Contract address: {address}")
    logging.info(f"Transaction hash: {tx_hash}")


@cli.command()
@click.argument("contract_name", nargs=1)
@click.argument("method", nargs=1)
@click.argument("params", nargs=-1)
@click.option("--max_fee", nargs=1)
@network_option
async def invoke(contract_name, method, params, network, max_fee=None):
    """Invoke functions of StarkNet smart contracts."""
    address, tx_hash = await call_or_invoke_command(
        contract_name, "invoke", method, params, network, max_fee=max_fee
    )
    logging.info("Invoke transaction was sent.")
    logging.info(f"Contract address: {address}")
    logging.info(f"Transaction hash: {tx_hash}")


@cli.command()
@click.argument("contract_name", nargs=1)
@click.argument("method", nargs=1)
@click.argument("params", nargs=-1)
@network_option
async def call(contract_name, method, params, network):
    """Call functions of StarkNet smart contracts."""
    result = await call_or_invoke_command(
        contract_name, "call", method, params, network
    )
    logging.info(result)


@cli.command()
@click.argument("contracts", nargs=-1)
def test(contracts):
    """
    Run cairo test contracts.

    $ nile test
      Compiles all test contracts in CONTRACTS_DIRECTORY

    $ nile test contracts/MyContract.test.cairo
      Runs tests in MyContract.test.cairo

    $ nile test contracts/foo.test.cairo contracts/bar.test.cairo
      Runs tests in foo.test.cairo and bar.test.cairo
    """
    test_command(contracts)


@cli.command()
@click.argument("contracts", nargs=-1)
@click.option("--directory")
@click.option("--account_contract", is_flag="True")
@click.option("--disable-hint-validation", is_flag=True)
def compile(contracts, directory, account_contract, disable_hint_validation):
    """
    Compile cairo contracts.

    $ compile.py
      Compiles all contracts in CONTRACTS_DIRECTORY

    $ compile.py contracts/MyContract.cairo
      Compiles MyContract.cairo

    $ compile.py contracts/foo.cairo contracts/bar.cairo
      Compiles foo.cairo and bar.cairo
    """
    compile_command(contracts, directory, account_contract, disable_hint_validation)


@cli.command()
def clean():
    """Remove default build directory."""
    clean_command()


@cli.command()
@click.option("--host", default="127.0.0.1")
@click.option("--port", default=5050)
@click.option("--lite_mode", is_flag=True)
def node(host, port, lite_mode):
    """Start StarkNet local network.

    $ nile node
      Start StarkNet local network at port 5050

    $ nile node --host HOST --port 5001
      Start StarkNet network on address HOST listening at port 5001

    $ nile node --lite_mode
      Start StarkNet network on lite-mode
    """
    node_command(host, port, lite_mode)


@cli.command()
@click.version_option()
def version():
    """Print out toolchain version."""
    version_command()


@cli.command()
@click.argument("tx_hash", nargs=1)
@network_option
@click.option("--contracts_file", nargs=1)
def debug(tx_hash, network, contracts_file):
    """Locate an error in a transaction using contracts."""
    debug_command(tx_hash, network, contracts_file)


cli = load_plugins(cli)


if __name__ == "__main__":
    cli(_anyio_backend="asyncio")
