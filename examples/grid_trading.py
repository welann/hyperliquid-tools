from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from hyperliquid.info import Info
import example_utils
import time

from hyperliquid.utils.signing import OrderType
from hyperliquid.utils.types import Any, List, Meta, SpotMeta, Optional, Tuple, Cloid
import logging

logger = logging.getLogger(__name__)


class grid:
    def __init__(
        self,
        address: str,
        info: Info,
        exchange: Exchange,
        COIN="PURR/USDC",
        gridnum=10,
        gridmax=0.18,
        gridmin=0.06,
        tp=0.01,
        eachgridamount=100,
    ):
        self.address = address
        self.info = info
        self.exchange = exchange
        """
        COIN: 在哪个币上交易
        gridnum: 网格数量
        gridmax: 网格上界
        gridmin: 网格下界
        tp: 涨多少就卖掉
        money: 在这个网格中的总投入u数量
        eachgridamount: 每个网格购买的币数量
        """
        self.COIN = COIN
        self.gridnum = gridnum
        self.gridmax = gridmax
        self.gridmin = gridmin
        self.tp = tp
        self.eachgridamount = eachgridamount

        # 格式{"price": xxxx,"oid": xxxx}
        self.buy_orders = []  # 买单.
        self.sell_orders = []  # 卖单.

    def compute(self):
        self.exchange.set_referrer("WELANN")
        eachprice = []
        pricestep = (self.gridmax - self.gridmin) / self.gridnum
        # 这里需要保留小数点后五位才能符合交易条件
        # 不同币种不一样
        for i in range(self.gridnum):
            price = round(self.gridmin + i * pricestep, 5)
            eachprice.append(price)
        logger.info(f"each grid's price: {eachprice}")
        logger.info(f"each grid buy: {self.eachgridamount} {self.COIN}")

        # 初始化网格订单
        for i in range(self.gridnum):
            # 只在当前价格下方开单
            # 如果当前已经有对应价格的单子了则不开
            midprice = float(self.info.all_mids()[self.COIN][:-1])
            if eachprice[i] > midprice:
                logger.info("price is higher than grid price ")
                self.buy_orders.append({"price": eachprice[i], "oid": 00000})
                continue
            order_result = self.exchange.order(
                self.COIN, True, self.eachgridamount, eachprice[i], {"limit": {"tif": "Gtc"}}
            )
            logger.info(f"init the {i} th grid order: {order_result}")

            if order_result.get("status") == "ok":
                buy_oid = (
                    order_result["response"]["data"]["statuses"][0]["resting"]["oid"]
                    if order_result["response"]["data"]["statuses"][0].get("resting")
                    else order_result["response"]["data"]["statuses"][0]["filled"]["oid"]
                )
                self.buy_orders.append({"price": eachprice[i], "oid": buy_oid})
        logger.info(f"inital buy orders: {self.buy_orders}")

    def trader(self):
        eachprice = []
        pricestep = (self.gridmax - self.gridmin) / self.gridnum
        # 这里需要保留小数点后五位才能符合交易条件
        # 不同币种不一样
        for i in range(self.gridnum):
            price = round(self.gridmin + i * pricestep, 5)
            eachprice.append(price)

        self.buy_orders.sort(key=lambda x: float(x["price"]), reverse=True)  # 最高价到最低价.
        self.sell_orders.sort(key=lambda x: float(x["price"]), reverse=True)  # 最高价到最低价.
        print(f"buy orders: {self.buy_orders}")
        print("------------------------------")
        print(f"sell orders: {self.sell_orders}")
        print("------------------------------")

        # 格式{"price": xxxx,"oid": xxxx}
        buy_delete_orders = []  # 需要删除买单
        sell_delete_orders = []  # 需要删除的卖单

        for buy_order in self.buy_orders:
            order_status = self.info.query_order_by_oid(self.address, buy_order["oid"])
            print("Order status by oid:", order_status)
            print(order_status.get("status"))
            status=order_status.get("status")
            # 如果oid有效
            if status != "unknownOid":
                # 如果此订单已成交
                if order_status["order"].get("status") == "filled":
                    logging.info(f"{buy_order} filled")
                    print(f"buy order: {buy_order} filled")

                    # 下个卖单
                    sell_price = buy_order["price"] + self.tp
                    sell_order_result = self.exchange.order(
                        self.COIN, False, self.eachgridamount, sell_price, {"limit": {"tif": "Gtc"}}
                    )
                    # {'status': 'ok', 'response': {'type': 'order', 'data': {'statuses': [{'resting': {'oid': 7701703031}}]}}}
                    if sell_order_result.get("status") == "ok":
                        #原本对应位置的卖单需要从队列里删除
                        buy_delete_orders.append(buy_order)
                        sell_oid = (
                            sell_order_result["response"]["data"]["statuses"][0]["resting"]["oid"]
                            if sell_order_result["response"]["data"]["statuses"][0].get("resting")
                            else sell_order_result["response"]["data"]["statuses"][0]["filled"]["oid"]
                        )
                        self.sell_orders.append({"price": sell_price, "oid": sell_oid})

                    # 再来个买单
                    new_buy_order = self.exchange.order(
                        self.COIN, True, self.eachgridamount, buy_order["price"], {"limit": {"tif": "Gtc"}}
                    )
                    if new_buy_order.get["status"] == "ok":
                        buy_oid = (
                            new_buy_order["response"]["data"]["statuses"][0]["resting"]["oid"]
                            if new_buy_order["response"]["data"]["statuses"][0].get("resting")
                            else new_buy_order["response"]["data"]["statuses"][0]["filled"]["oid"]
                        )
                        self.buy_orders.append({"price": buy_order["price"], "oid": buy_oid})
            #oid 无效，检测此时价格是否适合下单
            #适合的话就下单
            else:
                midprice = float(self.info.all_mids()[self.COIN][:-1])
                if buy_order["price"] < midprice:
                    buy_order_result = self.exchange.order(
                    self.COIN, True, self.eachgridamount, eachprice[i], {"limit": {"tif": "Gtc"}}
                    )
                    if buy_order_result.get["status"] == "ok":
                        buy_oid = (
                            buy_order_result["response"]["data"]["statuses"][0]["resting"]["oid"]
                            if buy_order_result["response"]["data"]["statuses"][0].get("resting")
                            else buy_order_result["response"]["data"]["statuses"][0]["filled"]["oid"]
                        )
                        self.buy_orders.remove({"price": buy_order["price"], "oid": 00000})
                        self.buy_orders.append({"price": buy_order["price"], "oid": buy_oid})
                        logger.info("new gird has been activated ")

        for delete_order in buy_delete_orders:
            self.buy_orders.remove(delete_order)

        # 检查卖单
        for sell_order in self.sell_orders:
            order_status = self.info.query_order_by_oid(self.address, sell_order["oid"])
            print("Order status by oid:", order_status)
            print(order_status.get("status"))

            if order_status != "unknownOid":
                if order_status["order"].get("status") == "filled":
                    logging.info(f"{sell_order} filled")
                    print(f"buy order: {sell_order} filled")
                    # 下个买单
                    buy_price = sell_order["price"] - self.tp
                    buy_order_result = self.exchange.order(
                        self.COIN, True, self.eachgridamount, buy_price, {"limit": {"tif": "Gtc"}}
                    )
                    if buy_order_result.get("status") == "ok":
                        sell_delete_orders.append(sell_order)
                        buy_oid = (
                            buy_order_result["response"]["data"]["statuses"][0]["resting"]["oid"]
                            if buy_order_result["response"]["data"]["statuses"][0].get("resting")
                            else buy_order_result["response"]["data"]["statuses"][0]["filled"]["oid"]
                        )
                        self.buy_orders.append({"price": buy_price, "oid": buy_oid})

                    # 再来个卖单
                    new_sell_order = self.exchange.order(
                        self.COIN, False, self.eachgridamount, sell_order["price"], {"limit": {"tif": "Gtc"}}
                    )
                    if new_sell_order.get["status"] == "ok":
                        sell_oid = (
                            sell_order_result["response"]["data"]["statuses"][0]["resting"]["oid"]
                            if sell_order_result["response"]["data"]["statuses"][0].get("resting")
                            else sell_order_result["response"]["data"]["statuses"][0]["filled"]["oid"]
                        )
                        self.sell_orders.append({"price": sell_price, "oid": sell_oid})

        for delete_order in sell_delete_orders:
            self.sell_orders.remove(delete_order)

        # # 没有买单
        # if len(self.buy_orders) <= 0:
        #     midprice = float(self.info.all_mids()[self.COIN][:-1])
        #     nearest_grid_price = 0.0
        #     min_difference = float("inf")
        #     for price in eachprice:
        #         difference = midprice - price
        #         if difference > 0 and difference < min_difference:
        #             min_difference = difference
        #             nearest_grid_price = price
        #     buy_order_result = self.exchange.order(
        #         self.COIN, True, self.eachgridamount, nearest_grid_price, {"limit": {"tif": "Gtc"}}
        #     )
        #     if buy_order_result.get("status") == "ok":
        #         buy_oid = (
        #             buy_order_result["response"]["data"]["statuses"][0]["resting"]["oid"]
        #             if buy_order_result["response"]["data"]["statuses"][0].get("resting")
        #             else buy_order_result["response"]["data"]["statuses"][0]["filled"]["oid"]
        #         )
        #         self.buy_orders.append({"price": nearest_grid_price, "oid": buy_oid})
        # # 没有卖单
        # if len(self.sell_orders) <= 0:
        #     midprice = float(self.info.all_mids()[self.COIN][:-1])
        #     nearest_grid_price = 0.0
        #     min_difference = float("inf")
        #     for price in eachprice:
        #         difference = midprice - price
        #         if difference > 0 and difference < min_difference:
        #             min_difference = difference
        #             nearest_grid_price = price
        #     sell_order_result = self.exchange.order(
        #         self.COIN, False, self.eachgridamount, nearest_grid_price, {"limit": {"tif": "Gtc"}}
        #     )
        #     if sell_order_result.get("status") == "ok":
        #         sell_oid = (
        #             sell_order_result["response"]["data"]["statuses"][0]["resting"]["oid"]
        #             if sell_order_result["response"]["data"]["statuses"][0].get("resting")
        #             else sell_order_result["response"]["data"]["statuses"][0]["filled"]["oid"]
        #         )
        #         self.sell_orders.append({"price": nearest_grid_price, "oid": sell_oid})
def main():
    # logging.basicConfig(filename="myapp.log", level=logging.INFO)
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)
    # trading = grid(
    #     address=address,
    #     info=info,
    #     exchange=exchange,
    #     COIN="PURR/USDC",
    #     gridnum=10,
    #     gridmax=105,
    #     gridmin=95,
    #     tp=0.5,
    #     eachgridamount=1,
    # )
    trading = grid(
        address=address,
        info=info,
        exchange=exchange,
        COIN="BTC",
        gridnum=20,
        gridmax=65800,
        gridmin=65600,
        tp=0.1,
        eachgridamount=0.001,
    )
    trading.compute()
    while True:
        trading.trader()
        time.sleep(1)


if __name__ == "__main__":
    main()
