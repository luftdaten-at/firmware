from sensors.sensor import Sensor
from enums import SensorModel, Dimension


class VirtualSensor(Sensor):
    def __init__(self, sensors: list[Sensor], dimensions: set[Dimension]) -> None:
        '''
        sensors: list of sensors requierd to calculate requested dimensions
        dimensions: dimensions that should be calculated
        '''
        super().__init__()

        self.model_id = SensorModel.VIRTUAL_SENSOR
        self.dimensions = dimensions        
        self.current_values: dict[Dimension, float] = None

    def read(self) -> None:
        '''
        recalculate all current_values
        '''
        
        pass
