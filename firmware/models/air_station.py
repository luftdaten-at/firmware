from models.ld_product_model import LdProductModel
from enums import LdProduct, Color

class AirStation(LdProductModel): 
    def __init__(self, ble_service, sensors, battery_monitor, status_led):
        super().__init__(ble_service, sensors, battery_monitor, status_led)
        self.polling_interval = 0.1  # TODO is this the best value?
        self.model_id = LdProduct.AIR_STATION
        self.ble_on = False
        
    def receive_command(self, command):
        if(len(command) == 0):
            return
        # We should use this for sending configuration commands to the device
    
    def receive_button_press(self):
        self.ble_on = not self.ble_on
        # Possibly change polling interval?
        if self.ble_on:
            self.status_led.fill(Color.BLUE)
        else:
            self.status_led.fill(Color.OFF)
        self.status_led.show()
    
    def tick(self):
        pass
        # We measure in fixed intervals, do this here
        
    def connection_update(self, connected):
        pass