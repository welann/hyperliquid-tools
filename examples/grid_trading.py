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
    # Default Max Slippage for Market Orders 1%
    DEFAULT_SLIPPAGE = 0.01
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
        isspot=False
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
        isspot: 是现货还是合约
        """
        self.gridnum = gridnum
        self.gridmax = gridmax
        self.gridmin = gridmin
        self.tp = tp
        self.money = money
        self.eachgridamount = eachgridamount
        self.isbuy = isbuy
        self.isspot=isspot

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
        logger.info(f"each grid buy: {self.eachgridamount} {COIN}")


    def openorder(self):
        open_order_price = []
        open_orders = self.info.open_orders(self.address)
        # 当前所有开单的限制价格
        for open_order in open_orders:
            if open_order["coin"] == COIN:
                open_order_price.append(open_order["limitPx"])
        logging.info(f"open_order_price: {open_order_price}")
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
            # 只在当前价格下方开单
            # 如果当前已经有对应价格的单子了则不开
            if str(eachprice[i]) in open_order_price or eachprice[i]> midprice or self.grids[i]==True:
                logger.info("no need ")
                continue

            order_result = self.exchange.order(
                COIN, self.isbuy, self.eachgridamount, eachprice[i], {"limit": {"tif": "Alo"}}
            )
            self.grids[i]=True
            logger.info(f"order: {order_result}")
            #把每个网格对应的订单号存起来
            status=order_result["response"]["data"]["statuses"][0]
            if "resting" in status:
                self.oids[i]=status["resting"]["oid"]
            if "filled" in status:
                self.oids[i]=status["filled"]["oid"]

        logging.info(f"oids : {self.oids}")
        for i in range(self.gridnum):
            order_status = self.info.query_order_by_oid(self.address, self.oids[i])
            logging.info(f"check tp : {order_status}")
            #检测订单状态
            if "order" in order_status:
                if "resting" in order_status["order"]["status"]:
                    logging.info("resting")
                    continue
                #如果购买订单已完成
                #则判断此时价格是否达到止盈点
                if "filled" in order_status["order"]["status"]:
                    self.grids[i]=True
                    logging.info("try end filled order")
                    midprice = float(self.info.all_mids()[COIN][:-1])
                    #达到止盈点则卖出
                    if eachprice[i]+self.tp<midprice and not self.isspot:
                        order_result = self.exchange.order(
                            COIN, not self.isbuy, self.eachgridamount, eachprice[i], {"limit": {"tif": "Gtc"}},reduce_only=True
                        )
                        self.grids[i]=False
                        logger.info(f"order: {order_result}")
                    elif eachprice[i]+self.tp<midprice and self.isspot:
                    
                        order_result=self.market_close(COIN,sz=self.eachgridamount)
                        self.grids[i]=False
                        logger.info(f"spot order: {order_result}")


COIN = "SOL"
def main():
    logging.basicConfig(filename='myapp.log', level=logging.INFO)
    address, info, exchange = example_utils.setup(
        constants.MAINNET_API_URL, skip_ws=True
    )
    trading = grid(
        address=address,
        info=info,
        exchange=exchange,
        gridnum=10,
        gridmax=150,
        gridmin=130,
        tp=3,
        eachgridamount=0.15,
        isbuy=True,
        isspot=False
    )
    trading.compute()
    while True:
        trading.openorder()
        time.sleep(1)

if __name__ == "__main__":
    main()
