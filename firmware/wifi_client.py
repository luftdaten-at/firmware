import wifi # type: ignore
import ssl # type: ignore
import socketpool # type: ignore
import adafruit_requests # type: ignore
import json
from lib.cptoml import put
from storage import remount

class WifiClient:
    def __init__(self, connection_callback: callable | None = None):
        self.connection_callback = connection_callback
        
    def connect(self, ssid: str, password: str) -> bool | int:
        wifi.radio.enabled = True
        try:
            print("Connecting to Wi-Fi...")
            wifi.radio.connect(ssid, password)
            print("Connected to Wi-Fi")
            # Load the root CA certificate
            with open("/certs/isrgrootx1.pem", "rb") as f:
                root_ca = f.read()
            # Create an SSL context
            context = ssl.create_default_context()
            context.load_verify_locations(cadata=root_ca)
            # Create a request session
            pool = socketpool.SocketPool(wifi.radio)
            self.requests = adafruit_requests.Session(pool, ssl_context=context)
            print("SSL initialized & request session created")

            print('Write credentials to settings.toml')
            print(f'write ssid: {ssid}, pwd: {password}')
            # write credentials to settings.toml 
            remount('/', False)
            put('SSID', ssid, toml='/settings.toml')
            put('PASSWORD', password, toml='/settings.toml')

            return True
        except ConnectionError as connection_error:
            message: str = connection_error.errno
            if message == "No network with that ssid":
                print("SSID not found")
                return ConnectionFailure.SSID_NOT_FOUND
            elif message == "Authentication failure":
                print("Password incorrect")
                return ConnectionFailure.PASSWORD_INCORRECT
        except ValueError as value_error:
            message: str = value_error.args[0]
            if message == "password length must be 8-64":
                print("Password length must be 8-64 characters long")
                return ConnectionFailure.PASSWORD_LENGTH
            elif message == "Invalid BSSID":
                print("Invalid BSSID")
                return ConnectionFailure.INVALID_BSSID
        except:
            print("Unspecified error occurred while connecting to Wi-Fi")
            return ConnectionFailure.OTHER
        
    def disconnect(self) -> None:
        wifi.radio.enabled = False
        print("Disconnected from Wi-Fi")
        
    def connected(self) -> bool:
        return wifi.radio.connected
    
    most_recent_connection_status = False
    
    def tick(self) -> None:
        """Only needed when connection_callback is set."""
        if self.connection_callback is not None:
            if self.connected() != self.most_recent_connection_status:
                self.most_recent_connection_status = self.connected()
                self.connection_callback(self.connected())
                
    def post(self, url: str, jsonData: dict | None = None) -> adafruit_requests.Response:
        headers = {"Content-Type": "application/json"}
        return self.requests.post(url, data=json.dumps(jsonData), headers=headers)

class ConnectionFailure:
    SSID_NOT_FOUND = 1
    PASSWORD_INCORRECT = 2
    PASSWORD_LENGTH = 3
    INVALID_BSSID = 4
    OTHER = 5