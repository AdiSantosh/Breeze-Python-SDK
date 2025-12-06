from enum import Enum
from typing import NamedTuple

EQUITY_EXCHANGES = frozenset(["NSE","BSE"])
DERIVATIVES_EXCHANGES = frozenset(["BFO", "NFO", "NDX", "MCX"])

class MessageType(Enum):
    """Message type identifiers by length of message"""
    ICLICK_RECOMMENDATION = 19
    STRATEGY_UPDATE = 28
    ORDER_UPDATE_EQUITY = "4_5"
    ORDER_UPDATE_DERIVATIVE = "6_7"
    COMMODITY_QUOTE = "6"
    NIFTY_INDEX = "3"
    LIVE_QUOTE = "1"
    MARKET_DEPTH = "2"

class EquityTick(NamedTuple):
    """NamedTuple for equity ohlc tick data"""
    interval: str
    exchange_code: str
    stock_code: str
    low: str
    high: str
    open: str
    close: str
    volume: str
    datetime: str


class OptionTick(NamedTuple):
    """NamedTuple for Option ohlc tick data"""
    interval: str
    exchange_code: str
    stock_code: str
    expiry_date: str
    strike_price: str
    right_type: str
    low: str
    high: str
    open: str
    close: str
    volume: str
    oi: str 
    datetime: str


class FutureTick(NamedTuple):
    """NamedTuple for Futures ohlc tick data"""
    interval: str
    exchange_code: str
    stock_code: str
    expiry_date: str
    low: str
    high: str
    open: str
    close: str
    volume: str
    oi: str
    datetime: str

class DepthLevelEq(NamedTuple): ## For exchange = 1
    BestBuyRate: float
    BestBuyQty: int
    BestSellRate: float
    BestSellQty: int

class DepthLevelOpt(NamedTuple): ## For exchange = 8
    """For """
    BestBuyRate: float
    BestBuyQty: int
    BuyNoOfOrders: int
    BestSellRate: float
    BestSellQty: int
    SellNoOfOrders: int

class DepthLevelCommodity(NamedTuple): ## For exchnage = 6
    """For Commodity Exchange (MCX)"""
    BuyQuantity: int
    BuyOrderPrice: float
    BuyTotalOrders: int
    BuyReserved: str
    SellQuantity: int
    SellOrderPrice: float
    SellTotalOrders: int
    SellReserved: str

class DepthLevelExt(NamedTuple): ## Other
    BestBuyRate: float
    BestBuyQty: int
    BuyNoOfOrders: int
    BuyFlag: str
    BestSellRate: float
    BestSellQty: int
    SellNoOfOrders: int
    SellFlag: str