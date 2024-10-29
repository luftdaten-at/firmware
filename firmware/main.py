import time
import board  # type: ignore
import digitalio  # type: ignore
import busio  # type: ignore
import gc
import os
import neopixel  # type: ignore
from ld_service import LdService
from adafruit_ble import BLERadio  # type: ignore
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement  # type: ignore

from config import Config
from enums import LdProduct, SensorModel, Color
from led_controller import LedController
from wifi_client import WifiUtil
from ugm.upgrade_mananger import Ugm


# Initialize status LED(s) at GPIO8
status_led = neopixel.NeoPixel(board.IO8, 5 if Config.settings['MODEL'] == LdProduct.AIR_CUBE else 1)
status_led.fill(Color.CYAN)
status_led.show()
time.sleep(1)

# Check boot mode
# Options:
# - normal:
#    - Check if button is pressed
#        - If pressed, check all sensors and save to boot.toml. Reboot into transmit mode.
#        - If not pressed, load boot.toml and connect to all sensors listed. Start BLE operation.
# - detectmodel

# Load startup config
Config.init()
Ugm.init(WifiUtil, Config)

# init bus
i2c = busio.I2C(scl=board.IO5, sda=board.IO4, frequency=20000)

# Initialize the button at GPIO9
button_pin = board.IO9
button = digitalio.DigitalInOut(button_pin)
button.direction = digitalio.Direction.INPUT

def get_connected_sensors():
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

    connected_sensors = {}

    for sensor in defined_sensors:
        if sensor.attempt_connection(i2c):
            print(f'Found sensor: {sensor.model_id}')
            connected_sensors[sensor.model_id] = sensor

    return connected_sensors

def get_battery_monitor():
    # Try to connect to battery sensor, as that is part of criteria
    from sensors.max17048 import MAX17048
    battery_monitor = None
    for i in range(10):
        try:
            battery_monitor = MAX17048(i2c)
            print(f'Attempt {i + 1}: Battery monitor initialized')
            break
        except:
            pass
        print("Waiting 0.5 seconds before retrying battery monitor initialization")
        time.sleep(0.5)
    
    return battery_monitor

def get_model_id_from_sensors(connected_sensors: dict, battery_monitor) -> int:
    # Find correct model
    device_model = -1
    if connected_sensors.get(SensorModel.SCD4X, None):
        device_model = LdProduct.AIR_CUBE
    elif battery_monitor is None:
        device_model = LdProduct.AIR_STATION
    elif not connected_sensors.get(SensorModel.SEN5X, None):
        device_model = LdProduct.AIR_BADGE
    else:
        device_model = LdProduct.AIR_AROUND
    
    return device_model

# get connected sensors
connected_sensors = get_connected_sensors()
battery_monitor = get_battery_monitor()

# auto detect model if model=-1
if Config.settings['MODEL'] == -1:
    Config.settings['MODEL'] = get_model_id_from_sensors(connected_sensors, battery_monitor)

# prepare connected sensors status for ble 
connected_sensors_status = bytearray([
    len(connected_sensors),  # Number of sensors
])

# list of sensors -> is passed to the model
sensors = []

# add connected sensors
for name in connected_sensors:
    connected_sensors_status.extend([
            name,
            0x01,  # Connected
        ])
    sensors.append(connected_sensors[name])

# Initialize BLE, define custom service
ble = BLERadio()
service = LdService()

# init ble name
ble.name = "Luftdaten.at-" + Config.settings['mac']

# init led controller
led_controller = LedController(status_led, 5 if Config.settings['MODEL'] == LdProduct.AIR_CUBE else 1)

device = None
if Config.settings['MODEL'] == LdProduct.AIR_AROUND or Config.settings['MODEL'] == LdProduct.AIR_BADGE or Config.settings['MODEL'] == LdProduct.AIR_BIKE:
    from models.ld_portable import LdPortable
    device = LdPortable(Config.settings['MODEL'], service, sensors, battery_monitor, led_controller)
if Config.settings['MODEL'] == LdProduct.AIR_CUBE:
    from models.air_cube import AirCube
    device = AirCube(service, sensors, battery_monitor, led_controller)
if Config.settings['MODEL'] == LdProduct.AIR_STATION:
    from models.air_station import AirStation
    device = AirStation(service, sensors, battery_monitor, led_controller)

# bad Model was not recognised
if device is None:
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
    Config.settings['PROTOCOL_VERSION'],
    Config.settings['FIRMWARE_MAJOR'],
    Config.settings['FIRMWARE_MINOR'],
    Config.settings['FIRMWARE_PATCH'],
    # Device Name (e.g. F001). To be retrieved from Datahub, otherwise use 0x00 0x00 0x00 0x00
    0x00, 0x00, 0x00, 0x00,  # Not yet implemented
    Config.settings['MODEL'],  # Device model (e.g. AIR_AROUND)
])

# set characteristics
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
if battery_monitor is not None:  # First none should be battery_monitor
    service.device_status_characteristic = bytes([
        1,  # Has battery status: Yes
        round(battery_monitor.cell_soc()),  # Battery percentage
        round(battery_monitor.cell_voltage() * 10),  # Battery voltage
        0,  # Error status: 0 = no error
    ])
else:
    service.device_status_characteristic = bytes([
        0,  # Has battery status: No
        0, 0,  # Battery percentage, voltage
        0,  # Error status: 0 = no error
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
            if percent > point:
                status_led.fill(Color.GREEN)
                status_led.show()
                time.sleep(0.5)
                status_led.fill(Color.OFF)
                status_led.show()
                time.sleep(0.5)
    time.sleep(2)

button_state = False

device.connection_update(False)

ble_connected = False

# Main loop
while True:
    # Clean memory
    gc.collect()

    if not WifiUtil.radio.connected:
        WifiUtil.connect()

    # Check for updates
    if WifiUtil.radio.connected:
        print(f'{Ugm.check_if_upgrade_available()=}')
        print(f'{Ugm.get_latest_firmware_version()=}')

        if Ugm.check_if_upgrade_available():
            import supervisor
            supervisor.set_next_code_file('code.py')
            supervisor.reload()

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
