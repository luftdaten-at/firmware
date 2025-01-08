from sensors.sensor import Sensor
from enums import SensorModel, Dimension


class VirtualSensor(Sensor):
    def __init__(self, *args, **kwargs):
        '''
        pass all needed sensor for calculation 
        '''
        super().__init__()
        self.model_id = SensorModel.VIRTUAL_SENSOR
        
        self.current_values: dict[Dimension, float] = None

    def read(self) -> None:
        '''
        recalculate all current_values
        '''
        pass
