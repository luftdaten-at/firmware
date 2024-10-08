class Dimension():
    PM0_1 = 1
    PM1_0 = 2
    PM2_5 = 3
    PM4_0 = 4
    PM10_0 = 5
    HUMIDITY = 6
    TEMPERATURE = 7
    VOC_INDEX = 8
    NOX_INDEX = 9
    PRESSURE = 10
    CO2 = 11
    O3 = 12
    AQI = 13
    GAS_RESISTANCE = 14
    TVOC = 15
    NO2 = 16
    SGP40_RAW_GAS = 17
    SGP40_ADJUSTED_GAS = 18
    
class SensorModel():
    SEN5X = 1
    BMP280 = 2
    BME280 = 3
    BME680 = 4
    SCD4X = 5
    AHT20 = 6
    SHT30 = 7
    SHT31 = 8
    AGS02MA = 9
    SHT4X = 10
    SGP40 = 11
    
class LdProduct():
    AIR_AROUND = 1
    AIR_CUBE = 2
    AIR_STATION = 3
    AIR_BADGE = 4
    AIR_BIKE = 5
    
class Color():
    # LED colors. Found experimentally, they do not correspond to accurate RGB values.
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    GREEN_LOW = (0, 50, 0)
    BLUE = (0, 0, 255)
    YELLOW = (255, 100, 0)
    CYAN = (0, 255, 50)
    MAGENTA = (255, 0, 20)
    WHITE = (255, 150, 40)
    ORANGE = (255, 70, 0)
    PURPLE = (200, 0, 80)
    OFF = (0, 0, 0)
    
    def with_brightness(color, brightness):
        return tuple([int(x * brightness) for x in color])

class Quality():
    HIGH = 1
    LOW = 2

class BleCommands:
    READ_SENSOR_DATA = 0x01
    READ_SENSOR_DATA_AND_BATTERY_STATUS = 0x02
    UPDATE_BRIGHTNESS = 0x03 
    TURN_OFF_STATUS_LIGHT = 0x04
    TURN_ON_STATUS_LIGHT = 0x05
    SET_AIR_STATION_CONFIGURATION = 0x06

class AirstationConfigFlags:
    AUTO_UPDATE_MODE = 0  # Bit 0
    BATTERY_SAVE_MODE = 1  # Bit 1
    MEASUREMENT_INTERVAL = 2  # Bit 2
    LONGITUDE = 3  # Bit 3
    LATITUDE = 4  # Bit 4
    HEIGHT = 5  # Bit 5
    SSID = 6  # Bit 6
    PASSWORD = 7  # Bit 7
    DEVICE_ID = 8

class AirStationMeasurementInterval:
    sec30 = 30
    min1 = 60
    min3 = 180
    min5 = 300
    min10 = 600
    min15 = 900
    min30 = 1800
    h1 = 3600

class AutoUpdateMode:
    off = 0
    critical = 2
    on = 3
    
class BatterySaverMode:
    off = 0
    normal = 1
    ultra = 3
