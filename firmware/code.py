import time
import board # type: ignore
import digitalio # type: ignore
import busio # type: ignore
import gc
from config import Config

from lib.cptoml import fetch
from enums import LdProduct, SensorModel, Color
from led_controller import LedController
import os

import neopixel # type: ignore

# Configuration
TEST_MODE = fetch('TEST_MODE')
SSID = fetch('SSID')
PASSWORD = fetch('PASSWORD')

if TEST_MODE:
    API_URL = fetch('TEST_API_URL')
else:
    API_URL = fetch('API_URL')

FIRMWARE_MAJOR = fetch('FIRMWARE_MAJOR')
FIRMWARE_MINOR = fetch('FIRMWARE_MINOR')
FIRMWARE_PATCH = fetch('FIRMWARE_PATCH')
PROTOCOL_VERSION = fetch('PROTOCOL_VERSION')
MODEL = fetch('model')
Config.MANUFACTURE_ID = fetch('MANUFACTURE_ID')

Config.SSID = SSID
Config.PASSWORD = PASSWORD
Config.API_URL = API_URL
Config.FIRMWARE_MAJOR = FIRMWARE_MAJOR
Config.FIRMWARE_MINOR = FIRMWARE_MINOR
Config.FIRMWARE_PATCH = FIRMWARE_PATCH
Config.PROTOCOL_VERSION = PROTOCOL_VERSION
Config.MODEL = MODEL

# print settings
print(f'{SSID=}')
print(f'{PASSWORD=}')
print(f'{API_URL=}')
print(f'{FIRMWARE_MAJOR=}')
print(f'{FIRMWARE_MINOR=}')
print(f'{FIRMWARE_PATCH=}')
print(f'{PROTOCOL_VERSION=}')
print(f'{MODEL=}')

# Initialize status LED(s) at GPIO8
status_led = neopixel.NeoPixel(board.IO8, 5 if MODEL == LdProduct.AIR_CUBE else 1)
status_led.fill(Color.CYAN)
status_led.show()
time.sleep(1)

# Check boot mode
# Options:
# - normal:
#    - Check if button is pressed
#        - If pressed, check all sensors and save to boot.toml. Reboot into transmit mode.
#        - If not pressed, load boot.toml and connect to all sensors listed. Start BLE operation.
# - transmit:
#    - Send device status data to API. Reboot into normal mode.

boot_mode = fetch('boot_into', toml="/boot.toml")
if boot_mode == 'transmit':
    status_led.fill(Color.ORANGE)
    status_led.show()
    # Relevant imports
    import wifi # type: ignore
    # Get MAC address
    mac = wifi.radio.mac_address_ap.hex().upper()
    #import socketpool
    #import adafruit_requests
    #import ssl
    #import json
    # Do the transmission bit
    # ...
    time.sleep(2)
    # Do we want to auto-detect device model (model == -1 in boot.toml)?
    next_boot_mode = 'normal'
    if MODEL == -1:
        # Do auto-detect
        next_boot_mode = 'detectmodel'
    # Reset boot mode
    from storage import remount # type: ignore
    from lib.cptoml import put
    remount("/", False)
    put('boot_into', next_boot_mode, toml="/boot.toml")
    put('mac', mac, toml="/boot.toml")
    # save device id
    put('device_id', f'{os.uname()[0]}-{mac}-{Config.MANUFACTURE_ID}', toml='/boot.toml')
    remount("/", True)
    # Reboot
    import supervisor # type: ignore
    supervisor.reload()
    # This should never be reached

