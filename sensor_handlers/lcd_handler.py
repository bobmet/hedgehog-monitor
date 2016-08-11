import threading
import Queue
import logging

logger = logging.getLogger('hh')


class DataReportingThread(threading.Thread):
    def __init__(self, run_event, queue, lcd, version_msg):
        threading.Thread.__init__(self)

        self.run_event = run_event
        self.queue = queue

        # Initialize some default values
        self.sensor_data = {"temp_f": 0,
                            "temp_c": 0,
                            "humidity": 0,
                            "lux": 0}
        self.lcd = lcd

        self.backlight_status = False

        self.message_list = list()
        self.current_message_num = 0

        self.timeout_length = 5
        self.loop_sleep = 0.001

        self.version_msg = version_msg
        self.lcd.message(self.version_msg)

    def run(self):
        timeout_counter = 0

        while self.run_event.is_set():
            try:
                timeout_counter += self.loop_sleep

                if timeout_counter >= self.timeout_length:
                    if self.backlight_status is True:
                        self.lcd.set_backlight(1)
                        self.backlight_status = False
                    timeout_counter = 0

                data = self.queue.get(True, self.loop_sleep)

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
                        self.update_lcd()
                        timeout_counter = 0

                    logger.info("LCD THREAD:  {0}".format(self.sensor_data))
#                    self.update_lcd()

            except Queue.Empty:
                # The queue.get with a timeout throws a Queue.Empty exception. Just continue if that happens
                continue

        logger.info("Thread {0} closing".format(threading.currentThread().name))

    def toggle_backlight(self):
        backlight_set = 0 if self.backlight_status is True else 1
        self.lcd.set_backlight(backlight_set)
        self.backlight_status = not self.backlight_status

    def update_lcd(self):
        if self.backlight_status is False:
            self.backlight_status = True
            self.lcd.set_backlight(0)
        else:
            if self.current_message_num == 0:
                message = self.version_msg
            elif self.current_message_num == 1:
                message = "{0}{1}{2} {3}%\n{4} lux".format(self.sensor_data['temp_f'],
                                                           chr(223),
                                                           "F",
                                                           self.sensor_data['humidity'],
                                                           self.sensor_data['lux'])
            elif self.current_message_num == 2:
                message = "Message #3"

            elif self.current_message_num == 3:
                message = "Message #4 ABCD\nS'more monitor"

            self.lcd.clear()
            self.lcd.message(message)

            self.current_message_num += 1
            if self.current_message_num > 3:
                self.current_message_num  = 0

#        logger.info(message)
