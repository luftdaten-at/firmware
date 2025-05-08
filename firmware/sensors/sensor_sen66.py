from sensirion_i2c_sen66.device import Sen66Device  # type: ignore
from sensirion_i2c_driver import I2cTransceiver, I2cConnection, CrcCalculator  # type: ignore
from sensirion_driver_adapters.i2c_adapter.i2c_channel import I2cChannel  # type: ignore
from sensors.sensor import Sensor
from enums import Dimension, SensorModel, Quality
import time
from logger import logger

SEN66_DEFAULT_ADDRESS = 0x6B

class Sen66Sensor(Sensor):
    def __init__(self):
        super().__init__()
        self.model_id = SensorModel.SEN66
        self.current_values = {
            Dimension.PM1_0: None,
            Dimension.PM2_5: None,
            Dimension.PM4_0: None,
            Dimension.PM10_0: None,
            Dimension.TEMPERATURE: None,
            Dimension.HUMIDITY: None,
            Dimension.VOC_INDEX: None,
            Dimension.NOX_INDEX: None,
            Dimension.CO2: None,
        }
        self.measures_values = list(self.current_values.keys())
        self.value_quality = {
            Dimension.PM1_0: Quality.HIGH,
            Dimension.PM2_5: Quality.HIGH,
            Dimension.PM4_0: Quality.HIGH,
            Dimension.PM10_0: Quality.HIGH,
            Dimension.TEMPERATURE: Quality.LOW,
            Dimension.HUMIDITY: Quality.LOW,
            Dimension.VOC_INDEX: Quality.HIGH,
            Dimension.NOX_INDEX: Quality.HIGH,
            Dimension.CO2: Quality.MEDIUM,
        }

    def get_serial_number(self):
        return str(self.sen66_device.get_serial_number())

    def attempt_connection(self, i2c):
        try:
            transceiver = I2cTransceiver(i2c, SEN66_DEFAULT_ADDRESS)
            channel = I2cChannel(
                I2cConnection(transceiver),
                slave_address=SEN66_DEFAULT_ADDRESS,
                crc=CrcCalculator(8, 0x31, 0xff, 0x0)
            )
            self.sen66_device = Sen66Device(channel)
        except (OSError, ValueError):
            logger.debug("SEN66 sensor not detected")
            return False

        logger.debug("SEN66 initialised, resetting, waiting 1 second before read")
        self.sen66_device.device_reset()
        time.sleep(1.0)

        serial = self.sen66_device.get_serial_number()
        version = self.sen66_device.get_version()  # returns (major, minor)

        logger.debug(f"SEN66 device found on I2C bus {i2c}, version: {version}, serial: {serial}")

        self.sensor_details = bytearray([
            version[0],  # firmware major
            version[1],  # firmware minor
        ])
        self.sensor_details.extend(serial.encode('ascii'))

        self.sen66_device.start_continuous_measurement()
        return True

    def read(self):
        try:
            (
                pm1,
                pm2_5,
                pm4,
                pm10,
                humidity,
                temperature,
                voc,
                nox,
                co2
            ) = self.sen66_device.read_measured_values()

            self.current_values = {
                Dimension.PM1_0: pm1.value,
                Dimension.PM2_5: pm2_5.value,
                Dimension.PM4_0: pm4.value,
                Dimension.PM10_0: pm10.value,
                Dimension.HUMIDITY: humidity.value,
                Dimension.TEMPERATURE: temperature.value,
                Dimension.VOC_INDEX: voc.value,
                Dimension.NOX_INDEX: nox.value,
                Dimension.CO2: co2.value,
            }
        except Exception as e:
            logger.error(f"Error reading SEN66 sensor data: {e}")
