import Adafruit_CharLCD as LCD
import Adafruit_GPIO.MCP230xx as MCP
import time


class LCDDisplay(LCD.Adafruit_CharLCD):
    """
    Subclass for our HD44780 LCD using an I2C MCP23008 backpack.  I subclassed it just to to make the initialization
    of the LCD w/MCP23008 a bit easier. It's a simple wrapper subclass of the Adafruit_CharLCD software, available
    on GitHub:
        https://github.com/adafruit/Adafruit_Python_CharLCD

    The Adafruit parts:
    - Standard LCD 16x2 + extras - white on blue (https://www.adafruit.com/products/181)
    - I2C/SPI character LCD Backpack (https://www.adafruit.com/products/292)

    Both purchased July, 2016
    """
    def __init__(self):
        # pinouts
        lcd_rs = 1
        lcd_en = 2
        lcd_d4 = 3
        lcd_d5 = 4
        lcd_d6 = 5
        lcd_d7 = 6
        backlight_pin = 7

        lcd_columns = 16
        lcd_rows = 2

        # We're going to use an I2C interface, so get the correct object to pass to the LCD class
        gpio = MCP.MCP23008(0x20,busnum=1)

        # Use the base class's init to set everything up
        LCD.Adafruit_CharLCD.__init__(self, lcd_rs,lcd_en, lcd_d4, lcd_d5, lcd_d6,lcd_d7,
                                        lcd_columns, lcd_rows, gpio=gpio, backlight=backlight_pin)


if __name__ == '__main__':
    print "Starting"
    lcd = LCDDisplay()

    lcd.set_backlight(0)
    lcd.message("0123456789abcdef\nfedcba987654321")
    time.sleep(10)
    lcd.set_backlight(1)
    lcd.clear()
