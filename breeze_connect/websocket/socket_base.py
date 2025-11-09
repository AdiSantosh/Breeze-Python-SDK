
import socketio
import threading
from enum import Enum
from typing import Set, Dict, Optional
import dotenv
import logging, os

logger = logging.getLogger("WebSocketLogger")


from core.config import ExceptionMessage


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
        self._sub_lock = threading.Lock()
        
        #Connection settings
        self.hostname: Optional[str] = None
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

        self._resubscribe_to_symbols()


    def on_disconnect_event(self):
        """Handle disconnection event."""
        logger.warning("WebSocket disconnected.")
        self._set_state(SocketState.DISCONNECTED)


    def on_connect_error(self, error_msg):
        """Handle connection error event."""
        logger.error(f"WebSocket connection error: {error_msg}")
        self._set_state(SocketState.ERROR)
        self.is_authenticated = False


    def get_state(self) -> SocketState:
        """Thread-safe state getter."""
        with self._state_lock:
            return self.state
        

    def connect(self, hostname: str, is_ohlc: bool = False):
        """Establish WebSocket connection."""

        auth = {"user": self.breeze.user_id, "token": self.breeze.seesion_key}
        try:
            if is_ohlc:
                self.sio.connect(hostname, socketio_path="ohlcvstream", headers=CustomHeaders.USER_AGENT.value, auth=auth,
                                transports="websocket", wait_timeout=3)
            else:
                self.sio.connect(hostname, headers=CustomHeaders.USER_AGENT.value, auth=auth,
                                transports="websocket", wait_timeout=3)
            self._register_handlers()

        except Exception as e:
            if self.sio.connected:
                logger.info("WebSocket already connected.")
                self._set_state(SocketState.CONNECTED)
            else:
                if hostname == os.getenv("LIVE_OHLC_STREAM_URL"):
                    raise Exception(except_message.OHLC_SOCKET_CONNECTION_DISCONNECTED.value)
                elif hostname == os.getenv("LIVE_STREAM_URL"):
                    raise Exception(except_message.LIVESTREAM_SOCKET_CONNECTION_DISCONNECTED.value)
                else:
                    raise Exception(except_message.ORDERNOTIFY_SOCKET_CONNECTION_DISCONNECTED.value)


    def _resubscribe_to_symbols(self):
        pass



class BreezeConnect():
    def __init__(self):
        self.user_id = ""
        self.seesion_key = ""

    



        