if boot_mode == 'detectmodel':
    # Try to connect to battery sensor, as that is part of criteria
    from sensors.max17048 import MAX17048
    i2c = busio.I2C(scl=board.IO5, sda=board.IO4, frequency=20000)
    battery_monitor = None
    for i in range(10):
        try:
            battery_monitor = MAX17048(i2c)
            print(f'Attempt {i+1}: Battery monitor initialized')
            break
        except:
            pass
        print("Waiting 0.5 seconds before retrying battery monitor initialization")
        time.sleep(0.5)
    # Fetch list of connected sensors
    possible_sensor_ids = [
        SensorModel.SEN5X,
        SensorModel.BME280,
        SensorModel.BME680,
        SensorModel.AHT20,
        SensorModel.BMP280,
        SensorModel.AGS02MA,
        SensorModel.SHT30,
        SensorModel.SHT31,
        SensorModel.SCD4X,
        SensorModel.SHT4X,
        SensorModel.SGP40,
    ]
    connected_sensors = {}
    for sensor_id in possible_sensor_ids:
        try:
            connected_sensors[sensor_id] = fetch(str(sensor_id), toml="/boot.toml")
        except:
            connected_sensors[sensor_id] = False
    # Find correct model
    device_model = -1
    colors = []
    if connected_sensors[SensorModel.SCD4X]:
        device_model = LdProduct.AIR_CUBE
        colors = [Color.WHITE, Color.PURPLE]
    elif battery_monitor == None:
        device_model = LdProduct.AIR_STATION
        colors = [Color.WHITE, Color.GREEN]
    elif not connected_sensors[SensorModel.SEN5X]:
        device_model = LdProduct.AIR_BADGE
        colors = [Color.CYAN, Color.ORANGE]
    else:
        device_model = LdProduct.AIR_AROUND
        colors = [Color.WHITE, Color.BLUE]
    # Reset boot mode
    from storage import remount # type: ignore
    from lib.cptoml import put
    remount("/", False)
    put('boot_into', 'normal', toml="/boot.toml")
    put('model', device_model)
    remount("/", True)
    # Show which model was detected
    status_led.fill(colors[0])
    status_led.show()
    time.sleep(2)
    status_led.fill(colors[1])
    status_led.show()
    time.sleep(2)
    # Reboot
    import supervisor # type: ignore
    supervisor.reload()
    # This should never be reached

# Initialize the button at GPIO9
button_pin = board.IO9
button = digitalio.DigitalInOut(button_pin)
button.direction = digitalio.Direction.INPUT

# Initialize I2C at GPIO4 and GPIO5
i2c = busio.I2C(scl=board.IO5, sda=board.IO4, frequency=20000)

# If button was pressed, check all sensors and save to boot.toml
if button.value or MODEL == -1:
    status_led.fill(Color.MAGENTA)
    status_led.show()
    
    from lib.cptoml import put
    from storage import remount # type: ignore
    # Import all sensor modules (if we have many, may go over memory limit)
    from sensors.sensor_sen5x import Sen5xSensor
    from sensors.sensor_bme280 import BME280Sensor
    from sensors.sensor_bme680 import BME680Sensor
    from sensors.sensor_aht20 import AHT20Sensor
    from sensors.sensor_bmp280 import BMP280Sensor
    from sensors.sensor_ags02ma import AGS02MASensor
    from sensors.sensor_scd4x import Scd4xSensor
    from sensors.sensor_sht30 import Sht30Sensor
    from sensors.sensor_sht31 import Sht31Sensor
    from sensors.sensor_sht4x import Sht4xSensor
    from sensors.sensor_sgp40 import Sgp40Sensor

    # List of sensors that we will attempt to connect to
    defined_sensors = [
        Sen5xSensor(),
        BME280Sensor(),
        BME680Sensor(),
        AHT20Sensor(),
        BMP280Sensor(),
        AGS02MASensor(),
        Sht30Sensor(),
        Sht31Sensor(),
        Scd4xSensor(),
        Sht4xSensor(),
        Sgp40Sensor(),
    ]
    remount("/", False)
    for sensor in defined_sensors:
        if sensor.attempt_connection(i2c):
            put(str(sensor.model_id), True, toml="/boot.toml")
            if sensor.model_id == SensorModel.SEN5X:
                put(str(sensor.model_id) + "_is_sen54", sensor.is_sen54, toml="/boot.toml")
        else:
            put(str(sensor.model_id), False, toml="/boot.toml")
    status_led.fill(Color.PURPLE)
    status_led.show()
    put('boot_into', 'transmit', toml="/boot.toml")
    status_led.fill(Color.PURPLE)
    status_led.show()
    remount("/", True)
    # Reboot
    status_led.fill(Color.WHITE)
    status_led.show()
    import supervisor # type: ignore
    supervisor.reload()
    # This should never be reached

# If we reached this point, we are in normal mode

status_led.fill(Color.BLUE)
status_led.show()

