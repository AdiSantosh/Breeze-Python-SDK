
"""
Data parsers for different message types from Breeze WebSocket.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, NamedTuple
import logging
import config
import model

logger = logging.getLogger(__name__)

class DataParser:
    """Parse different types of WebSocket messages."""
    
    def __init__(self, tux_to_user_value: Dict):
        """
        Initialize parser.
        
        Args:
            tux_to_user_value: Mapping for order status codes
        """
        self.tux_to_user_value = tux_to_user_value
        self.feed_interval_map = config.feed_interval_map


    def parse_ohlc_data(self, data: Any):
        """Parse tick data from server to corresponding NamedTuples"""

        split_data = data.split(",")
        data_len = len(split_data)
        exchange = split_data[0]

        if data_len < 9:
            logger.warning(f"Insufficient OHLC fields from server: expected >= 9, got {data_len}, data preview: {data[:100]}")
            return None

        if exchange in model.EQUITY_EXCHANGES:
            parsed_data = model.EquityTick(
                interval=self.feed_interval_map[split_data[8]],
                exchange_code=split_data[0],
                stock_code=split_data[1],
                low=split_data[2],
                high=split_data[3],
                open=split_data[4],
                close=split_data[5],
                volume=split_data[6],
                datetime=split_data[7]
            )

        elif data_len==13 and exchange in model.DERIVATIVES_EXCHANGES:
            parsed_data = model.OptionTick(
                    interval=self.feed_interval_map[split_data[12]],
                    exchange_code=split_data[0],
                    stock_code=split_data[1],
                    expiry_date=split_data[2],
                    strike_price=split_data[3],
                    right_type=split_data[4],
                    low=split_data[5],
                    high=split_data[6],
                    open=split_data[7],
                    close=split_data[8],
                    volume=split_data[9],
                    oi=split_data[10],
                    datetime=split_data[11]
            )

        else:
            parsed_data = model.FutureTick(
                    interval=self.feed_interval_map[split_data[10]],
                    exchange_code=split_data[0],
                    stock_code=split_data[1],
                    expiry_date=split_data[2],
                    low=split_data[3],
                    high=split_data[4],
                    open=split_data[5],
                    close=split_data[6],
                    volume=split_data[7],
                    oi=split_data[8],
                    datetime=split_data[9]
            )
        return parsed_data
    

    def parse_market_depth(self, data: Any, exchange: str):
        """Parse market depth with indexes of list as level of order book"""

        if not data:
            return []
        
        try:
            if exchange == "1":
                return [
                    model.DepthLevelEq(BestBuyRate=item[0],
                                BestBuyQty=item[1],
                                BestSellRate=item[2],
                                BestSellQty=item[3]) 
                                for item in data
                ]

            elif exchange == "8":
                return [
                    model.DepthLevelOpt(BestBuyRate=item[0],
                                BestBuyQty=item[1],
                                BuyNoOfOrders=item[2],
                                BestSellRate=item[3],
                                BestSellQty=item[4],
                                SellNoOfOrders=item[5])
                                for item in data
                ]
            
            elif exchange == "6":
                return [
                    model.DepthLevelCommodity(BuyQuantity=item[0],
                                    BuyOrderPrice=item[1],
                                    BuyTotalOrders=item[2],
                                    BuyReserved=item[3],
                                    SellQuantity=item[4],
                                    SellOrderPrice=item[5],
                                    SellTotalOrders=item[6],
                                    SellReserved=item[7])
                                    for item in data
                ]
            
            else:
                return [
                    model.DepthLevelExt(BestBuyRate=item[0],
                                BestBuyQty=item[1],
                                BuyNoOfOrders=item[2],
                                BuyFlag=item[3],
                                BestSellRate=item[4],
                                BestSellQty=item[5],
                                SellNoOfOrders=item[6],
                                SellFlag=item[7])
                                for item in data
                ]
                
        except (IndexError, TypeError) as e:
            logger.error(f"Market depth parsing error for exchange {exchange}: {e}")
            return []
        

    def parse_data(self, data):
        # Validation
        if not data or not isinstance(data, list) or len(data) == 0:
            logger.warning(f"Invalid input for parse_data: type={type(data).__name__}, length={len(data) if isinstance(data, list) else 0}, preview={str(data)[:100]}")
            return None
        
        first_element = data[0]
        # If "!" is NOT in the first element, it is an Order/Strategy/iClick notification
        if isinstance(first_element, str) and "!" not in first_element:
            return self._parse_notification(data)
        
        # Otherwise, it is a Market Feed (Quotes/Depth)
        return self._parse_market_feed(data)
    

    def _parse_notification(self, data):
        data_len = len(data)

        # iClick Recommendation Data
        if data_len == model.MessageType.ICLICK_RECOMMENDATION.value:
            return {
                'stock_name': data[0],
                'stock_code': data[1],
                'action_type': data[2],
                'expiry_date': data[3],
                'strike_price': data[4],
                'option_type': data[5],
                'stock_description': data[6],
                'recommended_price_and_date': data[7],
                'recommended_price_from': data[8],
                'recommended_price_to': data[9],
                'recommended_date': data[10],
                'target_price': data[11],
                'sltp_price': data[12],
                'part_profit_percentage': data[13],
                'profit_price': data[14],
                'exit_price': data[15],
                'recommended_update': data[16],
                'iclick_status': data[17],
                'subscription_type': data[18]
            }

        # Strategy Data
        elif data_len == model.MessageType.STRATEGY_UPDATE.value:
            return {
                'strategy_date': data[0],
                'modification_date': data[1],
                'portfolio_id': data[2],
                'call_action': data[3],
                'portfolio_name': data[4],
                'exchange_code': data[5],
                'product_type': data[6],
                'underlying': data[8],
                'expiry_date': data[9],
                'option_type': data[11],
                'strike_price': data[12],
                'action': data[13],
                'recommended_price_from': data[14],
                'recommended_price_to': data[15],
                'minimum_lot_quantity': data[16],
                'last_traded_price': data[17],
                'best_bid_price': data[18],
                'best_offer_price': data[19],
                'last_traded_quantity': data[20],
                'target_price': data[21],
                'expected_profit_per_lot': data[22],
                'stop_loss_price': data[23],
                'expected_loss_per_lot': data[24],
                'total_margin': data[25],
                'leg_no': data[26],
                'status': data[27]
            }

        # Order Update (Default fallback if not 19 or 28)
        else:
            return self._parse_order_update(data)

    def _parse_order_update(self, data):
        order_dict = {
            "sourceNumber": data[0],
            "group": data[1],
            "userId": data[2],
            "key": data[3],
            "messageLength": data[4],
            "requestType": data[5],
            "messageSequence": data[6],
            "messageDate": data[7],
            "messageTime": data[8],
            "messageCategory": data[9],
            "messagePriority": data[10],
            "messageType": data[11],
            "orderMatchAccount": data[12],
            "orderExchangeCode": data[13]
        }

        msg_type = data[11]

        # Equity / F&O (Type 4 or 5)
        if msg_type in model.MessageType.ORDER_UPDATE_EQUITY.value.split('_'):
            order_dict.update({
                "stockCode": data[14],
                "orderFlow": self.tux_to_user_value['orderFlow'].get(str(data[15]).upper(), str(data[15])),
                "limitMarketFlag": self.tux_to_user_value['limitMarketFlag'].get(str(data[16]).upper(), str(data[16])),
                "orderType": self.tux_to_user_value['orderType'].get(str(data[17]).upper(), str(data[17])),
                "orderLimitRate": data[18],
                "productType": self.tux_to_user_value['productType'].get(str(data[19]).upper(), str(data[19])),
                "orderStatus": self.tux_to_user_value['orderStatus'].get(str(data[20]).upper(), str(data[20])),
                "orderDate": data[21],
                "orderTradeDate": data[22],
                "orderReference": data[23],
                "orderQuantity": data[24],
                "openQuantity": data[25],
                "orderExecutedQuantity": data[26],
                "cancelledQuantity": data[27],
                "expiredQuantity": data[28],
                "orderDisclosedQuantity": data[29],
                "orderStopLossTrigger": data[30],
                "orderSquareFlag": data[31],
                "orderAmountBlocked": data[32],
                "orderPipeId": data[33],
                "channel": data[34],
                "exchangeSegmentCode": data[35],
                "exchangeSegmentSettlement": data[36],
                "segmentDescription": data[37],
                "marginSquareOffMode": data[38],
                "orderValidDate": data[40],
                "orderMessageCharacter": data[41],
                "averageExecutedRate": data[42],
                "orderPriceImprovementFlag": data[43],
                "orderMBCFlag": data[44],
                "orderLimitOffset": data[45],
                "systemPartnerCode": data[46]
            })

        # Type 6 or 7
        elif msg_type in model.MessageType.ORDER_UPDATE_DERIVATIVE.value.split('_'):
            order_dict.update({
                "stockCode": data[14],
                "productType": self.tux_to_user_value['productType'].get(str(data[15]).upper(), str(data[15])),
                "optionType": self.tux_to_user_value['optionType'].get(str(data[16]).upper(), str(data[16])),
                "exerciseType": data[17],
                "strikePrice": data[18],
                "expiryDate": data[19],
                "orderValidDate": data[20],
                "orderFlow": self.tux_to_user_value['orderFlow'].get(str(data[21]).upper(), str(data[21])),
                "limitMarketFlag": self.tux_to_user_value['limitMarketFlag'].get(str(data[22]).upper(), str(data[22])),
                "orderType": self.tux_to_user_value['orderType'].get(str(data[23]).upper(), str(data[23])),
                "limitRate": data[24],
                "orderStatus": self.tux_to_user_value['orderStatus'].get(str(data[25]).upper(), str(data[25])),
                "orderReference": data[26],
                "orderTotalQuantity": data[27],
                "executedQuantity": data[28],
                "cancelledQuantity": data[29],
                "expiredQuantity": data[30],
                "stopLossTrigger": data[31],
                "specialFlag": data[32],
                "pipeId": data[33],
                "channel": data[34],
                "modificationOrCancelFlag": data[35],
                "tradeDate": data[36],
                "acknowledgeNumber": data[37],
                "stopLossOrderReference": data[37],
                "totalAmountBlocked": data[38],
                "averageExecutedRate": data[39],
                "cancelFlag": data[40],
                "squareOffMarket": data[41],
                "quickExitFlag": data[42],
                "stopValidTillDateFlag": data[43],
                "priceImprovementFlag": data[44],
                "conversionImprovementFlag": data[45],
                "trailUpdateCondition": data[45],
                "systemPartnerCode": data[46]
            })
        return order_dict
    
    def _parse_market_feed(self, data):
        try:
            stream_header = data[0].split('!')[0]
            if '.' in stream_header:
                exchange, data_type = stream_header.split('.')
        except (IndexError, ValueError) as e:
            logger.warning(f"Stock code not in correct format {data}, missing splitters (!,.)")
            return None 

        data_len = len(data)
        data_dict = {}

        try:
            # Index Data (NIFTY 50)
            if exchange == '3':
                data_dict = {
                    'stock_code': data[0],
                    'open': data[1],
                    'high': data[2],
                    'low': data[3],
                    'previous_close': data[4],
                    'last_trade_price': data[5],
                    'last_trade_quantity': data[6],
                    'last_traded_time': data[7],
                    'total_traded_volume': data[8],
                    'percentage_change': data[9],
                    'absolute_change': data[10],
                    'weighted_average': data[11],
                    'bid_price': data[12],
                    'bid_quantity': data[13],
                    'offer_price': data[14],
                    'offer_quantity': data[15],
                    'open_interest_value': data[16]
                }

            # Commodity Exchange (MCX)
            elif exchange == '6':
                ltt_formatted = self._safe_date(data[7])
                data_dict = {
                    "symbol": data[0],
                    "AndiOPVolume": data[1],
                    "Reserved": data[2],
                    "IndexFlag": data[3],
                    "ttq": data[4],
                    "last": data[5],
                    "ltq": data[6],
                    "ltt": ltt_formatted,
                    "AvgTradedPrice": data[8],
                    "TotalBuyQnt": data[9],
                    "TotalSellQnt": data[10],
                    "ReservedStr": data[11],
                    "ClosePrice": data[12],
                    "OpenPrice": data[13],
                    "HighPrice": data[14],
                    "LowPrice": data[15],
                    "ReservedShort": data[16],
                    "CurrOpenInterest": data[17],
                    "TotalTrades": data[18],
                    "HightestPriceEver": data[19],
                    "LowestPriceEver": data[20],
                    "TotalTradedValue": data[21],
                    "exchange": "Commodity"
                }
                if data_len > 22:
                    data_dict["depth"] = self.parse_market_depth(data[22:], exchange)
                    
            # Standard Quotes (OHLCV)
            elif data_type == '1':
                data_dict = {
                    "symbol": data[0],
                    "open": data[1],
                    "last": data[2],
                    "high": data[3],
                    "low": data[4],
                    "change": data[5],
                    "bPrice": data[6],
                    "bQty": data[7],
                    "sPrice": data[8],
                    "sQty": data[9],
                    "ltq": data[10],
                    "avgPrice": data[11],
                    "quotes": "Quotes Data"
                }

                # NSE Equity / BSE (Length 21)
                if data_len == 21:
                    data_dict.update({
                        "ttq": data[12],
                        "totalBuyQt": data[13],
                        "totalSellQ": data[14],
                        "ttv": data[15],
                        "trend": data[16],
                        "lowerCktLm": data[17],
                        "upperCktLm": data[18],
                        "ltt": self._safe_date(data[19]),
                        "close": data[20]
                    })
                
                # FONSE / CDNSE (Length 23)
                elif data_len == 23:
                    data_dict.update({
                        "OI": data[12],
                        "CHNGOI": data[13],
                        "ttq": data[14],
                        "totalBuyQt": data[15],
                        "totalSellQ": data[16],
                        "ttv": data[17],
                        "trend": data[18],
                        "lowerCktLm": data[19],
                        "upperCktLm": data[20],
                        "ltt": self._safe_date(data[21]),
                        "close": data[22]
                    })

            # Fallback (Pure Market Depth Updates)
            else:
                data_dict = {
                    "symbol": data[0],
                    "time": self._safe_date(data[1]),
                    "depth": self.parse_market_depth(data[2], exchange),
                    "quotes": "Market Depth"
                }
        except (IndexError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse market feed data: {e}, exchange={exchange}, data_type={data_type}")
            return None
        
        # Exchange Name
        if exchange == '4':
            if data_len == 21:
                data_dict['exchange'] = 'NSE Equity'
            elif data_len == 23:
                data_dict['exchange'] = 'NSE Futures & Options'
        elif exchange == '1':
            data_dict['exchange'] = 'BSE'
        elif exchange == '13':
            data_dict['exchange'] = 'NSE Currency'
        elif exchange == '6':
            data_dict['exchange'] = 'Commodity'
        return data_dict


    def _safe_date(self, ts):
        """Safely convert timestamp to formatted string."""
        try:
            return datetime.fromtimestamp(ts).strftime('%c')
        except (ValueError, TypeError, OSError):
            return ts