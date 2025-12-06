"""
Test suite for StockMaster module.

Tests caching, thread safety, token lookups, and error handling.
"""
import os, sys
from dotenv import load_dotenv

import pytest
import threading
import time
import pickle
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

load_dotenv()

sys.path.insert(0, os.getenv("ROOT_DIR", ""))

# Import the module to test
from breeze_connect.utils.stock_master import StockMaster, Exchange


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_csv_content():
    """Sample CSV content for testing"""
    return """ShortName,CompanyName,Exchange,ExchangeStockCode,ISIN,Token,LotSize,FullName
RELIANCE INDUSTRIES,RELIANCE INDUSTRIES,NSE,RELIANCE,INE002A01018,2885,1,RELIANCE INDUSTRIES
TATA CONSULTANCY SERVICES,TATA CONSULTANCY SERVICES,NSE,TCS,INE467B01029,3588,1,TATA CONSULTANCY SERVICES
INFOSYS LIMITED,INFOSYS LIMITED,NSE,INFY,INE009A01021,1594,1,INFOSYS LIMITED
HDFC BANK LIMITED,HDFC BANK LIMITED,BSE,500180,INE040A01034,500180,1,HDFC BANK LIMITED
ICICI BANK LIMITED,ICICI BANK LIMITED,BSE,532174,INE090A01021,532174,1,ICICI BANK LIMITED
NIFTY 50 FUT,NIFTY 50 FUT,NFO,,INE000000000,26000,,NIFTY 50 FUT 27FEB2025
BANKNIFTY FUT,BANKNIFTY FUT,NFO,,INE000000000,26001,,BANKNIFTY FUT 27FEB2025
"""


@pytest.fixture
def mock_csv_url():
    """Mock CSV URL"""
    return "https://api.icicidirect.com/breezeapi/documents/stock_master.csv"


@pytest.fixture
def stock_master(mock_csv_url):
    """Create a StockMaster instance"""
    return StockMaster(mock_csv_url)


@pytest.fixture
def clean_cache():
    """Remove cache file before and after test"""
    cache_file = StockMaster.CACHE_FILE
    if os.path.exists(cache_file):
        os.remove(cache_file)
    yield
    if os.path.exists(cache_file):
        os.remove(cache_file)


# ============================================================================
# INITIALIZATION TESTS
# ============================================================================

def test_stockmaster_initialization(stock_master, mock_csv_url):
    """Test StockMaster initializes with correct defaults"""
    assert stock_master.csv_url == mock_csv_url
    assert not stock_master.is_loaded()
    assert stock_master._cache_timestamp is None
    
    # Check all exchanges initialized
    for exchange in Exchange:
        assert exchange in stock_master.stock_dict
        assert exchange in stock_master.token_dict
        assert len(stock_master.stock_dict[exchange]) == 0
        assert len(stock_master.token_dict[exchange]) == 0


# ============================================================================
# DOWNLOAD AND PARSE TESTS
# ============================================================================

def test_download_and_parse_success(stock_master, mock_csv_content, clean_cache):
    """Test successful CSV download and parsing"""
    with patch('requests.Session.get') as mock_get:
        # Mock successful response
        mock_response = Mock()
        mock_response.content = mock_csv_content.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Load data
        result = stock_master.load()
        
        assert result is True
        assert stock_master.is_loaded()
        
        # Check NSE stocks loaded
        assert stock_master.get_token("RELIANCE", "NSE") == "2885"
        assert stock_master.get_token("TCS", "NSE") == "3588"
        assert stock_master.get_token("INFY", "NSE") == "1594"
        
        # Check BSE stocks loaded
        assert stock_master.get_token("500180", "BSE") == "500180"
        assert stock_master.get_token("532174", "BSE") == "532174"


def test_download_network_error(stock_master, clean_cache):
    """Test handling of network errors during download"""
    with patch('requests.Session.get') as mock_get:
        mock_get.side_effect = Exception("Network error")
        
        with pytest.raises(Exception) as exc_info:
            stock_master.load()
        
        assert "Failed to load stock master data" in str(exc_info.value)
        assert not stock_master.is_loaded()


def test_download_timeout(stock_master, clean_cache):
    """Test handling of timeout during download"""
    with patch('requests.Session.get') as mock_get:
        import requests
        mock_get.side_effect = requests.Timeout("Connection timeout")
        
        with pytest.raises(Exception):
            stock_master.load()


# ============================================================================
# CACHING TESTS
# ============================================================================