# Check for sensors in boot.toml.
listed_sensors = [] # Sensors that we will connect to
for model_id in [SensorModel.SEN5X, 
                 SensorModel.BME280, 
                 SensorModel.BME680, 
                 SensorModel.AHT20, 
                 SensorModel.BMP280, 
                 SensorModel.AGS02MA, 
                 SensorModel.SHT30, 
                 SensorModel.SHT31,
                 SensorModel.SCD4X,
                 SensorModel.SHT4X,
                 SensorModel.SGP40
                 ]:
    try:
        add = False
        add = fetch(str(model_id), toml="/boot.toml")
        if add:
            print(f'Will attempt to connect to sensor {model_id} (boot.toml)')
            # Import only sensors we will use
            if model_id == SensorModel.SEN5X:
                from sensors.sensor_sen5x import Sen5xSensor
                is_sen54 = fetch(str(model_id) + "_is_sen54", toml="/boot.toml")
                listed_sensors.append(Sen5xSensor(is_sen54))
                pass
            elif model_id == SensorModel.BME280:
                from sensors.sensor_bme280 import BME280Sensor
                listed_sensors.append(BME280Sensor())
            elif model_id == SensorModel.BME680:
                from sensors.sensor_bme680 import BME680Sensor
                listed_sensors.append(BME680Sensor())
            elif model_id == SensorModel.AHT20:
                from sensors.sensor_aht20 import AHT20Sensor
                listed_sensors.append(AHT20Sensor())
            elif model_id == SensorModel.BMP280:
                from sensors.sensor_bmp280 import BMP280Sensor
                listed_sensors.append(BMP280Sensor())
            elif model_id == SensorModel.AGS02MA:
                from sensors.sensor_ags02ma import AGS02MASensor
                listed_sensors.append(AGS02MASensor())
            elif model_id == SensorModel.SHT30:
                from sensors.sensor_sht30 import Sht30Sensor
                listed_sensors.append(Sht30Sensor())
            elif model_id == SensorModel.SHT31:
                from sensors.sensor_sht31 import Sht31Sensor
                listed_sensors.append(Sht31Sensor())
            elif model_id == SensorModel.SCD4X:
                from sensors.sensor_scd4x import Scd4xSensor
                listed_sensors.append(Scd4xSensor())
            elif model_id == SensorModel.SHT4X:
                from sensors.sensor_sht4x import Sht4xSensor
                listed_sensors.append(Sht4xSensor())
            elif model_id == SensorModel.SGP40:
                from sensors.sensor_sgp40 import Sgp40Sensor
                listed_sensors.append(Sgp40Sensor())
        else:
            print(f'Will not attempt to connect to sensor {model_id} (boot.toml)')
    except:
        print(f'Sensor {model_id} not found in boot.toml')
        print(f'Have you run the initial setup procedure?')
print("Sensors loaded from boot.toml")

from ld_service import LdService

from adafruit_ble import BLERadio # type: ignore
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement # type: ignore

# Battery monitor
from sensors.max17048 import MAX17048

# Initialize MAX17048 battery monitor at I2C
battery_monitor = None

for i in range(10):
    try:
        battery_monitor = MAX17048(i2c)
        print(f'Attempt {i+1}: Battery monitor initialized')
        break
    except:
        pass
    print("Waiting 0.5 seconds before retrying battery monitor initialization")
    time.sleep(0.5)
if battery_monitor is None:
    print("Battery monitor failed to initialize after 10 attempts")

# Connect to all sensors that were discovered and saved in boot.toml
sensors = []
connected_sensors_status = bytearray([
    len(listed_sensors), # Number of sensors
])
for sensor in listed_sensors:
    print("Currently at", gc.mem_free())
    if not sensor.attempt_connection(i2c):
        print(f"Failed to connect to sensor {sensor.model_id}")
        connected_sensors_status.extend([
            sensor.model_id,
            0x00, # Not connected
        ])
    else:
        print(f"Connected to sensor {sensor.model_id}")
        connected_sensors_status.extend([
            sensor.model_id,
            0x01, # Connected
        ])
        sensors.append(sensor)

# Initialize BLE, define custom service
ble = BLERadio()
service = LdService()

# Set BLE name to Luftdaten.at-MAC
mac = fetch('mac', toml="/boot.toml")
ble.name = "Luftdaten.at-" + mac

led_controller = LedController(status_led, 5 if MODEL == LdProduct.AIR_CUBE else 1)

