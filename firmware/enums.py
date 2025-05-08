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
    DHT22 = 12
    SDS011 = 13
    SHT35 = 14
    SPS30 = 15
    PMS5003 = 16
    PMS7003 = 17
    VIRTUAL_SENSOR = 18
    LTR390 = 19
    BMP388 = 20
    BMP390 = 21
    LSM6DS = 22
    SEN66 = 23
    MLX90640 = 24
    TSL2591 = 25

    _names = {
        SEN5X: "SEN5X",
        BMP280: "BMP280",
        BME280: "BME280",
        BME680: "BME680",
        SCD4X: "SCD4X",
        AHT20: "AHT20",
        SHT30: "SHT30",
        SHT31: "SHT31",
        AGS02MA: "AGS02MA",
        SHT4X: "SHT4X",
        SGP40: "SGP40",
        DHT22: "DHT22",
        SDS011: "SDS011",
        SHT35: "SHT35",
        SPS30: "SPS30",
        PMS5003: "PMS5003",
        PMS7003: "PMS7003",
        VIRTUAL_SENSOR: "VIRTUAL_SENSOR",
        LTR390: "LTR390",
        BMP388: "BMP388",
        BMP390: "BMP390",
        LSM6DS: "lsm6ds",
        SEN66: "SEN66",
        MLX90640: "MLX90640",
        TSL2591: "TSL_2591",
    }

    _manufacturer = {
        SEN5X: "Sensirion",
        BMP280: "Bosch Sensortec",
        BME280: "Bosch Sensortec",
        BME680: "Bosch Sensortec",
        SCD4X: "Sensirion",
        AHT20: "ASAIR",
        SHT30: "Sensirion",
        SHT31: "Sensirion",
        AGS02MA: "ASAIR",
        SHT4X: "Sensirion",
        SGP40: "Sensirion",
        DHT22: "ASAIR",
        SDS011: "Nova Fitness",
        SHT35: "Sensirion",
        SPS30: "Sensirion",
        PMS5003: "Plantower",
        PMS7003: "Plantower",
        VIRTUAL_SENSOR: "Luftdaten.at",
        SEN66: "Sensirion",
        MLX90640: "Mouser Electronics", 
        TSL2591: "Berry Base",
    }

    _pins = {
        PMS5003: 1,
        PMS7003: 1,
        SDS011: 1,
        SPS30: 1,
        BME280: 11,
        BME680: 11,
        BMP280: 3,
        DHT22: 7,
        SHT30: 7,
        SHT31: 7,
        SHT35: 7,
        SHT4X: 7,
        SEN5X: 16
    }

    @classmethod
    def get_pin(cls, model_id: str):
        return cls._pins[model_id]

    @classmethod
    def get_sensor_name(cls, sensor_model):
        return cls._names.get(sensor_model, "Unknown Sensor")

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
    ADJUSTED_TEMP_CUBE = 19
    UVS = 20
    LIGHT = 21
    ALTITUDE = 22
    UVI = 23
    LUX = 24
    ACCELERATION_X = 25
    ACCELERATION_Y = 26
    ACCELERATION_Z = 27
    GYRO_X = 28
    GYRO_Y = 29
    GYRO_Z = 30
    THERMAL_ARRAY = 31
    VISIBLE = 32
    INFRARED = 33
    FULL_SPECTRUM = 34
    RAW_LUMINOSITY = 35

    thresholds = {
        TEMPERATURE: ([18, 24], [Color.BLUE, Color.GREEN, Color.RED]),
        PM2_5: ([5, 15], [Color.GREEN, Color.YELLOW, Color.RED]),
        TVOC: ([220, 1430], [Color.GREEN, Color.YELLOW, Color.RED]),
        CO2: ([800, 1000, 1400], [Color.GREEN, Color.YELLOW, Color.ORANGE, Color.RED]),
        ADJUSTED_TEMP_CUBE: ([18, 24], [Color.BLUE, Color.GREEN, Color.RED]),
        UVI: ([3, 6, 8, 11], [Color.GREEN, Color.YELLOW, Color.ORANGE, Color.RED, Color.PURPLE])
    }

    # Dictionary für die Einheiten der Dimensionen
    _units = {
        PM0_1: "µg/m³",
        PM1_0: "µg/m³",
        PM2_5: "µg/m³",
        PM4_0: "µg/m³",
        PM10_0: "µg/m³",
        HUMIDITY: "%",
        TEMPERATURE: "°C",
        VOC_INDEX: "Index",
        NOX_INDEX: "Index",
        PRESSURE: "hPa",
        CO2: "ppm",
        O3: "ppb",
        AQI: "Index",
        GAS_RESISTANCE: "Ω",
        TVOC: "ppb",
        NO2: "ppb",
        SGP40_RAW_GAS: "Ω",
        SGP40_ADJUSTED_GAS: "Ω",
        ADJUSTED_TEMP_CUBE: "°C",
        ACCELERATION_X: "m/s²",
        ACCELERATION_Y: "m/s²",
        ACCELERATION_Z: "m/s²",
        GYRO_X: "radians/s",
        GYRO_Y: "radians/s",
        GYRO_Z: "radians/s",
        UVI: "UV Index",
        LUX: "lx"
    }

    _names = {
        PM0_1: "PM0.1",
        PM1_0: "PM1.0",
        PM2_5: "PM2.5",
        PM4_0: "PM4.0",
        PM10_0: "PM10.0",
        HUMIDITY: "Humidity",
        TEMPERATURE: "Temperature",
        VOC_INDEX: "VOC Index",
        NOX_INDEX: "NOx Index",
        PRESSURE: "Pressure",
        CO2: "CO2",
        O3: "Ozone (O3)",
        AQI: "Air Quality Index (AQI)",
        GAS_RESISTANCE: "Gas Resistance",
        TVOC: "Total VOC",
        NO2: "Nitrogen Dioxide (NO2)",
        SGP40_RAW_GAS: "SGP40 Raw Gas",
        SGP40_ADJUSTED_GAS: "SGP40 Adjusted Gas",
        ADJUSTED_TEMP_CUBE: "Adjusted Temperature Air Cube",
        UVS: "UVS",
        LIGHT: "Light",
        ACCELERATION_X: "acceleration X",
        ACCELERATION_Y: "acceleration Y",
        ACCELERATION_Z: "acceleration Z",
        GYRO_X: "gyro X",
        GYRO_Y: "gyro Y",
        GYRO_Z: "gyro Z",
        UVI: "UV Index",
        LUX: "Lux",
        THERMAL_ARRAY: "Thermal Image",
    }

    _required_sensors = {
        ADJUSTED_TEMP_CUBE: set([SensorModel.SHT4X, SensorModel.SEN5X])
    }

    _sensor_community_names = {
        PM0_1: "P01",
        PM1_0: "P1",
        PM2_5: "P2",
        PM4_0: "P4",
        PM10_0: "P10",
        HUMIDITY: "humidity",
        TEMPERATURE: "temperature",
        PRESSURE: "pressure",
        CO2: "co2_ppm",
        O3: "ozone_ppb",
        TVOC: "tvoc",
        NO2: "no2_ppb",
    }

    @classmethod
    def get_required_sensors(cls, dimension_id: int) -> set[SensorModel]:
        return cls._required_sensors.get(dimension_id, None)

    @classmethod
    def get_unit(cls, dimension_id: int) -> str:
        """
        Gibt die Einheit der angegebenen Dimension zurück.
        :param dimension_id: Die ID der Dimension
        :return: Die zugehörige Einheit oder 'Unknown', wenn keine Einheit vorhanden ist
        """
        return cls._units.get(dimension_id, "Unknown")

    @classmethod
    def get_name(cls, dimension_id: int) -> str:
        """
        Gibt den Namen der angegebenen Dimension zurück.
        :param dimension_id: Die ID der Dimension
        :return: Der zugehörige Name oder 'Unknown', wenn kein Name vorhanden ist
        """
        return cls._names.get(dimension_id, "Unknown")
    
    @classmethod
    def get_sensor_community_name(cls, dimension_id: int) -> str:
        """Returns the sensor-community-specific name for the dimension ID or 'Unknown' if none."""
        return cls._sensor_community_names.get(dimension_id, "Unknown")

    @classmethod
    def get_color(cls, dimension_id: int, val: float):
        th, colors = cls.thresholds.get(dimension_id)
        th = [-float('inf')] + th + [float('inf')]
        for i in range(len(th)):
            if th[i] <= val < th[i + 1]:
                return colors[i]


class LdProduct():
    AIR_AROUND = 1
    AIR_CUBE = 2
    AIR_STATION = 3
    AIR_BADGE = 4
    AIR_BIKE = 5
    

class Quality():
    HIGH = 1
    LOW = 2
    MEDIUM = 3

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
