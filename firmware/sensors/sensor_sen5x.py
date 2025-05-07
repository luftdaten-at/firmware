from sensirion_i2c_sen5x import Sen5xI2cDevice # type: ignore
from sensirion_i2c_driver import I2cTransceiver,I2cConnection # type: ignore
from sensors.sensor import Sensor
from enums import Dimension, SensorModel, Quality
import time
from logger import logger

SEN5X_DEFAULT_ADDRESS = 0x69

class Sen5xSensor(Sensor):
    # Argument: empty if model unknown, 4 for Sen54, 5 for Sen55
    def __init__(self, *args):
        super().__init__()
        self.model_id = SensorModel.SEN5X
        
        self.is_sen54 = False
        if args:
            if args[0]:
                self.is_sen54 = True
        
        self.measures_values = [
            Dimension.PM1_0,
            Dimension.PM2_5,
            Dimension.PM4_0,
            Dimension.PM10_0,
            Dimension.TEMPERATURE,
            Dimension.HUMIDITY,
            Dimension.VOC_INDEX,
        ]
        if not self.is_sen54:
            self.measures_values.append(Dimension.NOX_INDEX)
        self.current_values = {
            Dimension.PM1_0: None,
            Dimension.PM2_5: None,
            Dimension.PM4_0: None,
            Dimension.PM10_0: None,
            Dimension.TEMPERATURE: None,
            Dimension.HUMIDITY: None,
            Dimension.VOC_INDEX: None,
        }
        if not self.is_sen54:
            self.current_values[Dimension.NOX_INDEX] = None
        self.value_quality = {
            Dimension.PM1_0: Quality.HIGH,
            Dimension.PM2_5: Quality.HIGH,
            Dimension.PM4_0: Quality.HIGH,
            Dimension.PM10_0: Quality.HIGH,
            Dimension.TEMPERATURE: Quality.LOW,
            Dimension.HUMIDITY: Quality.LOW,
            Dimension.VOC_INDEX: Quality.HIGH,
            Dimension.NOX_INDEX: Quality.HIGH,
        }
    
    def get_serial_number(self):
        return str(self.sen5x_device.get_serial_number())
        
    def attempt_connection(self, i2c):
        try:
            transceiver = I2cTransceiver(i2c, SEN5X_DEFAULT_ADDRESS)
            self.sen5x_device = Sen5xI2cDevice(I2cConnection(transceiver))
        except (OSError,ValueError):
            logger.debug("SEN5x sensor not detected")
            return False

        logger.debug("SEN5x initialised, resetting, waiting 1.1 seconds before read")
        self.sen5x_device.device_reset()
        time.sleep(1.1)
        logger.debug(f"SEN5x device found on I2C bus {i2c}, product type: {self.sen5x_device.get_product_name()}, #{self.sen5x_device.get_serial_number()}")
        self.sensor_details = bytearray([
            self.sen5x_device.get_version().firmware.major,
            self.sen5x_device.get_version().firmware.minor,
            self.sen5x_device.get_version().hardware.major,
            self.sen5x_device.get_version().hardware.minor,
            self.sen5x_device.get_version().protocol.major,
            self.sen5x_device.get_version().protocol.minor,
        ])
        self.sensor_details.extend(self.sen5x_device.get_serial_number().encode('ascii'))
        self.sen5x_device.start_measurement()
        self.is_sen54 = self.sensor_details[2] == 4
        return True

    def read(self):
        try:
            sen5x_data = self.sen5x_device.read_measured_values()
            self.current_values = {
                Dimension.PM1_0: sen5x_data.mass_concentration_1p0.physical,
                Dimension.PM2_5: sen5x_data.mass_concentration_2p5.physical,
                Dimension.PM4_0: sen5x_data.mass_concentration_4p0.physical,
                Dimension.PM10_0: sen5x_data.mass_concentration_10p0.physical,
                Dimension.TEMPERATURE: sen5x_data.ambient_temperature.degrees_celsius,
                Dimension.HUMIDITY: sen5x_data.ambient_humidity.percent_rh,
                Dimension.VOC_INDEX: sen5x_data.voc_index.scaled,
            }
            if not self.is_sen54:
                self.current_values[Dimension.NOX_INDEX] = sen5x_data.nox_index.scaled
        except:
            logger.error("Error reading SEN5x sensor data")