device = None
if MODEL == LdProduct.AIR_AROUND or MODEL == LdProduct.AIR_BADGE or MODEL == LdProduct.AIR_BIKE:
    from models.ld_portable import LdPortable
    device = LdPortable(MODEL, service, sensors, battery_monitor, led_controller)
if MODEL == LdProduct.AIR_CUBE:
    from models.air_cube import AirCube
    device = AirCube(service, sensors, battery_monitor, led_controller)
if MODEL == LdProduct.AIR_STATION:
    from models.air_station import AirStation
    device = AirStation(service, sensors, battery_monitor, led_controller)

if device == None:
    print("Model not recognised")
    while True:
        time.sleep(1)
        status_led.fill(Color.RED)
        status_led.show()
        time.sleep(1)
        status_led.fill(Color.ORANGE)
        status_led.show()

# Set up device info characteristic
device_info_data = bytearray([
    PROTOCOL_VERSION,
    FIRMWARE_MAJOR,
    FIRMWARE_MINOR,
    FIRMWARE_PATCH,
    # Device Name (e.g. F001). To be retrieved from Datahub, otherwise use 0x00 0x00 0x00 0x00
    0x00, 0x00, 0x00, 0x00, # Not yet implemented
    MODEL, # Device model (e.g. AIR_AROUND)
])
device_info_data.extend(connected_sensors_status)
service.device_info_characteristic = device_info_data


# Set up sensor info characteristic
if len(sensors) > 0:
    sensor_info = bytearray()
    for sensor in sensors:
        sensor_info.extend(sensor.get_device_info())
    service.sensor_info_characteristic = sensor_info
else:
    service.sensor_info_characteristic = bytes([0x06])
    
# Load battery status for the first time
if battery_monitor is not None: # First none should be battery_monitor
    service.device_status_characteristic = bytes([
        1, # Has battery status: Yes
        round(battery_monitor.cell_soc()), # Battery percentage
        round(battery_monitor.cell_voltage() * 10), # Battery voltage
        0, # Error status: 0 = no error
    ])
else:
    service.device_status_characteristic = bytes([
        0, # Has battery status: No
        0, 0, # Battery percentage, voltage
        0, # Error status: 0 = no error
    ])
    
# Create services advertisement
advertisement = ProvideServicesAdvertisement(service)

# Flash the status LED green for 2s to indicate the device is ready, then turn off
status_led.fill(Color.GREEN)
status_led.show()
time.sleep(2)
status_led.fill(Color.OFF)
status_led.show()

for sensor in sensors:
    sensor.on_start_main_loop(device)

# If a battery monitor is connected, indicate battery percentage
if battery_monitor is not None:
    print('show battery state in 2 seconds')
    time.sleep(2)
    CRITICAL = 10
    percent = round(battery_monitor.cell_soc())
    points = [25, 50, 75]
    # critical
    if percent < CRITICAL:
        status_led.fill(Color.RED)
        status_led.show()
        time.sleep(0.2)
        status_led.fill(Color.OFF)
        status_led.show()
    else:
        for point in points:
            if percent>point:
                status_led.fill(Color.GREEN)
                status_led.show()
                time.sleep(0.5)
                status_led.fill(Color.OFF)
                status_led.show()
                time.sleep(0.5)
    time.sleep(2)

#buf = bytearray(512)

button_state = False

device.connection_update(False)

ble_connected = False

# Main loop
while True:
    # clean memory
    gc.collect()

    if not ble.advertising and device.ble_on:
        ble.start_advertising(advertisement)
        print("Started advertising")
    elif ble.advertising and not device.ble_on:
        ble.stop_advertising()
        print("Stopped advertising")
        
    if ble.connected and not ble_connected:
        ble_connected = True
        device.connection_update(True)
        print("BLE connection established")
    elif not ble.connected and ble_connected:
        ble_connected = False
        device.connection_update(False)
        print("Disconnected from BLE device")

    if button.value and not button_state:
        button_state = True
        device.receive_button_press()
        print("Button pressed")
    elif not button.value and button_state:
        button_state = False
        print("Button released")

    if service.trigger_reading_characteristic_2:
        command = service.trigger_reading_characteristic_2
        service.trigger_reading_characteristic_2 = bytearray()

        device.receive_command(command)
        led_controller.receive_command(command)

    device.tick()
    
    led_controller.tick()

    time.sleep(device.polling_interval)
