from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from hyperliquid.info import Info
import time

import logging

import eth_account
from eth_account.signers.local import LocalAccount

logger = logging.getLogger(__name__)


class grid:
    def __init__(
        self,
        info: Info,
        exchange: Exchange,
        COIN="PURR",
        gridnum=10,
        gridmax=0.18,
        gridmin=0.06,
        investamount=100,
        mode=1,
    ):
        self.info = info
        self.exchange = exchange
        """
        COIN: 在哪个币上交易
        gridnum: 网格数量
        gridmax: 网格上界
        gridmin: 网格下界
        tp: 涨多少就卖掉
        investamount: 每个网格投入的资金
        mode: 1: 等差, 2: 等比
        """
        self.COIN = COIN
        self.gridnum = gridnum
        self.gridmax = gridmax
        self.gridmin = gridmin
        self.investamount = investamount
        self.mode=mode

        self.eachbuyprice = []
        self.eachsellprice = []
        # 格式{"index": i, "oid": 0,"activated":False}
        self.buy_orders = []  # 买单.
        self.sell_orders = []  # 卖单.

    def check_order(self,orders,currentprice)-> tuple[list]:
        closest_index=0
        for i in range(self.gridnum):
            if self.eachbuyprice[i]<=currentprice<=self.eachsellprice[i]:
                closest_index=i
                break
        for i in range(closest_index,-1,-1):
            if orders[i]["activated"]:
                break
            else:
                order_status = self.info.query_order_by_oid(self.address, orders[i]["oid"])
                logging.info("Order status by oid:", order_status)
                logging.info(order_status.get("status"))
                status = order_status.get("status")
                if status != "unknownOid":
                    # 如果此订单已成交
                    if order_status["order"].get("status") == "filled":
                        logging.info(f"buy order: {orders[i]} filled")

    def compute(self):
        self.exchange.set_referrer("WELANN")
        if self.mode==1:
            pricestep = (self.gridmax - self.gridmin) / self.gridnum
      
            for i in range(self.gridnum):
                price = self.gridmin + i * pricestep
                sellprice=price+pricestep

                self.eachbuyprice.append(round(float(f"{price:.5g}"), 6))
                self.eachsellprice.append(round(float(f"{sellprice:.5g}"), 6))
        
        elif self.mode==2:
            pricestep=(self.gridmax-self.gridmin)/(self.gridnum-1)

            for i in range(self.gridnum):
                price=self.gridmin+i*pricestep
                sellprice=self.gridmin+(i+1)*pricestep

                self.eachbuyprice.append(round(float(f"{price:.5g}"), 6)) 
                self.eachsellprice.append(round(float(f"{sellprice:.5g}"), 6))
        else:
            logger.error("mode error")
            return
        #todo
        #eachgridamount需要根据币的信息，把数量转化为价格
        #不过或许也不用
        self.eachgridamount = self.investamount / self.gridnum
        logger.info(f"each grid's price: {self.eachprice}")
        logger.info(f"each grid buy: {self.eachgridamount} {self.COIN}")

        # 初始化网格订单
        for i in range(self.gridnum):
            # 只在当前价格下方开单
            #todo
            #这里换成查询数据库
            #并把订单信息存入数据库
            midprice = float(self.info.all_mids()[self.COIN][:-1])
            if self.eachprice[i] > midprice:
                logger.info("grid price is higher than price ")
                self.buy_orders.append({"index": i, "oid": 0, "activated": False})
                continue

            order_result = self.exchange.order(
                self.COIN, True, self.eachgridamount, self.eachprice[i], {"limit": {"tif": "Gtc"}}
            )
            logger.info(f"init the {i} th grid order: {order_result}")

            if order_result.get("status") == "ok":
                buy_oid = (
                    order_result["response"]["data"]["statuses"][0]["resting"]["oid"]
                    if order_result["response"]["data"]["statuses"][0].get("resting")
                    else order_result["response"]["data"]["statuses"][0]["filled"]["oid"]
                )
                self.buy_orders.append({"index": i, "oid": buy_oid, "activated": True})

        logger.info(f"inital buy orders: {self.buy_orders}")

    def check_buy_order(self):
        logging.info(f"check buy order: {self.buy_orders}")
        for buy_order in self.buy_orders:
            if buy_order["activated"]:
                order_status = self.info.query_order_by_oid(self.address, buy_order["oid"])
                logging.info("Order status by oid:", order_status)
                logging.info(order_status.get("status"))
                status = order_status.get("status")
                if status != "unknownOid":
                    # 如果此订单已成交
                    if order_status["order"].get("status") == "filled":
                        logging.info(f"buy order: {buy_order} filled")

                        # 下个卖单
                        sell_price = self.eachprice[buy_order["index"]] + self.tp
                        sell_order_result = self.exchange.order(
                            self.COIN, False, self.eachgridamount, sell_price, {"limit": {"tif": "Gtc"}}
                        )
                        # {'status': 'ok', 'response': {'type': 'order', 'data': {'statuses': [{'resting': {'oid': 7701703031}}]}}}
                        if sell_order_result.get("status") == "ok":
                            sell_oid = (
                                sell_order_result["response"]["data"]["statuses"][0]["resting"]["oid"]
                                if sell_order_result["response"]["data"]["statuses"][0].get("resting")
                                else sell_order_result["response"]["data"]["statuses"][0]["filled"]["oid"]
                            )
                            # 保存卖单
                            self.sell_orders.append({"index": buy_order["index"], "oid": sell_oid, "activated": True})
                            # 删除这个订单
                            self.buy_orders.remove(buy_order)

    def check_sell_order(self):
        logging.info(f"check sell order: {self.sell_orders}")
        for sell_order in self.sell_orders:
            order_status = self.info.query_order_by_oid(self.address, sell_order["oid"])
            logging.info("Order status by oid:", order_status)
            logging.info(order_status.get("status"))
            status = order_status.get("status")
            if status != "unknownOid":
                # 如果此订单已成交
                if order_status["order"].get("status") == "filled":
                    logging.info(f"sell order: {sell_order} filled")
                    self.sell_orders.remove(sell_order)

    def check_grid(self):
        activated_orders = [False] * self.gridnum
        for buy_order in self.buy_orders:
            if buy_order["activated"]:
                activated_orders[buy_order["index"]] = True
        for sell_order in self.sell_orders:
            if sell_order["activated"]:
                activated_orders[sell_order["index"]] = True
        logging.info(f"all activated orders: {activated_orders}")

        midprice = float(self.info.all_mids()[self.COIN][:-1])
        for i in range(self.gridnum):
            # 只在当前价格下方开单
            if self.eachprice[i] < midprice:
                # 如果当前网格未激活的话
                if activated_orders[i] == False:
                    order_result = self.exchange.order(
                        self.COIN, True, self.eachgridamount, self.eachprice[i], {"limit": {"tif": "Gtc"}}
                    )
                    logger.info(f"init the {i} th grid order: {order_result}")

                    if order_result.get("status") == "ok":
                        buy_oid = (
                            order_result["response"]["data"]["statuses"][0]["resting"]["oid"]
                            if order_result["response"]["data"]["statuses"][0].get("resting")
                            else order_result["response"]["data"]["statuses"][0]["filled"]["oid"]
                        )
                        self.buy_orders.append({"index": i, "oid": buy_oid, "activated": True})


    def hasspot_compute(self):
        if self.mode==1:
            pricestep = (self.gridmax - self.gridmin) / self.gridnum
      
            for i in range(self.gridnum):
                price = self.gridmin + i * pricestep
                sellprice=price+pricestep

                self.eachbuyprice.append(round(float(f"{price:.5g}"), 6))
                self.eachsellprice.append(round(float(f"{sellprice:.5g}"), 6))
        
        elif self.mode==2:
            pricestep=(self.gridmax-self.gridmin)/(self.gridnum-1)

            for i in range(self.gridnum):
                price=self.gridmin+i*pricestep
                sellprice=self.gridmin+(i+1)*pricestep

                self.eachbuyprice.append(round(float(f"{price:.5g}"), 6)) 
                self.eachsellprice.append(round(float(f"{sellprice:.5g}"), 6))
        else:
            logger.error("mode error")
            return
        
        self.eachgridamount = self.investamount / self.gridnum
        logger.info(f"each grid's price: {self.eachprice}")
        logger.info(f"each grid buy: {self.eachgridamount} {self.COIN}")

        # 初始化网格订单
        for i in range(self.gridnum):

            # 在当前价格上方开卖单
            #todo
            #这里换成查询数据库
            #需要判断当前持有的币数量是否足够现在价格上方网格的
            #如果不够，需要以现价购买足够的币
            #并把订单信息存入数据库
            midprice = float(self.info.all_mids()[self.COIN][:-1])
            if self.eachprice[i] > midprice:
                order_result = self.exchange.order(
                    self.COIN, False, self.eachgridamount, self.eachprice[i] + self.tp, {"limit": {"tif": "Gtc"}}
                )
                logger.info(f"SELL: init the {i} th grid order : {order_result}")

                if order_result.get("status") == "ok":
                    buy_oid = (
                        order_result["response"]["data"]["statuses"][0]["resting"]["oid"]
                        if order_result["response"]["data"]["statuses"][0].get("resting")
                        else order_result["response"]["data"]["statuses"][0]["filled"]["oid"]
                    )
                    self.sell_orders.append({"index": i, "oid": buy_oid})
            else:
                # 在当前价格下方开买单
                order_result = self.exchange.order(
                    self.COIN, True, self.eachgridamount, self.eachprice[i], {"limit": {"tif": "Gtc"}}
                )
                logger.info(f"BUY: init the {i} th grid order: {order_result}")
    
                if order_result.get("status") == "ok":
                    buy_oid = (
                        order_result["response"]["data"]["statuses"][0]["resting"]["oid"]
                        if order_result["response"]["data"]["statuses"][0].get("resting")
                        else order_result["response"]["data"]["statuses"][0]["filled"]["oid"]
                    )
                    self.buy_orders.append({"index": i, "oid": buy_oid})

        logger.info(f"inital buy orders: {self.buy_orders}")
        logger.info(f"inital sell orders: {self.sell_orders}")

    def hasspot_check_buy_order(self):
        logging.info(f"check buy order: {self.buy_orders}")
        for buy_order in self.buy_orders:
            order_status = self.info.query_order_by_oid(self.address, buy_order["oid"])
            logging.info("Order status by oid:", order_status)
            logging.info(order_status.get("status"))
            status = order_status.get("status")
            if status != "unknownOid":
                # 如果此订单已成交
                if order_status["order"].get("status") == "filled":
                    logging.info(f"buy order: {buy_order} filled")
                    # 下个卖单
                    sell_price = self.eachprice[buy_order["index"]] + self.tp
                    sell_order_result = self.exchange.order(
                        self.COIN, False, self.eachgridamount, sell_price, {"limit": {"tif": "Gtc"}}
                    )
                    # {'status': 'ok', 'response': {'type': 'order', 'data': {'statuses': [{'resting': {'oid': 7701703031}}]}}}
                    if sell_order_result.get("status") == "ok":
                        sell_oid = (
                            sell_order_result["response"]["data"]["statuses"][0]["resting"]["oid"]
                            if sell_order_result["response"]["data"]["statuses"][0].get("resting")
                            else sell_order_result["response"]["data"]["statuses"][0]["filled"]["oid"]
                        )
                        # 保存卖单
                        self.sell_orders.append({"index": buy_order["index"], "oid": sell_oid})
                        # 删除这个订单
                        self.buy_orders.remove(buy_order)

    def hasspot_check_sell_order(self):
        logging.info(f"check sell order: {self.sell_orders}")
        for sell_order in self.sell_orders:
            order_status = self.info.query_order_by_oid(self.address, sell_order["oid"])
            logging.info("Order status by oid:", order_status)
            logging.info(order_status.get("status"))
            status = order_status.get("status")
            if status != "unknownOid":
                # 如果此订单已成交
                if order_status["order"].get("status") == "filled":
                    logging.info(f"sell order: {sell_order} filled")
                    # 下个买单
                    buy_order_result = self.exchange.order(
                        self.COIN,
                        True,
                        self.eachgridamount,
                        self.eachprice[sell_order["index"]],
                        {"limit": {"tif": "Gtc"}},
                    )
                    if buy_order_result.get("status") == "ok":
                        buy_oid = (
                            buy_order_result["response"]["data"]["statuses"][0]["resting"]["oid"]
                            if buy_order_result["response"]["data"]["statuses"][0].get("resting")
                            else buy_order_result["response"]["data"]["statuses"][0]["filled"]["oid"]
                        )
                    self.buy_orders.append({"index": sell_order["index"], "oid": buy_oid})
                    self.sell_orders.remove(sell_order)

    def check_compute(self):
        if self.hasspot:
            self.hasspot_compute()
        else:
            self.compute()

    def trader(self):
        if self.hasspot:
            self.hasspot_check_buy_order()
            self.hasspot_check_sell_order()

        else:
            self.check_buy_order()
            self.check_sell_order()
            self.check_grid()
       


def main():
    logging.basicConfig(filename="grid.log", level=logging.INFO)
    baseurl = constants.MAINNET_API_URL
    skey = ""
    account: LocalAccount = eth_account.Account.from_key(skey)
    exchange = Exchange(account, baseurl)
    

    """
        COIN: 在哪个币上交易
        gridnum: 网格数量
        gridmax: 网格上界
        gridmin: 网格下界
        tp: 涨多少就卖掉
        eachgridamount: 每个网格购买的币数量
        hasspot: 如果为True,则会在当前价格上方放现货卖单,所以需要确保钱包中有现货
    """
    trading = grid(
        exchange=exchange,
        COIN="PURR/USDC",
        gridnum=1,
        gridmax=0.16,
        gridmin=0.14,
        investamount=100,
    )
    # trading = grid(
    #     address=address,
    #     info=info,
    #     exchange=exchange,
    #     COIN="SOL",
    #     gridnum=1,
    #     gridmax=162,
    #     gridmin=153.8,
    #     tp=1,
    #     eachgridamount=0.07,
    # )
    trading.check_compute()
    while True:
        trading.trader()
        time.sleep(1)


if __name__ == "__main__":
    main()