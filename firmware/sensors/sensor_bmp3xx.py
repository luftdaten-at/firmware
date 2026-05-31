from sensors.sensor import Sensor
from sensors.sensor_bmp3xx_common import (
    BMP388_CHIP_ID,
    BMP390_CHIP_ID,
    probe_bmp3xx,
)
from enums import Dimension, SensorModel, Quality
from logger import logger


class Bmp3xxSensor(Sensor):
    """Single probe for BMP388 (CHIP_ID 0x50) or BMP390 (CHIP_ID 0x60)."""

    def __init__(self):
        super().__init__()
        self.model_id = None
        self.measures_values = [
            Dimension.TEMPERATURE,
            Dimension.PRESSURE,
            Dimension.ALTITUDE,
        ]
        self.current_values = {
            Dimension.TEMPERATURE: None,
            Dimension.PRESSURE: None,
            Dimension.ALTITUDE: None,
        }
        self.value_quality = {
            Dimension.TEMPERATURE: Quality.HIGH,
            Dimension.PRESSURE: Quality.HIGH,
            Dimension.ALTITUDE: Quality.HIGH,
        }

    def attempt_connection(self, i2c):
        result = probe_bmp3xx(i2c)
        if result is None:
            logger.debug("Bmp3xx sensor not detected")
            return False

        chip_id, self.bmp, address = result
        if chip_id == BMP388_CHIP_ID:
            self.model_id = SensorModel.BMP388
            name = "Bmp388"
        elif chip_id == BMP390_CHIP_ID:
            self.model_id = SensorModel.BMP390
            name = "Bmp390"
        else:
            return False

        logger.debug(
            "%s device found on I2C at 0x%02x (CHIP_ID=0x%02x)"
            % (name, address, chip_id)
        )
        return True

    def read(self):
        try:
            self.current_values = {
                Dimension.TEMPERATURE: self.bmp.temperature,
                Dimension.PRESSURE: self.bmp.pressure,
                Dimension.ALTITUDE: self.bmp.altitude,
            }
        except Exception:
            logger.error("Bmp3xx read error (model_id=%s)" % self.model_id)
