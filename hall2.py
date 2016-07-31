# -*- coding: utf-8 -*-
"""
Created on Tue Jul 19 23:41:56 2016

@author: pi
"""

from time import sleep
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
LED = 21
ledState = False
HALL_SENSOR = 18
hallActive = False

GPIO.setwarnings(False)
GPIO.setup(LED, GPIO.OUT)
GPIO.setup(HALL_SENSOR, GPIO.IN)
GPIO.output(LED, ledState)

detect_count = 0

while True:
    try:
        GPIO.wait_for_edge(HALL_SENSOR, GPIO.BOTH)
        hallActive = GPIO.input(HALL_SENSOR)
        
        if (hallActive == False):
#            print("LED_ON")
            ledState = True
            detect_count += 1
            print detect_count
        else:
 #           print("LED_OFF")
            ledState= False
            
        GPIO.output(LED, ledState)
    except KeyboardInterrupt:
        print "Closing"
        GPIO.output(LED, False)
        GPIO.cleanup()
        
    
GPIO.output(LED, False)
GPIO.cleanup()
