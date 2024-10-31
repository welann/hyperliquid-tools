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
        self.status=True

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
        if self.COIN == "PURR/USDC":
            logger.info("sell purr")
            px = self._slippage_price(self.COIN, False, slippage)
            return self.exchange.order(self.COIN, False, self.buyamount, px, {"limit": {"tif": "Gtc"}})

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
            return self.exchange.order(
                coin, is_buy, sz, px, order_type={"limit": {"tif": "Ioc"}}, reduce_only=True, cloid=cloid
            )

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
        order_result = self.market_close(self.COIN, sz=self.buyamount)
        if order_result["status"] == "ok":
            for status in order_result["response"]["data"]["statuses"]:
                try:
                    filled = status["filled"]
                    logger.info(f'Order #{filled["oid"]} filled {filled["totalSz"]} @{filled["avgPx"]}')
                except KeyError:
                    logger.info(f'Error: {status["error"]}')
        logger.info(f"sell : {order_result}")

    def check_oid(self,oid)->bool:   
        time.sleep(0.5)
        order_status = self.info.query_order_by_oid(self.address, oid)

        status = order_status.get("status")
        #检查订单状态
        if status != "unknownOid":
            if order_status["order"].get("status") == "filled":
                logging.info(f"order: {order_status} filled")
                self.status=not self.status
                return True

        #没完成的就取消
        # {'status': 'ok', 'response': {'type': 'cancel', 'data': {'statuses': ['success']}}}
        cancel_status=self.exchange.cancel(self.COIN, oid)
        status = cancel_status.get("status")
        if status == "ok":
            statuses=cancel_status["response"]["data"]["statuses"][0]
            if statuses=="success":
                logging.info(f"cancel buy order: {oid}")
                return False
            else:
                self.status=not self.status
                logging.info(f"order: {oid} filled")
                return True
        # time.sleep(1)
        


    def midbuyandsell(self):
        """
        以midprice买入/卖出，随后查询订单状态
        在n秒内未完成则取消订单，重新下订单
        若订单完成，更新midprice，开相反方向的订单
        在n秒内未完成则取消订单，重新下订单
        """
        midprice = self.info.all_mids()[self.COIN]
        midprice=round(float(f"{float(midprice):.5g}"), 6)
        order_result = self.exchange.order(self.COIN, self.status, self.buyamount, midprice, {"limit": {"tif": "Gtc"}})
        logging.info(f"order_result: {order_result}")

        if order_result.get("status") == "ok":
            # {'status': 'ok', 'response': {'type': 'order', 'data': {'statuses': [{'error': 'Insufficient spot balance asset=10000'}]}}}
            if order_result["response"]["data"]["statuses"][0].get("error"):
                logging.info(f"order: {order_result['response']['data']['statuses'][0]['error']}")
                self.status=not self.status
            else:

                oid = (
                    order_result["response"]["data"]["statuses"][0]["resting"]["oid"]
                    if order_result["response"]["data"]["statuses"][0].get("resting")
                    else order_result["response"]["data"]["statuses"][0]["filled"]["oid"]
                )
                order=self.check_oid(oid)

                if order==False:
                    return
            
            #下一轮开始相反方向的开单
            logging.info("=========")
            # logging.info(f"first order: {oid} filled")
            logging.info(f"next round : { self.status}")
            logging.info("=========")
            time.sleep(random.randint(3, 11))


                

def main():
    logging.basicConfig(filename="purr.log", level=logging.INFO)
    address, info, exchange = example_utils.setup(constants.MAINNET_API_URL, skip_ws=True)
    exchange.set_referrer("WELANN")
    """
    COIN: 在哪个币上交易
    buyamount: 买入多少
    waittime: 多久后卖出
    isbuy: 先买后卖还是先卖后买
    """
    buysell = buyandsell(
        address=address, info=info, exchange=exchange, COIN="PURR/USDC", buyamount=150, waittime=5, isbuy=True
    )
    while True:
        #旧版
        #以市价买入卖出
        # buysell.order()
        # time.sleep(random.randint(3, 13))
        
        #新版
        #以中间价格限价买入卖出
        #手续费上有优势，但是其他风险不确定
        buysell.midbuyandsell()

if __name__ == "__main__":
    main()
