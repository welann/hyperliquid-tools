from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from hyperliquid.info import Info
import example_utils
import time

from hyperliquid.utils.signing import OrderType

import logging
logger = logging.getLogger(__name__)

COIN = "ETH"


class grid:
    def __init__(
        self,
        address: str,
        info: Info,
        exchange: Exchange,
        gridnum=10,
        gridmax=0.18,
        gridmin=0.06,
        tp=0.01,
        money=100,
        eachgridamount=100,
        isbuy=True,
    ):
        self.address = address
        self.info = info
        self.exchange = exchange
        """
        gridnum: 网格数量
        gridmax: 网格上界
        gridmin: 网格下界
        tp: 涨多少就卖掉
        money: 在这个网格中的总投入u数量
        eachgridamount: 每个网格购买的币数量
        """
        self.gridnum = gridnum
        self.gridmax = gridmax
        self.gridmin = gridmin
        self.tp = tp
        self.money = money
        self.eachgridamount = eachgridamount
        self.isbuy = isbuy
        
    def compute(self):
        eachprice = []
        pricestep = (self.gridmax - self.gridmin) / self.gridnum
        # 这里需要保留小数点后五位才能符合交易条件
        # 不同币种不一样
        for i in range(self.gridnum):
            price = round(self.gridmin + i * pricestep, 5)
            eachprice.append(price)
        logger.info(f"each grid's price: {eachprice}")
        logger.info(f"each grid buy: {self.eachgridamount} {COIN}")


    def openorder(self):
        open_order_price = []
        open_orders = self.info.open_orders(self.address)
        # 当前所有开单的限制价格
        for open_order in open_orders:
            if open_order["coin"] == COIN:
                open_order_price.append(open_order["limitPx"])

        # 当前的价格
        midprice = float(self.info.all_mids()[COIN][:-1])
        # print(f"midprice : {midprice}")
        logger.info(f"midprice : {midprice}")
        # 计算网格间距
        eachprice = []
        pricestep = (self.gridmax - self.gridmin) / self.gridnum
        # 这里需要保留小数点后五位才能符合交易条件
        # 不同币种不一样
        for i in range(self.gridnum):
            price = round(self.gridmin + i * pricestep, 5)
            eachprice.append(price)

        # print(f"each grid's price: {eachprice}")
        # print(f"each grid buy: {self.eachgridamount} {COIN}")

        
        # 开始下单

        # 超出下界，不下单
        if midprice < self.gridmin:
            # print("less than min")
            logger.info(f"price is {midprice}, less than min")
            return

        for i in range(self.gridnum):
            # 只在当前价格下方开单，设置止盈位
            if str(eachprice[i]) in open_order_price:
                continue

            tp_order_type: OrderType = {
                "trigger": {
                    "triggerPx": eachprice[i] + self.tp,
                    "isMarket": True,
                    "tpsl": "tp",
                }
            }

            order_result = self.exchange.order(
                COIN, self.isbuy, 0.004, eachprice[i], {"limit": {"tif": "Gtc"}}
            )
            logger.info(f"order: {order_result}")
            tp_result = self.exchange.order(
                COIN,
                not self.isbuy,
                0.004,
                eachprice[i] + self.tp,
                tp_order_type,
                reduce_only=True,
            )
            logger.info(f"order tp: {tp_result}")

def main():
    logging.basicConfig(filename='myapp.log', level=logging.INFO)
    address, info, exchange = example_utils.setup(
        constants.TESTNET_API_URL, skip_ws=True
    )
    trading = grid(
        address=address,
        info=info,
        exchange=exchange,
        gridnum=30,
        gridmax=3100,
        gridmin=3070,
        tp=2,
        eachgridamount=0.04,
        money=50
    )
    trading.compute()
    trading.set_referrer("WELANN")
    while True:
        trading.openorder()
        time.sleep(1)

if __name__ == "__main__":
    main()
