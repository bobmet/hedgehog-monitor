#!/usr/bin/python
# ========================================================
# Python script for controlling a push button switch
# Version 1.2 - by Thomas Schoch - www.retas.de
# ========================================================

import time
import RPi.GPIO as GPIO
import threading
import Queue

__version__ = "0.0.1"


class ButtonHandlerThread(threading.Thread):
    def __init__(self, gpio_pin, run_event, queue):

        threading.Thread.__init__(self)

        self.gpio_pin = gpio_pin
        self.run_event = run_event
        self.queue = queue

        # setup GPIO "gpio" as input with pull-up
        GPIO.setup(self.gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def run(self):
        counter = 0
        while self.run_event.is_set():

            # waiting for interrupt from button press
            GPIO.wait_for_edge(self.gpio_pin, GPIO.FALLING, timeout=100)

            sec = 0
            state = 0
            while GPIO.input(self.gpio_pin) == GPIO.LOW:
                time.sleep(0.05)
                sec += 0.05
                if sec > 2:
                    print "Long Press"

                if state == 0:
                    counter += 1
                    print "Press", counter
                    data = {'data_type': "button",
                            'action': 'press'}
                    self.queue.put(data)
                    state = 1


if __name__ == '__main__':
    print "Startup"
    GPIO.setmode(GPIO.BCM)
    GPIO.setmode(GPIO.BCM)

    # use button at GPIO 7 (P1 header pin 26)
    gpio = 6

    # state of some application, starts with "0"
    state = 0

    # setup GPIO "gpio" as input with pull-up
    GPIO.setup(gpio, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    counter = 0

    # main loop
    while True:

        # waiting for interrupt from button press
        GPIO.wait_for_edge(gpio, GPIO.FALLING, timeout=100)

        sec = 0
        state = 0
        while GPIO.input(gpio) == GPIO.LOW:
            time.sleep(0.05)
            sec += 0.05
            if sec > 2:
                print "Long Press"

            if state == 0:
                counter += 1
                print "Press", counter
                state = 1

    GPIO.cleanup()
    GPIO.setmode(GPIO.BCM)



def test():

    # waiting for button release
    sec = 0
    while GPIO.input(gpio) == GPIO.LOW:

        # delay for debouncing
        time.sleep(0.05)
        sec += 0.05

        # pressed longer than 2 seconds? Shutdown!
        if sec > 2:
            GPIO.cleanup()
            print "2 Second press"

    # button released: toggle state
    if (state == 0):
        print "Press"
        state = 1
#        system("/home/pi/io/led0 1900 100")
        # switch application on here ...
    else:
        print "release"
        state = 0
#        system("/home/pi/io/led0 100 1900")
        # switch application off here ...

# reset interrupt


