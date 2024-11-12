import time
from enums import BleCommands, Color
from logger import logger

class LedController:
    BRIGHTNESS_LEVELS = [1/5, 2/5, 3/5, 4/5, 1]

    def __init__(self, status_led, n):
        self.n = n 
        self.status_led = status_led
        self.default_pattern = [None] * n
        self.pattern_queue = [[] for _ in range(n)] 
         
    def tick(self):
        for i in range(self.n):
            if not self.pattern_queue[i]:
                if self.default_pattern[i]:
                    d = self.default_pattern[i]
                    d['repeat_times'] = 1
                    self.pattern_queue[i].append(d)
                else:
                    # no pattern found
                    continue
            if self.pattern_queue[i]:
                # execute pattern
                pattern = self.pattern_queue[i][0]
                pointer = pattern.get('pointer', 0)

                start_time = pattern.get(f'{pointer}_start_time', time.monotonic())
                pattern[f'{pointer}_start_time'] = start_time

                cur = pattern['elements'][pointer % len(pattern['elements'])]
                self._show_led(cur['color'], i)

                if time.monotonic() >= start_time + cur['duration']:
                    pointer += 1
                
                pattern['pointer'] = pointer

                cur = pattern['elements'][pointer % len(pattern['elements'])]
                self._show_led(cur['color'], i)

                if pointer // len(pattern['elements']) >= pattern['repeat_times']:
                    self.pattern_queue[i] = self.pattern_queue[i][1:]
                else:
                    self.pattern_queue[i][0] = pattern
    
    def show_led(self, pattern, led_id = 0):
        if pattern['repeat_mode'] == RepeatMode.FOREVER:
            self.default_pattern[led_id] = pattern
        elif pattern['repeat_mode'] == RepeatMode.PERMANENT:
            pattern['elements'] = [{'color': pattern['color'], 'duration': float('inf')}]
            self.default_pattern[led_id] = pattern
        else:
            self.pattern_queue[led_id].append(pattern)
            
    def _show_led(self, color, led_id = 0):
        self.status_led[led_id] = color
        self.status_led.show()
    
    def set_brightness(self, level):
        self.status_led.brightness = LedController.BRIGHTNESS_LEVELS[level]
    
    def receive_command(self, command):
        if not command:
            return
        cmd = command[0]
        if cmd == BleCommands.UPDATE_BRIGHTNESS:
            self.set_brightness(command[1])
        elif cmd == BleCommands.TURN_OFF_STATUS_LIGHT:
            self.turn_off_led()
        elif cmd == BleCommands.TURN_ON_STATUS_LIGHT:
            self.turn_on_led()

class RepeatMode:
    '''
    {
        "repeat_mode": [mode],
        "elements": [
            {"color": [color], "duration": [duration]},
            ...
        ]
        # if mode == TIMES
        "repeat_times": [int],

    } 
    '''
    FOREVER = 0
    TIMES = 1
    PERMANENT = 2