def test_save_and_load_cache(stock_master, mock_csv_content, clean_cache):
    """Test saving and loading from cache"""
    with patch('requests.Session.get') as mock_get:
        # Mock CSV download
        mock_response = Mock()
        mock_response.content = mock_csv_content.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # First load - downloads CSV
        stock_master.load()
        assert mock_get.call_count == 1
        
        # Create new instance
        stock_master2 = StockMaster(stock_master.csv_url)
        
        # Second load - uses cache (no download)
        stock_master2.load()
        assert mock_get.call_count == 1  # Still 1 (no new download)
        
        # Verify data loaded from cache
        assert stock_master2.get_token("RELIANCE", "NSE") == "2885"
        assert stock_master2.is_loaded()


def test_cache_expiry(stock_master, mock_csv_content, clean_cache):
    """Test cache expires after 24 hours"""
    with patch('requests.Session.get') as mock_get:
        # Mock CSV download
        mock_response = Mock()
        mock_response.content = mock_csv_content.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # First load
        stock_master.load()
        
        # Modify cache file timestamp to 25 hours ago
        cache_file = StockMaster.CACHE_FILE
        old_time = time.time() - (25 * 3600)  # 25 hours ago
        os.utime(cache_file, (old_time, old_time))
        
        # Create new instance
        stock_master2 = StockMaster(stock_master.csv_url)
        
        # Load again - should download fresh (cache expired)
        stock_master2.load()
        
        # Should have downloaded twice (once original, once refresh)
        assert mock_get.call_count == 2


def test_force_refresh(stock_master, mock_csv_content, clean_cache):
    """Test force refresh bypasses cache"""
    with patch('requests.Session.get') as mock_get:
        # Mock CSV download
        mock_response = Mock()
        mock_response.content = mock_csv_content.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # First load
        stock_master.load()
        assert mock_get.call_count == 1
        
        # Force refresh
        stock_master.load(force_refresh=True)
        assert mock_get.call_count == 2  # Downloaded again


def test_stale_cache_fallback(stock_master, mock_csv_content, clean_cache):
    """Test falls back to stale cache if download fails"""
    with patch('requests.Session.get') as mock_get:
        # First load - success
        mock_response = Mock()
        mock_response.content = mock_csv_content.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        stock_master.load()
        
        # Make cache stale (25 hours old)
        cache_file = StockMaster.CACHE_FILE
        old_time = time.time() - (25 * 3600)
        os.utime(cache_file, (old_time, old_time))
        
        # Create new instance
        stock_master2 = StockMaster(stock_master.csv_url)
        
        # Second load - download fails, uses stale cache
        mock_get.side_effect = Exception("Network error")
        
        result = stock_master2.load()
        
        assert result is True  # Loaded from stale cache
        assert stock_master2.is_loaded()
        assert stock_master2.get_token("RELIANCE", "NSE") == "2885"


# ============================================================================
# TOKEN LOOKUP TESTS
# ============================================================================

def test_get_token_success(stock_master, mock_csv_content, clean_cache):
    """Test successful token lookup"""
    with patch('requests.Session.get') as mock_get:
        mock_response = Mock()
        mock_response.content = mock_csv_content.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        stock_master.load()
        
        # Test NSE
        assert stock_master.get_token("RELIANCE", "NSE") == "2885"
        assert stock_master.get_token("TCS", "NSE") == "3588"
        
        # Test case insensitive
        assert stock_master.get_token("reliance", "nse") == "2885"
        assert stock_master.get_token("RELIANCE", "nse") == "2885"


def test_get_token_not_found(stock_master, mock_csv_content, clean_cache):
    """Test token lookup for non-existent stock"""
    with patch('requests.Session.get') as mock_get:
        mock_response = Mock()
        mock_response.content = mock_csv_content.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        stock_master.load()
        
        assert stock_master.get_token("NONEXISTENT", "NSE") is None


def test_get_token_invalid_exchange(stock_master, mock_csv_content, clean_cache):
    """Test token lookup with invalid exchange"""
    with patch('requests.Session.get') as mock_get:
        mock_response = Mock()
        mock_response.content = mock_csv_content.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        stock_master.load()
        
        assert stock_master.get_token("RELIANCE", "INVALID") is None


def test_get_token_before_load(stock_master):
    """Test get_token raises error if not loaded"""
    with pytest.raises(RuntimeError) as exc_info:
        stock_master.get_token("RELIANCE", "NSE")
    
    assert "not loaded" in str(exc_info.value).lower()


# ============================================================================
# STOCK INFO TESTS
# ============================================================================

