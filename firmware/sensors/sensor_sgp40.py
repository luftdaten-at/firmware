import adafruit_sgp40 # type: ignore
from sensors.sensor import Sensor
from enums import Dimension, SensorModel, Quality
from logger import logger

class Sgp40Sensor(Sensor):
    def __init__(self):
        super().__init__()
        self.model_id = SensorModel.SGP40
        self.measures_values = [
            Dimension.VOC_INDEX,
            Dimension.SGP40_RAW_GAS,
            Dimension.SGP40_ADJUSTED_GAS,
        ]
        self.current_values = {
            Dimension.VOC_INDEX: None,
            Dimension.SGP40_RAW_GAS: None,
            Dimension.SGP40_ADJUSTED_GAS: None,
        }
        self.value_quality = {
            Dimension.VOC_INDEX: Quality.HIGH,
            Dimension.SGP40_RAW_GAS: Quality.HIGH,
            Dimension.SGP40_ADJUSTED_GAS: Quality.HIGH,
        }
        self.temperature_provider = None
        
    def attempt_connection(self, i2c):
        try:
            self.sgp40_device = adafruit_sgp40.SGP40(i2c)
        except:
            logger.debug("SGP40 sensor not detected")
            return False

        logger.debug(f"SGP40 device found on I2C bus {i2c}")
        return True
    
    def on_start_main_loop(self, device):
        # Link with SHT3/4X sensor
        for sensor in device.sensors:
            if sensor.model_id in [SensorModel.SHT4X, SensorModel.SHT30, SensorModel.SHT31]:
                self.temperature_provider = sensor
                logger.debug('Linked SGP40 with sensor model ', sensor.model_id)
                return
        logger.debug('No temperature sensor found for SGP40')

    def read(self):
        try:
            if self.temperature_provider is not None:
                provided_temperature = self.temperature_provider.current_values[Dimension.TEMPERATURE]
                provided_humidity = self.temperature_provider.current_values[Dimension.HUMIDITY]
                if provided_temperature is None or provided_humidity is None:
                    logger.debug('Expected temperature and humidity from linked sensor, but got None.')
                else:
                    self.current_values = {
                        Dimension.VOC_INDEX: self.sgp40_device.measure_index(temperature=provided_temperature, relative_humidity=provided_humidity),
                        Dimension.SGP40_RAW_GAS: self.sgp40_device.raw,
                        Dimension.SGP40_ADJUSTED_GAS: self.sgp40_device.measure_raw(temperature=provided_temperature, relative_humidity=provided_humidity),
                    }
                    return
            self.current_values = {
                Dimension.VOC_INDEX: self.sgp40_device.measure_index(), # Uses default temperature and humidity
                Dimension.SGP40_RAW_GAS: self.sgp40_device.raw,
                Dimension.SGP40_ADJUSTED_GAS: self.sgp40_device.measure_raw(),
            }
        except:
            logger.error("SGP40 Error")
