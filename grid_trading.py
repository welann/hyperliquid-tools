from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from hyperliquid.info import Info
from loguru import logger

import eth_account
from eth_account.signers.local import LocalAccount
import time


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
        hasspot=False,
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
        eachgridamount: 每个网格购买的币数量
        hasspot: 如果为True,则会在当前价格上方放现货卖单,所以需要确保钱包中有现货
        """
        self.COIN = COIN
        self.gridnum = gridnum
        self.gridmax = gridmax
        self.gridmin = gridmin
        self.tp = tp
        self.eachgridamount = eachgridamount
        self.hasspot = hasspot

        self.eachprice = []
        # 格式{"index": i, "oid": 0,"activated":False}
        self.buy_orders = []  # 买单.
        self.sell_orders = []  # 卖单.

    def compute(self):
        self.exchange.set_referrer("WELANN")
        pricestep = (self.gridmax - self.gridmin) / self.gridnum
        # 不同币种的精度不一样，出现问题可能需要调整
        # 比如btc的价格是整数
        for i in range(self.gridnum):
            price = self.gridmin + i * pricestep
            self.eachprice.append(round(float(f"{price:.5g}"), 6))
        logger.info(f"each grid's price: {self.eachprice}")
        logger.info(f"each grid buy: {self.eachgridamount} {self.COIN}")

        # 初始化网格订单
        for i in range(self.gridnum):
            # 只在当前价格下方开单
            midprice = float(self.info.all_mids()[self.COIN][:-1])
            if self.eachprice[i] > midprice:
                logger.info("grid price is higher than price ")
                self.buy_orders.append({"index": i, "oid": 0, "activated": False})
                continue

            order_result = self.exchange.order(
                name=self.COIN,
                is_buy=True,
                sz=self.eachgridamount,
                limit_px=self.eachprice[i],
                order_type={"limit": {"tif": "Gtc"}},
                builder={"b": "0x3b20fdfd5b1185fae6d2eabd1c0f56c219b70c46", "f": 1},
            )
            logger.info(f"init the {i} th grid order: {order_result}")

            if order_result.get("status") == "ok":
                buy_oid = (
                    order_result["response"]["data"]["statuses"][0]["resting"]["oid"]
                    if order_result["response"]["data"]["statuses"][0].get("resting")
                    else order_result["response"]["data"]["statuses"][0]["filled"][
                        "oid"
                    ]
                )
                self.buy_orders.append({"index": i, "oid": buy_oid, "activated": True})

        logger.info(f"inital buy orders: {self.buy_orders}")

    def check_buy_order(self):
        logger.info(f"check buy order: {self.buy_orders}")
        for buy_order in self.buy_orders:
            if buy_order["activated"]:
                order_status = self.info.query_order_by_oid(
                    self.address, buy_order["oid"]
                )
                logger.info("Order status by oid:", order_status)
                logger.info(order_status.get("status"))
                status = order_status.get("status")
                if status != "unknownOid":
                    # 如果此订单已成交
                    if order_status["order"].get("status") == "filled":
                        logger.info(f"buy order: {buy_order} filled")

                        # 下个卖单
                        sell_price = self.eachprice[buy_order["index"]] + self.tp
                        sell_order_result = self.exchange.order(
                            name=self.COIN,
                            is_buy=False,
                            sz=self.eachgridamount,
                            limit_px=sell_price,
                            order_type={"limit": {"tif": "Gtc"}},
                            builder={
                                "b": "0x3b20fdfd5b1185fae6d2eabd1c0f56c219b70c46",
                                "f": 1,
                            },
                        )
                        # {'status': 'ok', 'response': {'type': 'order', 'data': {'statuses': [{'resting': {'oid': 7701703031}}]}}}
                        if sell_order_result.get("status") == "ok":
                            sell_oid = (
                                sell_order_result["response"]["data"]["statuses"][0][
                                    "resting"
                                ]["oid"]
                                if sell_order_result["response"]["data"]["statuses"][
                                    0
                                ].get("resting")
                                else sell_order_result["response"]["data"]["statuses"][
                                    0
                                ]["filled"]["oid"]
                            )
                            # 保存卖单
                            self.sell_orders.append(
                                {
                                    "index": buy_order["index"],
                                    "oid": sell_oid,
                                    "activated": True,
                                }
                            )
                            # 删除这个订单
                            self.buy_orders.remove(buy_order)

    def check_sell_order(self):
        logger.info(f"check sell order: {self.sell_orders}")
        for sell_order in self.sell_orders:
            order_status = self.info.query_order_by_oid(self.address, sell_order["oid"])
            logger.info("Order status by oid:", order_status)
            logger.info(order_status.get("status"))
            status = order_status.get("status")
            if status != "unknownOid":
                # 如果此订单已成交
                if order_status["order"].get("status") == "filled":
                    logger.info(f"sell order: {sell_order} filled")
                    self.sell_orders.remove(sell_order)

    def check_grid(self):
        activated_orders = [False] * self.gridnum
        for buy_order in self.buy_orders:
            if buy_order["activated"]:
                activated_orders[buy_order["index"]] = True
        for sell_order in self.sell_orders:
            if sell_order["activated"]:
                activated_orders[sell_order["index"]] = True
        logger.info(f"all activated orders: {activated_orders}")

        midprice = float(self.info.all_mids()[self.COIN][:-1])
        for i in range(self.gridnum):
            # 只在当前价格下方开单
            if self.eachprice[i] < midprice:
                # 如果当前网格未激活的话
                if activated_orders[i] == False:
                    order_result = self.exchange.order(
                        name=self.COIN,
                        is_buy=True,
                        sz=self.eachgridamount,
                        limit_px=self.eachprice[i],
                        order_type={"limit": {"tif": "Gtc"}},
                        builder={
                            "b": "0x3b20fdfd5b1185fae6d2eabd1c0f56c219b70c46",
                            "f": 1,
                        },
                    )
                    logger.info(f"init the {i} th grid order: {order_result}")

                    if order_result.get("status") == "ok":
                        buy_oid = (
                            order_result["response"]["data"]["statuses"][0]["resting"][
                                "oid"
                            ]
                            if order_result["response"]["data"]["statuses"][0].get(
                                "resting"
                            )
                            else order_result["response"]["data"]["statuses"][0][
                                "filled"
                            ]["oid"]
                        )
                        self.buy_orders.append(
                            {"index": i, "oid": buy_oid, "activated": True}
                        )

    def hasspot_compute(self):
        self.exchange.set_referrer("WELANN")
        pricestep = (self.gridmax - self.gridmin) / self.gridnum
        # 不同币种的精度不一样，出现问题可能需要调整
        # 比如btc的价格是整数
        for i in range(self.gridnum):
            price = self.gridmin + i * pricestep
            self.eachprice.append(round(float(f"{price:.5g}"), 6))
        logger.info(f"each grid's price: {self.eachprice}")
        logger.info(f"each grid buy: {self.eachgridamount} {self.COIN}")

        # 初始化网格订单
        for i in range(self.gridnum):

            # 在当前价格上方开卖单
            midprice = float(self.info.all_mids()[self.COIN][:-1])
            if self.eachprice[i] > midprice:
                order_result = self.exchange.order(
                    name=self.COIN,
                    is_buy=False,
                    sz=self.eachgridamount,
                    limit_px=self.eachprice[i] + self.tp,
                    order_type={"limit": {"tif": "Gtc"}},
                    builder={"b": "0x3b20fdfd5b1185fae6d2eabd1c0f56c219b70c46", "f": 1},
                )
                logger.info(f"SELL: init the {i} th grid order : {order_result}")

                if order_result.get("status") == "ok":
                    buy_oid = (
                        order_result["response"]["data"]["statuses"][0]["resting"][
                            "oid"
                        ]
                        if order_result["response"]["data"]["statuses"][0].get(
                            "resting"
                        )
                        else order_result["response"]["data"]["statuses"][0]["filled"][
                            "oid"
                        ]
                    )
                    self.sell_orders.append({"index": i, "oid": buy_oid})
            else:
                # 在当前价格下方开买单
                order_result = self.exchange.order(
                    name=self.COIN,
                    is_buy=True,
                    sz=self.eachgridamount,
                    limit_px=self.eachprice[i],
                    order_type={"limit": {"tif": "Gtc"}},
                    builder={"b": "0x3b20fdfd5b1185fae6d2eabd1c0f56c219b70c46", "f": 1},
                )
                logger.info(f"BUY: init the {i} th grid order: {order_result}")

                if order_result.get("status") == "ok":
                    buy_oid = (
                        order_result["response"]["data"]["statuses"][0]["resting"][
                            "oid"
                        ]
                        if order_result["response"]["data"]["statuses"][0].get(
                            "resting"
                        )
                        else order_result["response"]["data"]["statuses"][0]["filled"][
                            "oid"
                        ]
                    )
                    self.buy_orders.append({"index": i, "oid": buy_oid})

        logger.info(f"inital buy orders: {self.buy_orders}")
        logger.info(f"inital sell orders: {self.sell_orders}")

    def hasspot_check_buy_order(self):
        logger.info(f"check buy order: {self.buy_orders}")
        for buy_order in self.buy_orders:
            order_status = self.info.query_order_by_oid(self.address, buy_order["oid"])
            logger.info("Order status by oid:", order_status)
            logger.info(order_status.get("status"))
            status = order_status.get("status")
            if status != "unknownOid":
                # 如果此订单已成交
                if order_status["order"].get("status") == "filled":
                    logger.info(f"buy order: {buy_order} filled")
                    # 下个卖单
                    sell_price = self.eachprice[buy_order["index"]] + self.tp
                    sell_order_result = self.exchange.order(
                        name=self.COIN,
                        is_buy=False,
                        sz=self.eachgridamount,
                        limit_px=sell_price,
                        order_type={"limit": {"tif": "Gtc"}},
                        builder={
                            "b": "0x3b20fdfd5b1185fae6d2eabd1c0f56c219b70c46",
                            "f": 1,
                        },
                    )
                    # {'status': 'ok', 'response': {'type': 'order', 'data': {'statuses': [{'resting': {'oid': 7701703031}}]}}}
                    if sell_order_result.get("status") == "ok":
                        sell_oid = (
                            sell_order_result["response"]["data"]["statuses"][0][
                                "resting"
                            ]["oid"]
                            if sell_order_result["response"]["data"]["statuses"][0].get(
                                "resting"
                            )
                            else sell_order_result["response"]["data"]["statuses"][0][
                                "filled"
                            ]["oid"]
                        )
                        # 保存卖单
                        self.sell_orders.append(
                            {"index": buy_order["index"], "oid": sell_oid}
                        )
                        # 删除这个订单
                        self.buy_orders.remove(buy_order)

    def hasspot_check_sell_order(self):
        logger.info(f"check sell order: {self.sell_orders}")
        for sell_order in self.sell_orders:
            order_status = self.info.query_order_by_oid(self.address, sell_order["oid"])
            logger.info("Order status by oid:", order_status)
            logger.info(order_status.get("status"))
            status = order_status.get("status")
            if status != "unknownOid":
                # 如果此订单已成交
                if order_status["order"].get("status") == "filled":
                    logger.info(f"sell order: {sell_order} filled")
                    # 下个买单
                    buy_order_result = self.exchange.order(
                        name=self.COIN,
                        is_buy=True,
                        sz=self.eachgridamount,
                        limit_px=self.eachprice[sell_order["index"]],
                        order_type={"limit": {"tif": "Gtc"}},
                        builder={
                            "b": "0x3b20fdfd5b1185fae6d2eabd1c0f56c219b70c46",
                            "f": 1,
                        },
                    )
                    if buy_order_result.get("status") == "ok":
                        buy_oid = (
                            buy_order_result["response"]["data"]["statuses"][0][
                                "resting"
                            ]["oid"]
                            if buy_order_result["response"]["data"]["statuses"][0].get(
                                "resting"
                            )
                            else buy_order_result["response"]["data"]["statuses"][0][
                                "filled"
                            ]["oid"]
                        )
                    self.buy_orders.append(
                        {"index": sell_order["index"], "oid": buy_oid}
                    )
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
    baseurl = constants.MAINNET_API_URL
    # your private key
    skey = "0xabcd"
    
    account: LocalAccount = eth_account.Account.from_key(skey)
    print(account.address)
    exchange = Exchange(account, baseurl)
    info = Info(base_url=baseurl, skip_ws=True)
    """
        COIN: 在哪个币上交易
        gridnum: 网格数量
        gridmax: 网格上界
        gridmin: 网格下界
        tp: 涨多少就卖掉
        eachgridamount: 每个网格购买的币数量(注意需要价值大于10$)
        hasspot: 如果为True,则会在当前价格上方放现货卖单,所以需要确保钱包中有现货(合约交易的话不用管)
    """

    # approve setting a builder fee
    approve_result = exchange.approve_builder_fee(
        "0x3b20fdfd5b1185fae6d2eabd1c0f56c219b70c46", "0.001%"
    )
    logger.info(approve_result)

    trading = grid(
        address=account.address,
        info=info,
        exchange=exchange,
        COIN="HYPE",
        gridnum=32,
        gridmax=20,
        gridmin=28,
        tp=0.25,
        eachgridamount=0.5,
        hasspot=False,
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
        try:
            trading.trader()
            time.sleep(1)
        except Exception as e:
            logger.error(f"error:{e}")
            time.sleep(1)


if __name__ == "__main__":
    main()
