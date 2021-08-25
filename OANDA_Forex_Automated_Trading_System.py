# Importing Modules
import oandapyV20
import oandapyV20.endpoints.instruments as instruments
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.trades as trades
import pandas as pd
import json
import matplotlib.pyplot as plt
import time

def getAccountDetails(accountID = '<account number>'):
    """Gets OANDA Trading Account Details"""
    accountRequest = accounts.AccountDetails(accountID=account_ID)
    accountRequestResponse = client.request(accountRequest)
    return accountRequestResponse


def readableJson(data):
    """Converts the returned yahooFinancials into readable Json Data"""
    return json.dumps(data, indent=4)

def getAccountSummary(accountID = '101-004-20375000-001'):
    """Returns account summary"""
    accountRequest = accounts.AccountSummary(accountID=account_ID)
    accountRequestResponse = client.request(accountRequest)
    return (accountRequestResponse)



def stochastic(dataFrame , a , b , c):
    "function to calculate stochastic"
    dataFrame['k'] = ((dataFrame['c'] - dataFrame['l'].rolling(a).min())/(dataFrame['h'].rolling(a).max()- dataFrame['l'].rolling(a).min()))*100
    dataFrame['K'] = dataFrame['k'].rolling(b).mean()
    dataFrame['D'] = dataFrame['K'].rolling(c).mean()
    return dataFrame


def SMA(dataFrame , a , b):
    "function to calculate the Simple Moving Average"
    dataFrame['sma_fast'] = dataFrame['c'].rolling(a).mean()
    dataFrame['sma_slow'] = dataFrame['c'].rolling(b).mean()
    return dataFrame


def candles(instrument):
    """
    If you give this function a currency, it would return the data for that currency pair such as:
        * open
        * high
        * low
        * volume
        * close
    """
    # granularity can be in seconds S5 - S30, minutes M1 - M30, hours H1 - H12, days D, weeks W or months M
    params = {"count": 800, "granularity": "M5"}
    candles = instruments.InstrumentsCandles(instrument=instrument, params=params)
    client.request(candles)
    ohlc_dict = candles.response["candles"]
    ohlc = pd.DataFrame(ohlc_dict)
    ohlc_df = ohlc.mid.dropna().apply(pd.Series)
    ohlc_df["volume"] = ohlc["volume"]
    ohlc_df.index = ohlc["time"]
    ohlc_df = ohlc_df.apply(pd.to_numeric)
    return ohlc_df



def market_order(currencyPair,units,sl):
    """
    This is a function which would perform a market order of either buy / sell.
    units can be positive or negative, where:
     + units : Buy
     - units : Sell

    StopLoss allows you to select a range to cap your losses.
    """
    account_ID = '<Account number>'

    # This is the order template used, and by string formatting the appropriate values, it would perform market based operations of either buy or sell
    orderTemplate = {
            "order": {
            "price": "",
            "stopLossOnFill": {
            "trailingStopLossOnFill": "GTC",
            "distance": str(sl)
                              },
            "timeInForce": "FOK",
            "instrument": str(currencyPair),
            "units": str(units),
            "type": "MARKET",
            "positionFill": "DEFAULT"
                    }
            }
    r = orders.OrderCreate(accountID=account_ID, data=orderTemplate)
    client.request(r)



def ATR(dataFrame,n):
    "A financial indicator used to calculate the Average True Range of a stock"
    dataFrame['H-L']=abs(dataFrame['h']-dataFrame['l'])
    dataFrame['H-PC']=abs(dataFrame['h']-dataFrame['c'].shift(1))
    dataFrame['L-PC']=abs(dataFrame['l']-dataFrame['c'].shift(1))
    dataFrame['TR']=dataFrame[['H-L','H-PC','L-PC']].max(axis=1,skipna=False)
    dataFrame['ATR'] = dataFrame['TR'].rolling(n).mean()
    dataFrameFinal = dataFrame.drop(['H-L','H-PC','L-PC'],axis=1)
    return round(dataFrameFinal["ATR"][-1],2)


def tradeSignal(dataFrame , currency):
    """The logic of the program"""
    global upward_sma_dic , downward_sma_dic
    signal = ""
    # If the fast moving average is greater than the slow moving average, and the second last
    # slow moving average is larger than the second last fast moving average
    # Then a convergence has occured..
    if dataFrame['sma_fast'][-1] > dataFrame['sma_slow'][-1] and dataFrame['sma_fast'][-2] < dataFrame['sma_slow'][-2]:
        # An upward crossover has occured
        upward_sma_dic[currency] = True
        downward_sma_dic[currency] = False

    if dataFrame['sma_fast'][-1] < dataFrame['sma_slow'][-1] and dataFrame['sma_fast'][-2] > dataFrame['sma_slow'][-2]:
        upward_sma_dic[currency] = False
        downward_sma_dic[currency] = True

    # If the stochastic has crossed the minimum threshold of 25, then the projected prices are going to be bullish, therefore buy
    if upward_sma_dic[currency] == True and min(dataFrame['K'][-1], dataFrame['D'][-1]) > 25 and max(dataFrame['K'][-2], dataFrame['D'][-2]) < 25:
        signal = "Buy"
    # If the stochastic has crossed the minimum threshold of 25, then the projected prices are going to be baelish, therefore sell
    if downward_sma_dic[currency] == True and min(dataFrame['K'][-1], dataFrame['D'][-1]) < 75 and max(dataFrame['K'][-2], dataFrame['D'][-2]) > 75:
        signal = "Sell"



    return signal




def main():
    """This is the main method, where all things come together"""
    account_ID = '<Account number>'
    global pairs
    try:
        r = trades.OpenTrades(accountID=account_ID)
        open_trades = client.request(r)['trades']
        curr_ls = []
        for i in range(len(open_trades)):
            curr_ls.append(open_trades[i]['instrument'])

        pairs = [i for i in pairs if i not in curr_ls]
        for currency in pairs:
            print("analyzing ",currency)
            data = candles(currency)
            ohlc_df = stochastic(data,14,3,3)
            ohlc_df = SMA(ohlc_df,100,200)
            signal = tradeSignal(ohlc_df,currency)
            if signal == "Buy":
                market_order(currency, positionSize ,3*ATR(data,120))
                print("New long position initiated for ", currency)
            elif signal == "Sell":
                market_order(currency,-1 * positionSize ,3*ATR(data,120))
                print("New short position initiated for ", currency)
    except:
        print("error encountered....skipping this iteration")


# Setting up API connection
API_KEY = '<API Key'
client = oandapyV20.API(access_token=API_KEY, environment='practice')

# Initializing the currency pairs
pairs = ["EUR_USD" , "GBP_USD" , "USD_CHF" , "AUD_USD" , "USD_CAD"]

# The max capital to allocate, for any currency pair
positionSize = 2000

# Because we're using the divergence indicator, we will need two SMAs, one for upward
# trend and one for downward trend.
upward_sma_dic = {}
downward_sma_dic = {}

for i in pairs:
    upward_sma_dic[i] = False
    downward_sma_dic[i] = False



account_ID = '101-004-20375000-001'

# Continuous execution
starttime=time.time()
timeout = time.time() + 60*60*1  # 60 seconds times 60 meaning the script will run for 1 hr
while time.time() <= timeout:
    try:
        print("passthrough at ",time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
        main()
    except KeyboardInterrupt:
        print('\n\nKeyboard exception received. Exiting.')
        exit()



