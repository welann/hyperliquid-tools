# EverySpotBuyer

买入所有的现货（除了purr以及未上线的）

可以设置购买的数量（usdc），以及最大市值（mc），默认滑点5%

注意：虽然可以设置购买的usdc数量（最好设置为10.5及以上），如果小于10，会自动+11，然后卖出11个usdc同等数量的币
在这个过程中，因为各种原因导致最后保留的币可能不是你想要的那个数量（比如你想买3u，但是只剩下1.5u或者5u这样子）

You can set the amount to purchase (USDC) and the maximum market cap (MC), with a default slippage of 5%

Note: Although you can set the amount of USDC to purchase (preferably set to 10.5 or above), if it is less than 10, it will automatically add 11 and then sell the equivalent amount of coins for 11 USDC
During this process, due to various reasons, the final amount of coins retained may not be the one you wanted (for example, if you wanted to buy 3u, but only 1.5u or 5u is left)

## how to use it

+ `pip install hyperliquid-python-sdk`
+ 打开 `EverySpotBuyer.py`
+ 拉到代码最下面，把参数改为自己想要的（secret_key, usdc_amount, max_mc）
+ 最后在终端里运行 `python EverySpotBuyer.py`
+ 用完后记得删除，不要泄露你的私钥

+ `pip install hyperliquid-python-sdk`
+ Open `EverySpotBuyer.py`
+ Scroll to the bottom of the code and modify the parameters to your desired values (secret_key, usdc_amount, max_mc)
+ Finally, run `python EverySpotBuyer.py` in the terminal
+ Remember to delete it after use and do not expose your private key



# hyperliquid-grid-trading

in this repo, there's two examples for grid trading and buy-wait-sell(Market Making?) 

在这个代码库里，有两份代码： 网格交易 和 买入等待卖出刷量

## how to use it
for spot trading ,using `PURR/USDC` instead of `PURR`, and make sure that the balance in your wallet `USDC (Perps)` and `USDC (Spot)` is not **zero**

对于现货交易，必须加上 `/USDC`，并且需要确保你钱包中`USDC (Perps)` 和 `USDC (Spot)`里余额都不为零



### for grid trading

+ `pip install hyperliquid-python-sdk`
+ open `config.json`, use your own `secret_key`
+ open `grid_trading.py`
+ change `trading = grid(.....)`
+ and run `python grid_trading.py`

### 网格交易

+ `pip install hyperliquid-python-sdk`
+ 打开 `config.json`, 使用你自己的 `secret_key`，注意别搞错了，在测试中很多人都在这上面搞错
+ 打开 `grid_trading.py`
+ 修改这里： `trading = grid(.....)`，把参数改为自己想要的
+ 最后在终端里运行 `python grid_trading.py`

### for buy-wait-sell(Market Making?)
+ `pip install hyperliquid-python-sdk`
+ open `config.json`, use your own `secret_key`
+ open `buy_wait_sell.py`
+ change `buysell = buyandsell(...)` 
+ and run `python buy_wait_sell.py`

### 刷量
+ `pip install hyperliquid-python-sdk`
+ 打开 `config.json`, 使用你自己的 `secret_key`，注意别搞错了，在测试中很多人都在这上面搞错
+ 打开 `buy_wait_sell.py`
+ 修改这里： `buysell = buyandsell(...)` ，把参数改为自己想要的
+ 最后在终端里运行 `python buy_wait_sell.py`

## warning 

maybe some bugs, i will fix it if i can find it

可能有一些bug，如果我知道了的话会修复它
