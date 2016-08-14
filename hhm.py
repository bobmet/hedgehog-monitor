# -*- coding: utf-8 -*-
"""
Created on Thu Jul 14 23:20:03 2016

@author: pi
"""

#import Queue
import datetime
import logging
import math
import threading
from multiprocessing import Process, Queue
import time
import signal
import RPi.GPIO as GPIO

import dht22
import sensor_handlers
import tsl_sensor
from lcd_display import LCDDisplay
from results_writer import ResultsWriter
from sensor_handlers.button_handler import ButtonHandlerThread
from sensor_handlers.data_collection_thread import DataCollectionThread
from sensor_handlers.lcd_handler import DataReportingThread
from sensor_handlers.wheel_counter import WheelCounterThread

__version__ = "0.0.14"


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger('hh')

# --------- User Settings ---------
# Initial State settings
BUCKET_NAME = ":computer: DHT22 Test" 
BUCKET_KEY = "pi0709"
ACCESS_KEY = "VXwJYOQYjG20KhC37EaJgGBdiyh2Ob4f"
# Set the time between checks
MINUTES_BETWEEN_READS = 1
METRIC_UNITS = False
# ---------------------------------



class TemperatureThread(DataCollectionThread):
    def get_data(self):
        humidity, temp = self.sensor_module.get_data()

        data = {'data_type': 'temperature',
                'temp_c': round(float(temp), 2),
                'temp_f': round(float(temp) * 1.8 + 32, 2),
                'humidity': round(float(humidity), 2),
                'datetime': datetime.datetime.now()}

        return data


class LuxThread(DataCollectionThread):
    def get_data(self):
        lux = self.sensor_module.get_data()
        data = {'data_type': 'light',
                'lux': lux,
                'datetime': datetime.datetime.now()}
        return data



class MainLoop:
    def __init__(self):
        self.gpio_setup()
        self.run_event = threading.Event()
        self.queue = Queue()
        self.lcd_queue = Queue()
        self.lcd = LCDDisplay()

        self.version_msg = "S'more Monitor\nv{0}".format(__version__)
        self.wx_file = ResultsWriter(filename='temperature.csv',
                                     fieldnames=['datetime', 'temp_c', 'temp_f', 'humidity'])
        self.lux_file = ResultsWriter(filename='lux.csv', fieldnames=['datetime', 'lux'])
        self.wheel_file = ResultsWriter(filename='wheel.csv',
                                        fieldnames=['datetime', 'distance', 'moving_time', 'revolutions',
                                                    'avg_speed', 'active'])

        return

    def handle_wx_data(self, data):
        logger.info("WX: {0}".format(data))
        self.wx_file.writerow(data)

    def handle_data(self, data):
        logger.info(data)
        self.lux_file.writerow(data)

    def handle_wheel_data(self, data):
        logger.info(data)
        self.wheel_file.writerow(data)

    def gpio_setup(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

    def gpio_cleanup(self):
        GPIO.cleanup()

    def startup(self):
        self.run_event.set()

        dht_led_pin = 22
        dht_data_pin = 4
        GPIO.setup(dht_led_pin, GPIO.OUT)
        dht = dht22.DHT22(data_gpio_pin=dht_data_pin, led_gpio_pin=dht_led_pin)
        tsl = tsl_sensor.TSLSensor()

        original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)

        thread_temp = TemperatureThread(60, self.handle_wx_data, dht, self.run_event, self.queue)
        thread_lux = LuxThread(60, self.handle_data, tsl, self.run_event, self.queue)
        thread_wheel = WheelCounterThread(18, 21, self.handle_wheel_data, self.run_event, self.queue)
        thread_lcd = DataReportingThread(self.run_event, self.lcd_queue, self.lcd, self.version_msg)
        thread_button = ButtonHandlerThread(6, self.run_event, self.queue)

        signal.signal(signal.SIGINT, original_sigint_handler)
        thread_lcd.start()
        thread_temp.start()
        thread_lux.start()
        thread_wheel.start()
        thread_button.start()

        while True:
            try:
                # Wait for something on the queue, but only for a short time (1 ms). This will allow some
                # responsiveness on the loop (e.g. for CTRL+C shutdown) and will also act as the loop
                # delay since we're basically in a busy-wait loop
                data = self.queue.get(True, 0.001)
#                logger.info("{0}: {1}".format(threading.currentThread().name, data))

                self.lcd_queue.put(data)

            except KeyboardInterrupt:
                logger.info("Keyboard Stop, terminating worker processes")
                self.run_event.clear()
                thread_temp.join()
                thread_lux.join()
                thread_wheel.join()
                GPIO.cleanup()

                # Cleanup the LCD
                self.lcd.set_backlight(1)
                self.lcd.clear()
                logger.info("Threads shutdown")
                break
#            except Queue.Empty:
                # The queue.get with a timeout throws a Queue.Empty exception. Just continue if that happens
#                continue
            except Exception, ex:
#                logger.error(">{0}< exception caught".format(ex))
                pass

logger.info("Starting Hedgehog Monitor {0}, sensor_handler: v{1}".format(__version__, sensor_handlers.__version__))
mainloop = MainLoop()
mainloop.startup()
