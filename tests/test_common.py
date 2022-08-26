"""Tests for common library."""
from unittest.mock import patch, Mock

import pytest

from nile.common import BUILD_DIRECTORY, prepare_params, stringify, get_gateway_response, get_feeder_response
from starkware.starknet.services.api.gateway.transaction import InvokeFunction
from starkware.starkware_utils.error_handling import StarkErrorCode


CONTRACT = "contract"
OPERATION = "invoke"
NETWORK = "goerli"
ARGS = ["1", "2", "3"]
LIST1 = [1, 2, 3]
LIST2 = [1, 2, 3, [4, 5, 6]]
LIST3 = [1, 2, 3, [4, 5, 6, [7, 8, 9]]]


TX_RECEIVED = dict({"code": StarkErrorCode.TRANSACTION_RECEIVED.name, "result": "test"})
TX_FAILED = dict({"code": "test"})


class AsyncMock(Mock):
    def __call__(self, *args, **kwargs):
        sup = super()

        async def coro():
            return sup.__call__(*args, **kwargs)

        return coro()



@pytest.mark.asyncio
@pytest.mark.parametrize(
    "success, tx_response",
    [
        (False, TX_FAILED),
        (True, TX_RECEIVED),
    ],
)
async def test_get_gateway_response(success, tx_response):
    with patch("test_common.InvokeFunction") as mock_tx:
        with patch("nile.common.GatewayClient.add_transaction", new=AsyncMock()) as mock_client:
            mock_client.return_value = tx_response
            args = dict({"network": NETWORK, "tx": mock_tx, "token": None})

            if success:
                # success
                res = await get_gateway_response(**args)
                assert res == tx_response

            else:
                mock_client.return_value = tx_response

                with pytest.raises(BaseException) as err:
                    await get_gateway_response(**args)
                assert (
                    "Transaction failed because:\n{'code': 'test'}."
                    in str(err.value)
                )

            mock_client.assert_called_once_with(tx=mock_tx, token=None)


@pytest.mark.asyncio
async def test_get_feeder_response():
    with patch("test_common.InvokeFunction") as mock_tx:
        with patch("nile.common.FeederGatewayClient.call_contract", new=AsyncMock()) as mock_client:
            mock_client.return_value = TX_RECEIVED
            args = dict({"network": NETWORK, "tx": mock_tx})

            res = await get_feeder_response(**args)
            assert res == TX_RECEIVED['result']


@pytest.mark.parametrize(
    "args, expected",
    [
        ([], []),
        ([LIST1], [["1", "2", "3"]]),
        ([LIST2], [["1", "2", "3", ["4", "5", "6"]]]),
        ([LIST3], [["1", "2", "3", ["4", "5", "6", ["7", "8", "9"]]]]),
    ],
)
def test_stringify(args, expected):
    assert stringify(args) == expected


@pytest.mark.parametrize(
    "args, expected",
    [
        ([], []),
        ([LIST1], [["1", "2", "3"]]),
    ],
)
def test_prepare_params(args, expected):
    assert prepare_params(args) == expected
