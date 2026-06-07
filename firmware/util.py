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
        from sensors.sensor_shtc3 import Shtc3Sensor
        from sensors.sensor_sgp40 import Sgp40Sensor
        from sensors.sensor_bmp3xx import Bmp3xxSensor
        from sensors.sensor_bmp581 import Bmp581Sensor
        from sensors.sensor_ltr390 import Ltr390Sensor
        from sensors.sensor_lsm6ds import Lsm6dsSensor
        from sensors.sensor_sen62 import Sen62Sensor
        from sensors.sensor_sen63c import Sen63cSensor
        from sensors.sensor_sen66 import Sen66Sensor
        from sensors.sensor_mlx90640 import Mlx90640Sensor
        from sensors.sensor_tsl2591 import Tsl2591Sensor

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
            Shtc3Sensor(),
            Sgp40Sensor(),
            Bmp3xxSensor(),
            Bmp581Sensor(),
            Ltr390Sensor(),
            Lsm6dsSensor(),
            Sen62Sensor(),
            Sen63cSensor(),
            Sen66Sensor(),
            Mlx90640Sensor(),
            Tsl2591Sensor(),
        ]

        connected_sensors = {}

        for sensor in defined_sensors:
            if sensor.attempt_connection(i2c):
                logger.info(f'Found sensor: {sensor.model_id}')
                connected_sensors[sensor.model_id] = sensor

        if connected_sensors:
            nums = sorted(connected_sensors.keys())
            logger.info(
                "Sensor scan: %d connected — %s"
                % (len(nums), ", ".join(str(mid) for mid in nums))
            )
        else:
            logger.info("Sensor scan: no sensors connected")

        return connected_sensors


def log_sensors_startup_summary(sensors, battery_monitor):
    """Log a single startup block: battery monitor + each sensor by model number and serial."""
    parts = []
    if battery_monitor is not None:
        try:
            pct = round(battery_monitor.cell_soc())
            volts = battery_monitor.cell_voltage()
            parts.append("Battery: OK (%d%%, %.2fV)" % (pct, volts))
        except Exception as e:
            parts.append("Battery: present (%s)" % e)
    else:
        parts.append("Battery: none")

    if not sensors:
        parts.append("sensors: none")
    else:
        detail = []
        for s in sorted(sensors, key=lambda x: x.model_id):
            try:
                sn = s.get_serial_number()
            except Exception as e:
                sn = "(%s)" % e
            if sn is None:
                sn = "n/a"
            detail.append("%s serial=%s" % (s.model_id, sn))
        parts.append(
            "sensors (%d): %s" % (len(sensors), "; ".join(detail))
        )

    logger.info("Sensor scan: " + " | ".join(parts))


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
            time.sleep(0.5)
        
        return battery_monitor


def get_model_id_from_sensors(connected_sensors: dict, battery_monitor) -> int:
        # Find correct model
        device_model = -1
        if connected_sensors.get(SensorModel.SCD4X, None):
            device_model = LdProduct.AIR_CUBE
        elif battery_monitor is None:
            device_model = LdProduct.AIR_STATION
        elif not connected_sensors.get(SensorModel.SEN5X, None) and not connected_sensors.get(
            SensorModel.SEN62, None
        ) and not connected_sensors.get(SensorModel.SEN63C, None) and not connected_sensors.get(
            SensorModel.SEN66, None
        ):
            device_model = LdProduct.AIR_BADGE
        else:
            device_model = LdProduct.AIR_AROUND

        return device_model