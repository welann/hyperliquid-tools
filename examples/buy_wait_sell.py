from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from hyperliquid.info import Info
import example_utils
import time
import random

from hyperliquid.utils.signing import OrderType
from hyperliquid.utils.types import Any, List, Meta, SpotMeta, Optional, Tuple, Cloid

import logging

logger = logging.getLogger(__name__)


class buyandsell:
    # Default Max Slippage for Market Orders 1%
    DEFAULT_SLIPPAGE = 0.01

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

    def _slippage_price(
        self,
        coin: str,
        is_buy: bool,
        slippage: float,
        px: Optional[float] = None,
    ) -> float:

        if not px:
            # Get midprice
            px = float(self.info.all_mids()[coin])
        # Calculate Slippage
        px *= (1 + slippage) if is_buy else (1 - slippage)
        # We round px to 5 significant figures and 6 decimals
        return round(float(f"{px:.5g}"), 6)

    def market_close(
        self,
        coin: str,
        sz: Optional[float] = None,
        px: Optional[float] = None,
        slippage: float = DEFAULT_SLIPPAGE,
        cloid: Optional[Cloid] = None,
    ):
        address = self.address
        # if self.address:
        #     address = self.address
        # if self.vault_address:
        #     address = self.vault_address
        if self.COIN=="PURR/USDC":
            logger.info("sell purr")
            px = self._slippage_price(self.COIN, False, slippage)
            return self.exchange.order(self.COIN,False,self.buyamount,px,{"limit": {"tif": "Gtc"}})
    
        positions = self.info.user_state(address)["assetPositions"]
        for position in positions:
            item = position["position"]
            if coin != item["coin"]:
                continue
            szi = float(item["szi"])
            if not sz:
                sz = abs(szi)
            is_buy = True if szi < 0 else False
            
            # Get aggressive Market Price
            px = self._slippage_price(coin, is_buy, slippage, px)
            # Market Order is an aggressive Limit Order IoC
            return self.exchange.order(coin, is_buy, sz, px, order_type={"limit": {"tif": "Ioc"}} , reduce_only=True, cloid=cloid)
        

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
        order_result = self.market_close(self.COIN,sz=self.buyamount)
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
    exchange.set_referrer("WELANN")
    buysell = buyandsell(
        address=address, info=info, exchange=exchange, COIN="PURR/USDC", buyamount=1, waittime=5, waittime=5, isbuy=True
    )
    while True:
        buysell.order()
        time.sleep(random.randint(3, 13))


if __name__ == "__main__":
    main()
