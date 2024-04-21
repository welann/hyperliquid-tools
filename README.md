# hyperliquid-grid-trading

in this repo, there's two examples for grid trading and buy-wait-sell(Market Making?) operation

## how to use it
for spot trading ,using `PURR/USDC` instead of `PURR`

### for grid trading

+ `pip install hyperliquid-python-sdk`
+ open `examples/config.json`, use your own `secret_key`
+ open `examples/grid_trading.py`
+ change ` trading = grid(.....)` in line 125 and `COIN` in line 118
+ and run `python examples/grid_trading.py`

### for buy-wait-sell(Market Making?)
+ `pip install hyperliquid-python-sdk`
+ open `examples/config.json`, use your own `secret_key`
+ open `examples/buy_wait_sell.py`
+ change `buysell = buyandsell(...)` in line 55
+ and run `python examples/buy_wait_sell.py`

## warning 

maybe some bugs, i will fix it if i can find it
