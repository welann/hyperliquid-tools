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