def test_get_stock_info_success(stock_master, mock_csv_content, clean_cache):
    """Test successful stock info lookup"""
    with patch('requests.Session.get') as mock_get:
        mock_response = Mock()
        mock_response.content = mock_csv_content.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        stock_master.load()
        
        stock_code, company_name = stock_master.get_stock_info("2885", "NSE")
        assert stock_code == "RELIANCE"
        assert "RELIANCE INDUSTRIES" in company_name


def test_get_stock_info_not_found(stock_master, mock_csv_content, clean_cache):
    """Test stock info lookup for non-existent token"""
    with patch('requests.Session.get') as mock_get:
        mock_response = Mock()
        mock_response.content = mock_csv_content.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        stock_master.load()
        
        assert stock_master.get_stock_info("99999", "NSE") is None


# ============================================================================
# FULL TOKEN TESTS
# ============================================================================

def test_get_full_token_exchange_quotes(stock_master, mock_csv_content, clean_cache):
    """Test full token generation for exchange quotes"""
    with patch('requests.Session.get') as mock_get:
        mock_response = Mock()
        mock_response.content = mock_csv_content.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        stock_master.load()
        
        # NSE exchange quotes (level 1)
        token = stock_master.get_full_token("RELIANCE", "NSE")
        assert token == "4.1!2885"
        
        # BSE exchange quotes (level 1)
        token = stock_master.get_full_token("500180", "BSE")
        assert token == "1.1!500180"


def test_get_full_token_market_depth(stock_master, mock_csv_content, clean_cache):
    """Test full token generation for market depth"""
    with patch('requests.Session.get') as mock_get:
        mock_response = Mock()
        mock_response.content = mock_csv_content.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        stock_master.load()
        
        # Market depth (level 2)
        token = stock_master.get_full_token(
            "RELIANCE",
            "NSE",
            get_market_depth=True
        )
        assert token == "4.2!2885"


def test_get_full_token_not_found(stock_master, mock_csv_content, clean_cache):
    """Test full token for non-existent stock"""
    with patch('requests.Session.get') as mock_get:
        mock_response = Mock()
        mock_response.content = mock_csv_content.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        stock_master.load()
        
        assert stock_master.get_full_token("NONEXISTENT", "NSE") is None


# ============================================================================
# THREAD SAFETY TESTS
# ============================================================================

def test_concurrent_loads(stock_master, mock_csv_content, clean_cache):
    """Test multiple threads loading simultaneously"""
    with patch('requests.Session.get') as mock_get:
        mock_response = Mock()
        mock_response.content = mock_csv_content.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Track how many times download was called
        call_count = [0]
        original_download = stock_master._download_and_parse
        
        def tracked_download():
            call_count[0] += 1
            time.sleep(0.1)  # Simulate slow download
            return original_download()
        
        stock_master._download_and_parse = tracked_download
        
        # Start 5 threads trying to load
        threads = []
        for _ in range(5):
            t = threading.Thread(target=stock_master.load)
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Should only download once (lock prevents duplicates)
        assert call_count[0] == 1
        assert stock_master.is_loaded()


def test_concurrent_reads_during_load(stock_master, mock_csv_content, clean_cache):
    """Test reading tokens while loading"""
    with patch('requests.Session.get') as mock_get:
        mock_response = Mock()
        mock_response.content = mock_csv_content.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        results = []
        errors = []
        
        def load_data():
            try:
                stock_master.load()
            except Exception as e:
                errors.append(e)
        
        def read_token():
            time.sleep(0.05)  # Wait a bit
            try:
                token = stock_master.get_token("RELIANCE", "NSE")
                results.append(token)
            except RuntimeError:
                # Expected if read before load completes
                pass
        
        # Start load thread
        load_thread = threading.Thread(target=load_data)
        load_thread.start()
        
        # Start read threads
        read_threads = []
        for _ in range(5):
            t = threading.Thread(target=read_token)
            read_threads.append(t)
            t.start()
        
        # Wait for all
        load_thread.join()
        for t in read_threads:
            t.join()
        
        # Should have no errors
        assert len(errors) == 0
        
        # All successful reads should get correct token
        for token in results:
            assert token == "2885" or token is None


