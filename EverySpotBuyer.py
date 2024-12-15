from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from hyperliquid.info import Info

import eth_account
from eth_account.signers.local import LocalAccount
import time


class Buyer:
    def __init__(self, info: Info, exchange: Exchange, usdc_amount=11, max_mc=1000000):
        self.info = info
        self.exchange = exchange
        self.usdc_amount = usdc_amount
        self.max_mc = max_mc

    def buy(self, coin_name, sz, px):
        try:
            order_result = self.exchange.order(
                coin_name,
                True,
                sz,
                px,
                {"limit": {"tif": "Ioc"}},
            )
            if (
                order_result["status"] == "ok"
                and "response" in order_result
                and "data" in order_result["response"]
                and "statuses" in order_result["response"]["data"]
            ):
                for status in order_result["response"]["data"]["statuses"]:
                    if "filled" in status:
                        print(f"{coin_name} order filled: {status['filled']}")
                    else:
                        print(
                            f"{coin_name}  buy size: {sz} price: {px} \norder result: {order_result}"
                        )
            else:
                print(
                    f"{coin_name}  buy size: {sz} price: {px} \norder result: {order_result}"
                )
        except Exception as e:
            print(f"{coin_name}  buy size: {sz} price: {px} \norder error: {e}")

    def buy_less_10(self, coin_name, sz, px, sell_sz, sell_px):
        try:
            order_result = self.exchange.order(
                coin_name,
                True,
                sz,
                px,
                {"limit": {"tif": "Ioc"}},
            )
            if (
                order_result["status"] == "ok"
                and "response" in order_result
                and "data" in order_result["response"]
                and "statuses" in order_result["response"]["data"]
            ):
                for status in order_result["response"]["data"]["statuses"]:
                    if "filled" in status:
                        print(f"{coin_name} order filled: {status['filled']}")
                    else:
                        print(
                            f"{coin_name}  buy size: {sz} price: {px} \norder result: {order_result}"
                        )
            else:
                print(
                    f"{coin_name}  buy size: {sz} price: {px} \norder result: {order_result}"
                )

        except Exception as e:
            print(f"{coin_name}  buy size: {sz} price: {px} \norder error: {e}")
        print("sell")
        try:
            order_result = self.exchange.order(
                coin_name,
                False,
                sell_sz,
                sell_px,
                {"limit": {"tif": "Ioc"}},
            )
            if (
                order_result["status"] == "ok"
                and "response" in order_result
                and "data" in order_result["response"]
                and "statuses" in order_result["response"]["data"]
            ):
                for status in order_result["response"]["data"]["statuses"]:
                    if "filled" in status:
                        print(f"{coin_name} sell order filled: {status['filled']}")
                    else:
                        print(
                            f"{coin_name}  sell size: {sell_sz} price: {sell_px} \norder result: {order_result}"
                        )
            else:
                print(
                    f"{coin_name}  sell size: {sell_sz} price: {sell_px} \norder result: {order_result}"
                )

        except Exception as e:
            print(
                f"{coin_name}  sell size: {sell_sz} price: {sell_px} \norder error: {e}"
            )

    def calculate_market_caps(self, spot_meta_data):
        market_caps = {}
        for coin in spot_meta_data:
            # 检查midPx是否有效
            if coin["midPx"]:
                mc = float(coin["midPx"]) * float(coin["totalSupply"])
                market_caps[coin["coin"]] = mc
        return market_caps

    def get_all_coin_info(self):
        all_price = self.info.all_mids()
        spot_meta = self.info.spot_meta_and_asset_ctxs()

        # 这里自动排除了purr以及未开盘的币
        all_spot_coin = [
            key
            for key in all_price
            if (key.startswith("@") and (float(all_price[key]) != 1.0))
        ]

        mc = self.calculate_market_caps(spot_meta[-1])
        # print(mc)

        for i, spot in enumerate(all_spot_coin):
            if spot in mc and mc[spot] > self.max_mc:
                print(f"{spot} market cap is too high, skip")
                continue
            # 这里设置了最大滑点3%
            buyprice = float(all_price[spot]) * 1.03
            buyprice = round(float(f"{buyprice:.5g}"), 8)
            buy_sz = round(self.usdc_amount / buyprice, 0)
            print(f"{spot} : {buyprice} : {buy_sz}")

            if self.usdc_amount < 10:
                buy_sz = round((self.usdc_amount + 11) / buyprice, 0)
                sell_px = float(all_price[spot]) * 0.97
                sell_px = round(float(f"{sell_px:.5g}"), 8)
                sell_sz = round(11 / sell_px, 0)
                print(f"{spot} : {buyprice} : {buy_sz} : {sell_px} : {sell_sz}")
                self.buy_less_10(spot, buy_sz, buyprice, sell_sz, sell_px)
            else:
                self.buy(spot, buy_sz, buyprice)

            time.sleep(1)
            # 如果你不想全买，可以把下面两行接触注释，把数字改成你想要购买的数量
            # if i > 20:
            #     break


if __name__ == "__main__":
    # 设置参数
    secret_key = ""
    usdc_amount = 3
    max_mc = 1000000

    account: LocalAccount = eth_account.Account.from_key(secret_key)
    print(account.address)
    baseurl = constants.MAINNET_API_URL
    exchange = Exchange(account, baseurl)
    exchange.set_referrer("WELANN")
    info = Info(base_url=baseurl, skip_ws=True)

    buyer = Buyer(info, exchange, usdc_amount=usdc_amount, max_mc=max_mc)
    buyer.get_all_coin_info()
