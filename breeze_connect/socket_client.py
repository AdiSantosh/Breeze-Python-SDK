
import socketio
import threading
from enum import Enum
from typing import Set, Dict, Optional
import dotenv
import logging, os

logger = logging.getLogger("WebSocketLogger")

from breeze_connect.config_new import ExceptionMessage

except_message = ExceptionMessage

class SocketState(Enum):
    """WebSocket connection states."""
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    ERROR = 3

class CustomHeaders(Enum):
    """Custom headers for WebSocket connections."""
    USER_AGENT = {"User-Agent": "python-socketio[client]/socket"}
    APP_JSON = {"Content-Type": "application/json"}

class SocketBase(socketio.ClientNamespace):
    """Base class for WebSocket connections."""

    def __init__(self, namespace: str, breeze_instance):  ## Instance of BreezeConnect
        """
        Initialize socket client.
        
        Args:
            namespace: Socket.IO namespace (usually "/")
            breeze_instance: Reference to parent BreezeConnect
        """
        super().__init__(namespace)
        self.breeze = breeze_instance
        self.sio = socketio.Client(logger=False, engineio_logger=False)

        #State management
        self.state = SocketState.DISCONNECTED
        self._state_lock = threading.Lock()
        self.is_ohlc = False

        #Subscription tracking
        self.subscriptions: Set[str] = set()
        self.ohlc_subscriptions: Set[tuple] = set()
        self._sub_lock = threading.Lock()
        
        #Connection settings
        # self.hostname: Optional[str] = None
        self.is_authenticated: bool = False

        #Reconnection settings
        self.reconnect_attempts: int = 0
        self.max_reconnect_attempts: int = 5  
        self.reconnect_delay: int = 2 #secs

        self._register_handlers()  

    def _register_handlers(self):
        """Register event handlers for Socket.IO events."""
        self.sio.on('connect', self.on_connect_event)
        self.sio.on('disconnect', self.on_disconnect_event)
        self.sio.on('connect_error', self.on_connect_error)

        self.sio.on('order', self.on_message)
        self.sio.on('stock', self.on_message)

        for channel in ['1minute', '3minute', '5minute', '10minute', '15minute', '30minute', '60minute', 'day', 'week', 'month']:
            self.sio.on(channel, self.on_ohlc_sub)
