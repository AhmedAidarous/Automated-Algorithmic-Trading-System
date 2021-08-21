import pandas
import websocket, json, pprint, numpy
from binance.client import Client
from binance.enums import *

# Uncomment this once apiKeys have been inputted
import apiKeys

# trading Constants
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
TRADE_SYMBOL = 'ETHUSD'
TRADE_QUANTITY = 0.05
SOCKET = "wss://stream.binance.com:9443/ws/ethusdt@kline_1m"

inPosition = False

closes = []

client = Client(apiKeys.API_KEY , apiKeys.API_SECRET, tld='us')



def order(action, quantity, symbol, orderType= ORDER_TYPE_MARKET):
    """Performs either buy or sell orders"""
    try:
        order = client.create_order(
            symbol=symbol,
            side= action,
            type = orderType,
            quantity = quantity)

        print(order)

    except Exception as e:
        print("an exception occured - {}".format(e))
        return False

    return True


def RSI(df, periods=14, ema=True):
    """
    Returns a pd.Series with the relative strength index.
    """
    close_delta = df['close'].diff()

    # Make two series: one for lower closes and one for higher closes
    up = close_delta.clip(lower=0)
    down = -1 * close_delta.clip(upper=0)

    if ema == True:
        # Use exponential moving average
        ma_up = up.ewm(com=periods - 1, adjust=True, min_periods=periods).mean()
        ma_down = down.ewm(com=periods - 1, adjust=True, min_periods=periods).mean()
    else:
        # Use simple moving average
        ma_up = up.rolling(window=periods, adjust=False).mean()
        ma_down = down.rolling(window=periods, adjust=False).mean()

    rsi = ma_up / ma_down
    rsi = 100 - (100 / (1 + rsi))
    return rsi

def on_open(ws):
    """This method runs once the connection has been opened"""
    print("Opened Connection")


def on_close(ws):
    print("Closed Connection")


def on_message(ws, message):
    """Method is run everytime we recieve the data from the stream, this contains the actual data """
    global closes, inPosition
    print("Streaming")
    #Allows you to parse through a JSON string
    json_message = json.loads(message)

    # x : has candlestick reached final price, this is to check if candlestick is at the end if so,
    # That is when we will capture only the closing prices of the candle
    candle = json_message['k']
    isCandleClosed = candle['x']
    close = candle['c']

    # If candle closed
    if isCandleClosed:
        print("Candle Closed At {}".format(close))
        closes.append(float(close))
        print("Closes")
        print(closes)

        # if 14 closes have passed
        if len(closes) > RSI_PERIOD:
            pd_closes = pandas.DataFrame(closes)
            pd_closes.columns = [["close"]]
            rsi = RSI(pd_closes)
            print("CLOSE")

            rsiFrame = RSI(pd_closes)
            lastRsi = (rsiFrame.tail(1)).iloc[0, 0]


            # Check if the lastRsi value threashold has been surpassed
            if lastRsi > RSI_OVERBOUGHT:

                if inPosition:
                    print("Sell!")
                    # Place Binance Order Code here..
                    orderStatus = order(SIDE_SELL, TRADE_QUANTITY, TRADE_SYMBOL)
                    if orderStatus:
                        inPosition = False



                else:
                    print("Crypto isn't bought, your safe!")


            if lastRsi < RSI_OVERSOLD:
                if inPosition:
                    print("It is oversold, can't do anything....")

                else:
                    print("Buy!")
                    # Place Binance Order Code here..
                    orderStatus = order(SIDE_BUY, TRADE_QUANTITY, TRADE_SYMBOL)
                    if orderStatus:
                        inPosition = True



# This is the base endpoint
ws = websocket.WebSocketApp(SOCKET, on_open= on_open, on_close= on_close, on_message= on_message)
ws.run_forever()
