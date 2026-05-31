from sensors.sensor_bmp3xx import Bmp3xxSensor
from sensors.sensor_bmp3xx_common import BMP390_CHIP_ID, probe_bmp3xx
from enums import SensorModel
from logger import logger


class Bmp390Sensor(Bmp3xxSensor):
    """BMP390 only (CHIP_ID 0x60). Prefer Bmp3xxSensor in sensor scan."""

    def __init__(self):
        super().__init__()
        self.model_id = SensorModel.BMP390

    def attempt_connection(self, i2c):
        result = probe_bmp3xx(i2c)
        if result is None:
            logger.debug("Bmp390 sensor not detected")
            return False
        chip_id, self.bmp, address = result
        if chip_id != BMP390_CHIP_ID:
            logger.debug(
                "Bmp390 probe: CHIP_ID=0x%02x at 0x%02x (expected 0x%02x)"
                % (chip_id, address, BMP390_CHIP_ID)
            )
            return False
        logger.debug(
            "Bmp390 device found on I2C at 0x%02x (CHIP_ID=0x%02x)"
            % (address, chip_id)
        )
        return True
