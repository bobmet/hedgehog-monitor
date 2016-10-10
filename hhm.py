# -*- coding: utf-8 -*-
"""
Created on Thu Jul 14 23:20:03 2016

@author: pi
"""

import logging
import signal
import threading
from multiprocessing import Queue

import RPi.GPIO as GPIO
import yaml

import dht22
import sensor_handlers
import tsl_sensor
from lcd_display import LCDDisplay
from sensor_handlers.button_handler import ButtonHandlerThread
from sensor_handlers.data_collection_thread import TemperatureThread, LuxThread
from sensor_handlers.lcd_handler import DataReportingThread
from sensor_handlers.wheel_counter import WheelCounterThread

__version__ = "0.0.28"


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger('hh')

CONFIG_FILENAME = "hhconfig.yml"

class MainLoop:
    def __init__(self):
        self.config = self.load_config()
        self.gpio_setup()
        self.run_event = threading.Event()
        self.queue = Queue()
        self.reporting_queue = Queue()
        self.lcd = LCDDisplay()

        return

    def load_config(self):
        """
        Loads the configuration file using the PyYaml package
        :return: Dictionary containing the configuration
        """

        with open(CONFIG_FILENAME, "rb") as fp:
            config = yaml.safe_load(fp)

        return config

    def gpio_setup(self):
        """
        Some basic setup of the GPIO library
        :return:
        """
        # Use the BCM numbering for the GPIO pins
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        logger.info("GPIO Setup")

    def gpio_cleanup(self):
        """
        Takes care of the GPIO cleanup
        :return:
        """
        GPIO.cleanup()

    def startup(self):
        """
        Main function for the program
        :return:
        """
        self.run_event.set()

        if 'dht_led_pin' in self.config['pins']:
            dht_led_pin = self.config['pins']['dht_led_pin']
            GPIO.setup(dht_led_pin, GPIO.OUT)
        else:
            dht_led_pin = None
        dht_data_pin = self.config['pins']['dht_data_pin']
        button_pin = self.config['pins']['button_pin']
        dht = dht22.DHT22(data_gpio_pin=dht_data_pin, led_gpio_pin=dht_led_pin)
        tsl = tsl_sensor.TSLSensor()

        # TODO:
        original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)

        # Subprocess handlers
        thread_temp = TemperatureThread(self.config['timeouts']['wx_timeout'], dht, self.run_event, self.queue)
        thread_lux = LuxThread(self.config['timeouts']['lux_timeout'], tsl, self.run_event, self.queue)
        thread_wheel = WheelCounterThread(self.config['pins']['wheel_sensor_pin'],
                                          self.config['pins']['wheel_led_pin'],
                                          self.config['timeouts']['wheel_loop_timer'],
                                          self.config['timeouts']['wheel_inactivity_timer'],
                                          self.config['wheel_info']['circumference'],
                                          self.run_event,
                                          self.queue)
        thread_lcd = DataReportingThread(self.run_event, self.reporting_queue, self.lcd, __version__,
                                         self.config['timeouts']['lcd_fadeout_time'],
                                         self.config['database']['filename'])
        thread_button = ButtonHandlerThread(button_pin, self.run_event, self.queue)

        signal.signal(signal.SIGINT, original_sigint_handler)

        # Start the subprocesses
        thread_lcd.start()
        thread_temp.start()
        thread_lux.start()
        thread_wheel.start()
        thread_button.start()

        while True:
            try:
                # Wait for something on the queue, but only for a short time (1 ms). This will allow some
                # responsiveness on the loop (e.g. for CTRL+C shutdown) and will also act as the loop
                # delay since we're basically in a busy-wait
                data = self.queue.get(True, 0.001)
                logger.info("{0}: {1}".format(threading.currentThread().name, data))

                # Get the data over to the reporting thread
                self.reporting_queue.put(data)

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
            except Exception as ex:
                pass

logger.info("Starting Hedgehog Monitor {0}, sensor_handler: v{1}".format(__version__, sensor_handlers.__version__))
mainloop = MainLoop()
mainloop.startup()
