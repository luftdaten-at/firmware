import time

from logger import logger
from enums import SensorModel, LdProduct

def get_connected_sensors(i2c):
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
                logger.info(f'Found sensor: {sensor.model_id}')
                connected_sensors[sensor.model_id] = sensor

        return connected_sensors


def get_battery_monitor(i2c):
        # Try to connect to battery sensor, as that is part of criteria
        from sensors.max17048 import MAX17048
        battery_monitor = None
        for i in range(10):
            try:
                battery_monitor = MAX17048(i2c)
                logger.info(f'Attempt {i + 1}: Battery monitor initialized')
                break
            except:
                pass
            logger.info("Waiting 0.5 seconds before retrying battery monitor initialization")
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