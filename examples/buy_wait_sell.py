from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from hyperliquid.info import Info
import example_utils
import time

from hyperliquid.utils.signing import OrderType

import logging

logger = logging.getLogger(__name__)


class buyandsell:
    def __init__(
        self, address: str, info: Info, exchange: Exchange, COIN="ETH", buyamount=0.05, waittime=2, isbuy=True
    ):
        self.address = address
        self.info = info
        self.exchange = exchange
        self.COIN = COIN
        self.buyamount = buyamount
        self.waittime = waittime
        self.isbuy = isbuy

    def order(self):
        order_result = self.exchange.market_open(self.COIN, self.isbuy, self.buyamount, None, 0.01)
        logger.info(f"buy : {order_result}")

        if order_result["status"] == "ok":
            for status in order_result["response"]["data"]["statuses"]:
                try:
                    filled = status["filled"]
                    logger.info(f'Order #{filled["oid"]} filled {filled["totalSz"]} @{filled["avgPx"]}')
                except KeyError:
                    logger.info(f'Error: {status["error"]}')

            logger.info(f"wait {self.waittime}s before closing")
            time.sleep(self.waittime)

        order_result = self.exchange.market_close(self.COIN)
        if order_result["status"] == "ok":
            for status in order_result["response"]["data"]["statuses"]:
                try:
                    filled = status["filled"]
                    logger.info(f'Order #{filled["oid"]} filled {filled["totalSz"]} @{filled["avgPx"]}')
                except KeyError:
                    logger.info(f'Error: {status["error"]}')
        logger.info(f"sell : {order_result}")


def main():
    logging.basicConfig(filename="myapp.log", level=logging.INFO)
    address, info, exchange = example_utils.setup(constants.MAINNET_API_URL, skip_ws=True)
    buysell = buyandsell(
        address=address, info=info, exchange=exchange, COIN="ETH", buyamount=0.05, waittime=2, isbuy=True
    )
    while True:
        buysell.order()


if __name__ == "__main__":
    main()
