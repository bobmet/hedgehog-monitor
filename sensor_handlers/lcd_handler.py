import threading
import Queue
import logging

logger = logging.getLogger('hh')

class DataReporter:
    def __init__(self):
        self.sensor_data = None

        self.queue = Queue.Queue

class LCDDisplayThread(threading.Thread):
    def __init__(self, run_event, queue, lcd):
        threading.Thread.__init__(self)

        self.run_event = run_event
        self.queue = queue

        self.sensor_data = {"temp_f": 0,
                            "temp_c": 0,
                            "humidity": 0,
                            "lux": 0}
        self.lcd = lcd

        self.backlight_status = False

    def run(self):

        while self.run_event.is_set():
            try:
                data = self.queue.get(True, 0.001)
                if 'data_type' in data:
                    data_type = data['data_type']
                    if data_type == 'temperature':
                        self.sensor_data['temp_f'] = round(float(data['temp_f']), 1)
                        self.sensor_data['temp_c'] = round(float(data['temp_c']), 1)
                        self.sensor_data['humidity']= round(float(data['humidity']), 1)
                        self.sensor_data['temp_datetime'] = data['datetime']
                    elif data_type == 'light':
                        self.sensor_data['lux'] = data['lux']
                        self.sensor_data['temp_datetime'] = data['datetime']
                    elif data_type == 'button':
                        self.toggle_backlight()

                    logger.info("LCD THREAD:  {0}".format(self.sensor_data))
                    self.update_lcd()

            except Queue.Empty:
                # The queue.get with a timeout throws a Queue.Empty exception. Just continue if that happens
                continue

        logger.info("Thread {0} closing".format(threading.currentThread().name))

    def toggle_backlight(self):
        backlight_set = 0 if self.backlight_status is True else 1
        self.lcd.set_backlight(backlight_set)
        self.backlight_status = not self.backlight_status

    def update_lcd(self):
        message = "{0}{1} {2}%\n{3} lux".format(self.sensor_data['temp_f'],
                                                chr(223),
                                                self.sensor_data['humidity'],
                                                self.sensor_data['lux'])
        self.lcd.clear()
        self.lcd.message(message)
