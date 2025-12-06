import threading
from enum import Enum
from typing import Optional, Dict, Tuple
import logging
import os, sys
import pickle
import csv
import requests
from datetime import datetime, timedelta

from config import ExceptionMessage

logger = logging.getLogger(__name__)

except_message = ExceptionMessage

class Exchange(Enum):
    """Exchange codes enumeration."""
    BSE = "1."
    NSE = "4."
    NDX = "13."
    MCX = "6."
    NFO = "4."
    BFO = "2."


class StockMaster:
    """
    Thread-safe stock token management with caching.
    
    Handles conversion between stock codes and tokens for all exchanges.
    Downloads stock master CSV once and caches for 24 hours.

    args:
        url (str): URL to download the stock master (CSV file expected).
    
    Usage:
        stock_master = StockMaster()
        stock_master.load()  # Downloads/loads cache
        
        token = stock_master.get_token("RELIANCE", "NSE")
        stock_info = stock_master.get_stock_info("2885", "NSE")
    """

    CACHE_FILE = "stock_master_cache.pkl"
    CACHE_EXPIRY_HOURS = 24

    def __init__(self, url:str):
        self.csv_url = url

        # Stock dict structure (stock dict[exchange][stock_code] = stock_token)
        self.stock_dict: Dict[Exchange, Dict[str, str]] = {
            Exchange.BSE: {},
            Exchange.NSE: {},
            Exchange.NDX: {},
            Exchange.MCX: {},
            Exchange.NFO: {},
            Exchange.BFO: {}
        }

        # token_list structure (token_list[exchange][stock_token] = (stock_code, company_name))
        self.token_dict: Dict[Exchange, Dict[str, Tuple[str,str]]] = {
            Exchange.BSE: {},
            Exchange.NSE: {},
            Exchange.NDX: {},
            Exchange.MCX: {},
            Exchange.NFO: {},
            Exchange.BFO: {}
        }
    
        # Thread safety
        self._lock = threading.Lock()

        # Loading state
        self._loaded = False
        self._cache_timestamp: Optional[float] = None


    def load(self, force_refresh: bool = False) -> bool:
        """
        Load stock master data (from cache or download).
        
        Args:
            force_refresh: If True, bypass cache and download fresh data
            
        Returns:
            True if loaded successfully, False otherwise
            
        Raises:
            Exception: If download fails and no cache available
        """
        with self._lock:
            if self._loaded and not force_refresh:
                logger.info("Stock master already loaded.")
                return True  # Already loaded
            
            if not force_refresh and self._load_from_cache():
                logger.info("Loaded stock master from cache.")
                self._loaded = True
                return True
            
            if self._download_and_parse():
                self._save_to_cache()
                self._loaded = True
                logger.info("Downloaded and loaded stock master.")
                return True
            
            logger.warning("Download failed, loading stale cache if available.")
            if self._load_from_cache(allow_stale=True):
                logger.info("Loaded stock master from stale cache.")
                self._loaded = True
                return True

            raise Exception("Failed to load stock master data.")
        
        
    def _download_and_parse(self) -> bool:
        """"Download and parse stock master CSV from URL"""
        
        try:
            logger.info(f"Downloading stock master CSV from {self.csv_url}")
            start_time = datetime.now()
        
            with requests.Session() as session:
                response = session.get(self.csv_url, timeout=30)
                response.raise_for_status()  # Raise error for bad responses
                content = response.content.decode('utf-8')
                csv_reader = csv.reader(content.splitlines(), delimiter=',')
                rows = list(csv_reader)

                for exchange in Exchange:
                    self.stock_dict[exchange].clear()
                    self.token_dict[exchange].clear()
   
            # Process rows
            processed_count = 0
            for row in rows:
                exchange_code = row[2]
                
                # Map exchange code to Exchange enum
                exchange_map = {
                    "BSE": Exchange.BSE,
                    "NSE": Exchange.NSE,
                    "NDX": Exchange.NDX,
                    "MCX": Exchange.MCX,
                    "NFO": Exchange.NFO,
                    "BFO": Exchange.BFO,
                }
                
                if exchange_code not in exchange_map:
                    continue
                
                exchange = exchange_map[exchange_code]
                
                # Determine stock code column
                if exchange in [Exchange.BSE, Exchange.NSE]:
                    stock_code = row[3]  # Column 3 for equity
                else:
                    stock_code = row[7]  # Column 7 for derivatives
                
                token = row[5]          # Column 5 is token
                company_name = row[1]   # Column 1 is company name
                
                # Store mappings
                self.stock_dict[exchange][stock_code] = token
                self.token_dict[exchange][token] = (stock_code, company_name)
                
                processed_count += 1
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"Parsed {processed_count} stocks in {elapsed:.2f}s "
                f"({len(rows)} total rows)"
            )
            return True
            
        except requests.RequestException as e:
            logger.error(f"Network error downloading stock master: {e}")
            return False
        except Exception as e:
            logger.error(f"Error parsing stock master: {e}", exc_info=True)
            return False
        

    def _load_from_cache(self, allow_stale: bool = False) -> bool:
            """
            Load stock master from cache file.
            
            Args:
                allow_stale: If True, load cache even if > 24h old
            """
            if not os.path.exists(self.CACHE_FILE):
                logger.info("No cache file found")
                return False
            
            try:
                # Check cache age
                cache_age = datetime.now() - datetime.fromtimestamp(
                    os.path.getmtime(self.CACHE_FILE)
                )
                
                # Check if cache expired (> 24 hours)
                if not allow_stale and cache_age > timedelta(hours=self.CACHE_EXPIRY_HOURS):
                    logger.info(
                        f"Cache expired (age: {cache_age.seconds // 3600}h, "
                        f"ICICI updates daily at 8 AM)"
                    )
                    return False
                
                # Load cache
                with open(self.CACHE_FILE, 'rb') as f:
                    cached_data = pickle.load(f)
                
                self.stock_dict = cached_data['stock_dict']
                self.token_dict = cached_data['token_dict']
                self._cache_timestamp = cached_data.get('timestamp')
                
                logger.info(
                    f"Loaded from cache (age: {cache_age.seconds // 3600}h, "
                    f"stale: {allow_stale})"
                )
                return True
                
            except Exception as e:
                logger.error(f"Failed to load cache: {e}")
                return False


    
    def _save_to_cache(self):
        """Save stock master to cache file"""
        try:
            cache_data = {
                'stock_dict': self.stock_dict,
                'token_dict': self.token_dict,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(self.CACHE_FILE, 'wb') as f:
                pickle.dump(cache_data, f)
            
            logger.info(f"Saved stock master to cache: {self.CACHE_FILE}")
            
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    
    def get_token(self, stock_code: str, exchange: str) -> Optional[str]:
        """Get token for stock code"""
        if not self._loaded:
            raise RuntimeError("Stock master not loaded. Call load() first.")
        
        try:
            exchange_enum = Exchange[exchange.upper()]
            return self.stock_dict[exchange_enum].get(stock_code.upper())
        except KeyError:
            logger.warning(f"Invalid exchange: {exchange}")
            return None
    
    def get_stock_info(self, token: str, exchange: str) -> Optional[Tuple[str, str]]:
        """Get stock info from token"""
        if not self._loaded:
            raise RuntimeError("Stock master not loaded. Call load() first.")
        
        try:
            exchange_enum = Exchange[exchange.upper()]
            return self.token_dict[exchange_enum].get(token)
        except KeyError:
            logger.warning(f"Invalid exchange: {exchange}")
            return None
    
    def get_full_token(
        self,
        stock_code: str,
        exchange: str,
        get_exchange_quotes: bool = True,
        get_market_depth: bool = False
    ) -> Optional[str]:
        """Get full token in format: X.Y!token"""
        token = self.get_token(stock_code, exchange)
        if not token:
            return None
        
        exchange_prefix = {
            "BSE": "1",
            "NSE": "4",
            "NFO": "4",
            "NDX": "13",
            "MCX": "5",
            "BFO": "8",
        }
        
        prefix = exchange_prefix.get(exchange.upper(), "4")
        level = "2" if get_market_depth else "1"
        
        return f"{prefix}.{level}!{token}"
    
    def is_loaded(self) -> bool:
        """Check if stock master is loaded"""
        return self._loaded
    
    def get_cache_age(self) -> Optional[int]:
        """Get cache age in hours"""
        if not os.path.exists(self.CACHE_FILE):
            return None
        
        cache_age = datetime.now() - datetime.fromtimestamp(
            os.path.getmtime(self.CACHE_FILE)
        )
        return int(cache_age.total_seconds() // 3600)
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about loaded data"""
        stats = {
            "BSE": len(self.stock_dict[Exchange.BSE]),
            "NSE": len(self.stock_dict[Exchange.NSE]),
            "NDX": len(self.stock_dict[Exchange.NDX]),
            "MCX": len(self.stock_dict[Exchange.MCX]),
            "NFO": len(self.stock_dict[Exchange.NFO]),
            "BFO": len(self.stock_dict[Exchange.BFO]),
            "total": sum(len(d) for d in self.stock_dict.values())
        }
        
        cache_age = self.get_cache_age()
        if cache_age is not None:
            stats["cache_age_hours"] = cache_age
        
        return stats


def get_data_from_stock_token_value(input_stock_token: str):
    try:
        output_data = {}
        stock_token = input_stock_token.split(".")
        exchange_type, stock_token = stock_token[0], stock_token[1].split("!")[1]
        exchange_code_list = {
            "1": "BSE",
            "4": "NSE",
            "13": "NDX",
            "6": "MCX",
        }
        exchange_code_name = exchange_code_list.get(exchange_type, False)
        if exchange_code_name == False:
            raise Exception(except_message.WRONG_EXCHANGE_CODE_EXCEPTION.value)
        elif exchange_code_name.lower() == "bse":
            stock_data = self.token_script_dict_list[0].get(stock_token, False)
            if stock_data == False:
                self.subscribe_exception(except_message.STOCK_NOT_EXIST_EXCEPTION.value.format("BSE",input_stock_token))
        elif exchange_code_name.lower() == "nse":
            stock_data = self.token_script_dict_list[1].get(stock_token, False)
            if stock_data == False:
                stock_data = self.token_script_dict_list[4].get(stock_token, False)
                if stock_data == False:    
                    self.subscribe_exception(except_message.STOCK_NOT_EXIST_EXCEPTION.value.format("i.e. NSE or NFO",input_stock_token))
                else:
                    exchange_code_name = "NFO"
        elif exchange_code_name.lower() == "ndx":
            stock_data = self.token_script_dict_list[2].get(stock_token, False)
            if stock_data == False:
                self.subscribe_exception(except_message.STOCK_NOT_EXIST_EXCEPTION.value.format("NDX",input_stock_token))
        elif exchange_code_name.lower() == "mcx":
            stock_data = self.token_script_dict_list[3].get(stock_token, False)
            if stock_data == False:
                self.subscribe_exception(except_message.STOCK_NOT_EXIST_EXCEPTION.value.format("MCX",input_stock_token))
        output_data["stock_name"] = stock_data[1]
        if exchange_code_name.lower() not in ["nse", "bse"]:
            product_type = stock_data[0].split("-")[0]
            if product_type.lower() == "fut":
                output_data["product_type"] = "Futures"
            if product_type.lower() == "opt":
                output_data["product_type"] = "Options"
            date_string = ""
            for date in stock_data[0].split("-")[2:5]:
                date_string += date + "-"
            output_data["expiry_date"] = date_string[:-1]
            if len(stock_data[0].split("-")) > 5:
                output_data["strike_price"] = stock_data[0].split("-")[5]
                right = stock_data[0].split("-")[6]
                if right.upper() == "PE":
                    output_data["right"] = "Put"
                if right.upper() == "CE":
                    output_data["right"] = "Call"
        return output_data
    except Exception as e:
        return {}




