from enum import Enum

class APIRequestType(Enum):

    POST = "POST"
    GET = "GET"
    PUT = "PUT"
    DELETE = "DELETE"

    def __str__(self):
        return str(self.value)

#API endpoints
class APIEndPoint(Enum):

    CUST_DETAILS = "customerdetails"
    DEMAT_HOLDING = "dematholdings"
    FUND = "funds"
    HIST_CHART = "historicalcharts"
    MARGIN = "margin"
    ORDER = "order"
    PORTFOLIO_HOLDING = "portfolioholdings"
    PORTFOLIO_POSITION = "portfoliopositions"
    QUOTE = "quotes"
    TRADE = "trades"
    OPT_CHAIN = "optionchain"
    SQUARE_OFF = "squareoff"
    LIMIT_CALCULATOR = "fnolmtpriceandqtycal"
    MARGIN_CALULATOR = "margincalculator"
    GTT_ORDER = "gttorder"
    
    def __str__(self):
        return str(self.value)

#TUX Mapping
TUX_TO_USER_MAP = {
            "orderFlow": {
                "B": "Buy",
                "S": "Sell",
                "N": "NA"
            },
            "limitMarketFlag": {
                "L": "Limit",
                "M": "Market",
                "S": "StopLoss"
            },
            "orderType": {
                "T": "Day",
                "I": "IoC",
                "V": "VTC"
            },
            "productType": {
                "F": "Futures",
                "O": "Options",
                "P": "FuturePlus",
                "U": "FuturePlus_sltp",
                "I": "OptionPlus",
                "C": "Cash",
                "Y": "eATM",
                "B": "BTST",
                "M": "Margin",
                "T": "MarginPlus"
            },
            "orderStatus": {
                "A": "All",
                "R": "Requested",
                "Q": "Queued",
                "O": "Ordered",
                "P": "Partially Executed",
                "E": "Executed",
                "J": "Rejected",
                "X": "Expired",
                "B": "Partially Executed And Expired",
                "D": "Partially Executed And Cancelled",
                "F": "Freezed",
                "C": "Cancelled"
            },
            "optionType": {
                "C": "Call",
                "P": "Put",
                "*": "Others"
            },
        }


#Response Message
class ExceptionMessage(Enum):

    #Authentication Error
    AUTHENICATION_EXCEPTION = "Could not authenticate credentials. Please check token and keys"
    #Subscribe Exception
    QUOTE_DEPTH_EXCEPTION = "Either getExchangeQuotes must be true or getMarketDepth must be true"
    EXCHANGE_CODE_EXCEPTION = "Exchange Code allowed are 'BSE', 'NSE', 'NDX', 'MCX', 'NFO', 'BFO'."
    STOCK_CODE_EXCEPTION = "Stock-Code cannot be empty."
    EXPIRY_DATE_EXCEPTION = "Expiry-Date cannot be empty for given Exchange-Code."
    PRODUCT_TYPE_EXCEPTION = "Product-Type should either be Futures or Options for given Exchange-Code."
    STRIKE_PRICE_EXCEPTION = "Strike Price cannot be empty for Product-Type 'Options'."
    RIGHT_EXCEPTION = "Rights should either be Put or Call for Product-Type 'Options'."
    STOCK_INVALID_EXCEPTION = "Stock-Code not found."
    WRONG_EXCHANGE_CODE_EXCEPTION = "Stock-Token cannot be found due to wrong exchange-code."
    STOCK_NOT_EXIST_EXCEPTION = "Stock-Data does not exist in exchange-code {0} for Stock-Token {1}."
    ISEC_NSE_STOCK_MAP_EXCEPTION = "Result Not Found"
    STREAM_OHLC_INTERVAL_ERROR = "Interval should be either '1second','1minute', '5minute', '30minute'"

    #CUSTOMER_DETAILS_API
    SESSIONKEY_INCORRECT = "Could not authenticate credentials. Please check session key."
    APPKEY_INCORRECT = "Could not authenticate credentials. Please check api key."
    SESSIONKEY_EXPIRED = "Session key is expired."
    CUSTOMERDETAILS_API_EXCEPTION = "Unable to retrieve customer details at the moment. Please try again later."

    #SOCKET EXCEPTION
    OHLC_SOCKET_CONNECTION_DISCONNECTED = "Failed to connect to OHLC stream"
    LIVESTREAM_SOCKET_CONNECTION_DISCONNECTED = "Failed to connect to live stream"
    ORDERNOTIFY_SOCKET_CONNECTION_DISCONNECTED = "Failed to connect to order stream"
    STREAMING_SOCKET_CONNECTION_DISCONNECTED = "Connection Disconnected"    

    #API Call Exception
    API_REQUEST_EXCEPTION = "Error while trying to make request {0} {1}"

    def __str__(self):
        return str(self.value)

# Type List
INTERVAL_TYPES = ["1minute", "5minute", "30minute", "1day"]
INTERVAL_TYPES_HIST_V2 = ["1second","1minute", "5minute", "30minute", "1day"]
INTERVAL_TYPES_STREAM_OHLC = ["1second","1minute", "5minute", "30minute"]
PRODUCT_TYPES = ["futures", "options", "futureplus", "optionplus", "cash", "eatm", "margin","mtf","btst"]
PRODUCT_TYPES_HIST = ["futures", "options", "futureplus", "optionplus"]
PRODUCT_TYPES_HIST_V2 = ["futures", "options","cash"]
RIGHT_TYPES = ["call", "put", "others"]
ACTION_TYPES = ["buy", "sell"]
ORDER_TYPES = ["limit", "market", "stoploss"]
VALIDITY_TYPES = ["day", "ioc", "vtc"]
TRANSACTION_TYPES = ["debit", "credit"]
EXCHANGE_CODES_HIST = ["nse", "nfo", "ndx", "mcx"]
EXCHANGE_CODES_HIST_V2 = ["nse","bse","nfo","ndx","mcx","bfo"]
FNO_EXCHANGE_TYPES = ["nfo","mcx","ndx","bfo"]
STRATEGY_SUBSCRIPTION = ["one_click_fno","i_click_2_gain"]
GTT_ORDER_TYPES = ["oco","cover_oco"]

#Isec NSE Stockcode mapping file
ISEC_NSE_CODE_MAP_FILE = {
    'nse':'NSEScripMaster.txt',
    'bse':'BSEScripMaster.txt',
    'cdnse':'CDNSEScripMaster.txt',
    'fonse':'FONSEScripMaster.txt'
}

feed_interval_map = {
    '1MIN':"1minute",
    '5MIN':"5minute",
    '30MIN':'30minute',
    '1SEC':'1second'
}

channel_interval_map = {
    '1minute':'1MIN',
    '5minute':'5MIN',
    '30minute':'30MIN',
    '1second':'1SEC'
}