def test_concurrent_force_refresh(stock_master, mock_csv_content, clean_cache):
    """Test force refresh while other threads are reading"""
    with patch('requests.Session.get') as mock_get:
        mock_response = Mock()
        mock_response.content = mock_csv_content.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Initial load
        stock_master.load()
        
        results = []
        
        def refresh():
            time.sleep(0.05)
            stock_master.load(force_refresh=True)
        
        def read():
            for _ in range(10):
                token = stock_master.get_token("RELIANCE", "NSE")
                results.append(token)
                time.sleep(0.01)
        
        # Start refresh and read threads
        refresh_thread = threading.Thread(target=refresh)
        read_threads = [threading.Thread(target=read) for _ in range(3)]
        
        refresh_thread.start()
        for t in read_threads:
            t.start()
        
        refresh_thread.join()
        for t in read_threads:
            t.join()
        
        # All reads should succeed (no None values)
        assert all(token == "2885" for token in results)


# ============================================================================
# STATS AND UTILITY TESTS
# ============================================================================

def test_get_stats(stock_master, mock_csv_content, clean_cache):
    """Test statistics generation"""
    with patch('requests.Session.get') as mock_get:
        mock_response = Mock()
        mock_response.content = mock_csv_content.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        stock_master.load()
        
        stats = stock_master.get_stats()
        
        assert 'NSE' in stats
        assert 'BSE' in stats
        assert 'total' in stats
        assert stats['NSE'] == 3  # RELIANCE, TCS, INFY
        assert stats['BSE'] == 2  # Two BSE stocks
        assert stats['total'] == stats['NSE'] + stats['BSE'] + stats['NFO']


def test_get_cache_age(stock_master, mock_csv_content, clean_cache):
    """Test cache age calculation"""
    with patch('requests.Session.get') as mock_get:
        mock_response = Mock()
        mock_response.content = mock_csv_content.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Before load
        assert stock_master.get_cache_age() is None
        
        # Load and check
        stock_master.load()
        
        # Create new instance to test cache age
        stock_master2 = StockMaster(stock_master.csv_url)
        stock_master2.load()
        
        cache_age = stock_master2.get_cache_age()
        assert cache_age is not None
        assert cache_age >= 0
        assert cache_age < 1  # Should be less than 1 hour


def test_is_loaded(stock_master, mock_csv_content, clean_cache):
    """Test is_loaded flag"""
    assert not stock_master.is_loaded()
    
    with patch('requests.Session.get') as mock_get:
        mock_response = Mock()
        mock_response.content = mock_csv_content.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        stock_master.load()
        
        assert stock_master.is_loaded()


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================

def test_malformed_csv(stock_master, clean_cache):
    """Test handling of malformed CSV data"""
    malformed_csv = "InvalidData,NoCommas\nBadFormat"
    
    with patch('requests.Session.get') as mock_get:
        mock_response = Mock()
        mock_response.content = malformed_csv.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Should not crash, just skip invalid rows
        result = stock_master.load()
        assert result is True


def test_empty_csv(stock_master, clean_cache):
    """Test handling of empty CSV"""
    with patch('requests.Session.get') as mock_get:
        mock_response = Mock()
        mock_response.content = b""
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = stock_master.load()
        assert result is True
        assert stock_master.is_loaded()


def test_corrupted_cache_file(stock_master, mock_csv_content, clean_cache):
    """Test handling of corrupted cache file"""
    # Create corrupted cache
    with open(StockMaster.CACHE_FILE, 'wb') as f:
        f.write(b"corrupted data")
    
    with patch('requests.Session.get') as mock_get:
        mock_response = Mock()
        mock_response.content = mock_csv_content.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Should download fresh data (cache corrupted)
        result = stock_master.load()
        assert result is True
        assert stock_master.is_loaded()


# ============================================================================
# INTEGRATION TEST
# ============================================================================

def test_full_workflow(stock_master, mock_csv_content, clean_cache):
    """Test complete workflow: load, lookup, refresh"""
    with patch('requests.Session.get') as mock_get:
        mock_response = Mock()
        mock_response.content = mock_csv_content.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # 1. Initial load
        stock_master.load()
        assert stock_master.is_loaded()
        
        # 2. Lookup tokens
        token = stock_master.get_token("RELIANCE", "NSE")
        assert token == "2885"
        
        # 3. Get stock info
        stock_code, company = stock_master.get_stock_info("2885", "NSE")
        assert stock_code == "RELIANCE"
        
        # 4. Get full token
        full_token = stock_master.get_full_token("RELIANCE", "NSE")
        assert full_token == "4.1!2885"
        
        # 5. Check stats
        stats = stock_master.get_stats()
        assert stats['total'] > 0
        
        # 6. Force refresh
        stock_master.load(force_refresh=True)
        
        # 7. Verify still works
        token = stock_master.get_token("TCS", "NSE")
        assert token == "3588"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])