## change all the message to what is expected from the server (check error, disconnect etc)

    def _set_state(self, new_state: SocketState):
        """Thread-safe state setter."""
        with self._state_lock:
            old_state = self.state
            self.state = new_state
            if old_state != self.state:
                logger.info(f"Socket state changed from {old_state} to {new_state}")


    def on_connect_event(self):
        """Handle successful connection event."""
        logger.info("WebSocket connected.")

        self._set_state(SocketState.CONNECTED)
        self.is_authenticated = True

        self.rewatch()
        self.rewatch_ohlc()


    def on_disconnect_event(self):
        """Handle disconnection event."""
        logger.warning("WebSocket disconnected.")
        self._set_state(SocketState.DISCONNECTED)


    def on_connect_error(self, error_msg):
        """Handle connection error event."""
        logger.error(f"WebSocket connection error: {error_msg}")
        self._set_state(SocketState.ERROR)
        self.is_authenticated = False

    def on_ohlc_sub(self,data):
        data = self.breeze.parse_ohlc_data(data)
        self.breeze.on_ticks(data)

    def on_message(self, data):
        """Handle incoming messages."""
        data = self.breeze.parse_data(data)
        if "symbol" in data and data["symbol"] != None and len(data["symbol"]) > 0:
            data.update(self.breeze.get_data_from_symbol(data["symbol"]))
        if self.breeze.on_ticks is not None:
            self.breeze.on_ticks(data)
        if self.breeze.on_ticks2 is not None:
            self.breeze.on_ticks2(data)

    def get_state(self) -> SocketState:
        """Thread-safe state getter."""
        with self._state_lock:
            return self.state
        

    def connect(self, hostname: str, is_ohlc: bool = False):
        """Establish WebSocket connection."""
        if self.get_state() == SocketState.CONNECTED:
            logger.info("WebSocket already connected.")
            return
    
        self._set_state(SocketState.CONNECTING)
        auth = {"user": self.breeze.user_id, "token": self.breeze.session_key}
        try:
            if is_ohlc:
                self.sio.connect(hostname, socketio_path="ohlcvstream", headers=CustomHeaders.USER_AGENT.value, auth=auth,
                                transports="websocket", wait_timeout=3)
            else:
                self.sio.connect(hostname, headers=CustomHeaders.USER_AGENT.value, auth=auth,
                                transports="websocket", wait_timeout=3)

        except Exception as e:
            if hostname == os.getenv("LIVE_OHLC_STREAM_URL"):
                raise Exception(except_message.OHLC_SOCKET_CONNECTION_DISCONNECTED.value)
            elif hostname == os.getenv("LIVE_STREAM_URL"):
                raise Exception(except_message.LIVESTREAM_SOCKET_CONNECTION_DISCONNECTED.value)
            else:
                raise Exception(except_message.ORDERNOTIFY_SOCKET_CONNECTION_DISCONNECTED.value)


    def disconnect(self):
        """Request to disconnect from the websocket"""
        self.sio.emit("disconnect", "transport close")
        logger.info("WebSocket disconnect requested.")


    def watch(self, token) -> None:
        """Subscribe to data stream."""
        if not self.sio.connected or self.state != SocketState.CONNECTED:
            raise Exception(except_message.LIVESTREAM_SOCKET_CONNECTION_DISCONNECTED.value)
        
        with self._sub_lock:
            if isinstance(token, list):
                for t in token:
                    self.subscriptions.add(t)
                logger.info(f"Subscribing to tokens: {token}")
            else:
                self.subscriptions.add(token)
                logger.info(f"Subscribing to token: {token}")

        self.sio.emit("join", token)
        logger.info(f"Subscribed to tokens")
        

    def watch_ohlc(self, token, channel) -> None:
        """Subscribe to OHLC data stream."""
        if not self.sio.connected:
            raise Exception(except_message.OHLC_SOCKET_CONNECTION_DISCONNECTED.value)
        
        try:
            with self._sub_lock:
                if (token, channel) not in self.ohlc_subscriptions:
                    self.ohlc_subscriptions.add((token, channel))
                self.sio.emit("join", token)

            logger.info(f"Subscribed to OHLC tokens: {token} on channel: {channel}")
        except Exception as e:
            raise Exception(except_message.OHLC_SOCKET_CONNECTION_DISCONNECTED.value)
    
    def rewatch_ohlc(self):
        """Resubscribe to OHLC data streams after reconnection."""
        with self._sub_lock:
            for token, channel in self.ohlc_subscriptions:
                self.sio.emit("join", token)
                self.sio.on(channel, self.on_ohlc_sub)
            logger.info(f"Resubscribed to OHLC tokens: {self.ohlc_subscriptions}")

    
    def rewatch(self):
        """Resubscribe to data streams after reconnection."""
        with self._sub_lock:
            for token in self.subscriptions:
                self.sio.emit("join", token)
            logger.info(f"Resubscribed to tokens: {self.subscriptions}")


    def unwatch(self, token) -> None:
        """Unsubscribe from data stream.""" 
        if not self.sio.connected:
            raise Exception(except_message.LIVESTREAM_SOCKET_CONNECTION_DISCONNECTED.value)
        
        with self._sub_lock:
            if isinstance(token, list):
                for t in token:
                    self.subscriptions.discard(t)
            else:
                self.subscriptions.discard(token)

        if len(self.ohlc_subscriptions) > 0:
            to_remove = set()
            with self._sub_lock:
                for t, channel in self.ohlc_subscriptions:
                    if t == token or (isinstance(token, list) and t in token):
                        to_remove.add((t, channel))
                for item in to_remove:
                    self.ohlc_subscriptions.discard(item)
                
        self.sio.emit("leave", token)
        logger.info(f"Unsubscribed from tokens: {token}")

            


                
        


    



        