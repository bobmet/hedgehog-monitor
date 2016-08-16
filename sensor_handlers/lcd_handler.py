import threading
import Queue
import logging
import datetime
import sqlite3
import os

__version__ = "0.0.6"

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
                            "lux": 0,
                            "revolutions": 0,
                            "distance": 0,
                            "total_revs": 0,
                            "total_distance": 0}
        self.lcd = lcd

        self.backlight_status = False

        self.message_list = list()
        self.current_message_num = 0

        self.timeout_length = 6
        self.loop_sleep = 0.001

        self.version_msg = version_msg
        self.lcd.message(self.version_msg)

        self.display_version = 0
        self.display_wx = 1
        self.display_wheel = 2
        self.display_clock = 3
        self.display_msg = 4
        self.timeout_counter = 0

        if os.path.exists("hedgehog.db"):
            logger.info("Found")
        else:
            logger.info("not Found")
            conn = sqlite3.connect("hedgehog.db")

            c = conn.cursor()
            c.execute("CREATE TABLE temp_tbl (timestamp DATETIME, temp REAL, humidity REAL)")
            c.execute("CREATE TABLE light_tbl (timestamp DATETIME, lux INTEGER)")
            c.execute("CREATE TABLE wheel_tbl(timestamp DATETIME, revolutions REAL, distance REAL, "
                      "moving_time REAL, avg_speed REAL, active INTEGER)")
            conn.commit()
            conn.close()


    def run(self):
        last_datetime = None
        while self.run_event.is_set():
            try:
                self.timeout_counter += self.loop_sleep

                if self.timeout_counter >= self.timeout_length:
                    if self.backlight_status is True:
                        self.lcd.set_backlight(1)
                        self.backlight_status = False
                    self.timeout_counter = 0

                # If we're showing the clock, update it.  We need to do it here before we wait on the queue,
                # otherwise we'll essentially block behind the queue.get() call
                if self.current_message_num == self.display_clock:
                    current_time = datetime.datetime.now().strftime("%H:%M")
                    if current_time != last_datetime:
                        self.update_time()
                        last_datetime = current_time

                data = self.queue.get(True, self.loop_sleep)
                logger.info("LCD_HANDLER: {0}".format(data))
                if 'data_type' in data:
                    self.handle_update(data)

            except Queue.Empty:
                # The queue.get with a timeout throws a Queue.Empty exception. Just continue if that happens
                continue

        logger.info("Thread {0} closing".format(threading.currentThread().name))

    def save_to_database(self, data):
        """

        :param data:
        :return:
        """
        data_type = data['data_type']
        if data_type == 'temperature':
            sql = ("INSERT INTO temp_tbl (timestamp, temp, humidity) values ('{0}', {1}, {2})".format(
                data['datetime'],
                data['temp_f'],
                data['humidity']))
        elif data_type == "wheel":
            active = 1 if data['active'] is True else 0
            sql = ("INSERT INTO wheel_tbl (timestamp, revolutions, distance, moving_time, avg_speed, active)"
                   "values ('{0}', {1}, {2}, {3}, {4}, {5})".format(
                data['datetime'],
                data['revolutions'],
                data['distance'],
                data['moving_time'],
                data['avg_speed'],
                active))
        elif data_type == 'light':
            sql = ("INSERT INTO light_tbl (timestamp, lux) values ('{0}', {1})".format(
                data['datetime'],
                data['lux']))
        else:
            return

        conn = sqlite3.connect("hedgehog.db")
        c = conn.cursor()
        try:
            c.execute(sql)
            conn.commit()
            conn.close()
        except Exception, ex:
            print "Error inserting into table", ex, type(ex)

    def handle_update(self, data):
        data_type = data['data_type']

        if data_type == 'temperature':
            self.sensor_data['temp_f'] = round(float(data['temp_f']), 1)
            self.sensor_data['temp_c'] = round(float(data['temp_c']), 1)
            self.sensor_data['humidity'] = round(float(data['humidity']), 1)
            self.sensor_data['temp_datetime'] = data['datetime']
            if self.current_message_num == self.display_wx:
                self.update_wx()

        elif data_type == 'light':
            self.sensor_data['lux'] = data['lux']
            self.sensor_data['temp_datetime'] = data['datetime']
            if self.current_message_num == self.display_wx:
                self.update_wx()
        elif data_type == 'wheel':
            self.sensor_data['revolutions'] = data['revolutions']
            self.sensor_data['distance'] = data['distance']
            self.sensor_data['total_distance'] += data['distance']
            self.sensor_data['total_revs'] += data['revolutions']
            if self.current_message_num == self.display_wheel:
                self.update_wheel()
        elif data_type == 'button':
            self.update_lcd()
            self.timeout_counter = 0

        self.save_to_database(data)

    def toggle_backlight(self):
        backlight_set = 0 if self.backlight_status is True else 1
        self.lcd.set_backlight(backlight_set)
        self.backlight_status = not self.backlight_status

    def update_lcd(self):

        if self.backlight_status is False:
            self.backlight_status = True
            self.lcd.set_backlight(0)
        else:
            self.current_message_num += 1
            if self.current_message_num > self.display_msg:
                self.current_message_num = self.display_version

            logger.info("Current screen: {0}".format(self.current_message_num))

            if self.current_message_num == self.display_version:
                self.update_version()
            elif self.current_message_num == self.display_wx:
                self.update_wx()
            elif self.current_message_num == self.display_clock:
                self.update_time()
            elif self.current_message_num == self.display_wheel:
                self.update_wheel()
            elif self.current_message_num == self.display_msg:
                self.update_message()


    def update_message(self):
        # 72.4.F 71.6 77.6
        temps = self.get_temp_extremes()
        avg_temp = temps[0]
        min_temp = temps[1]
        max_temp = temps[2]
        avg_hum = temps[3]
        min_hum = temps[4]
        max_hum = temps[5]
        # avg_temp = round(float(temps[0]), 1)
        # max_temp = round(float(temps[1]), 1)
        # min_temp = round(float(temps[2]), 1)

        message = "{0:.1f} {1:.1f} {2:.1f}\n{3:.1f}% {4:.1f}% {5:.1f}".format(avg_temp, min_temp, max_temp, avg_hum, min_hum, max_hum)
        self.lcd.clear()
        self.lcd.message(message)

    def update_version(self):
        message = self.version_msg
        self.lcd.clear()
        self.lcd.message(message)

    def update_wheel(self):
        wheel_data = self.get_wheel_data()
        distance = wheel_data[0]
        revs = wheel_data[1]
        moving_time = wheel_data[2]
        speed = moving_time / distance

        message = "Revs: {0:.0} {1:.3f}\n{2:.0f} {3:.1f} mph".format(revs, distance, moving_time, speed)
        self.lcd.clear()
        self.lcd.message(message)

    def update_wx(self):
#        message = "{current} {avg}".format(current=current, avg=avg_temp)
        message = "{0}{1}{2} {3}%\n{4} lux".format(self.sensor_data['temp_f'],
                                                   chr(223),
                                                   "F",
                                                   self.sensor_data['humidity'],
                                                   self.sensor_data['lux'])
        logger.info(message)
        self.lcd.clear()
        self.lcd.message(message)

    def update_time(self):
        time_now = datetime.datetime.now()
        display_time = time_now.strftime("%a %m/%d/%Y\n%I:%M %p")
        message = display_time
        self.lcd.clear()
        self.lcd.message(message)

    def get_wheel_data(self):
        conn = sqlite3.connect('hedgehog.db')
        c = conn.cursor()

        sql = "select sum(distance),sum(revolutions), sum(moving_time) " \
              "from wheel_tbl where timestamp > datetime('now', '-24 hours')"

        result = c.execute(sql).fetchone()
        conn.close()
        return result

    def get_temp_extremes(self):
        conn = sqlite3.connect('hedgehog.db')
        c = conn.cursor()

        sql = "select avg(temp), min(temp), max(temp), avg(humidity), min(humidity), max(humidity) " \
              "from temp_tbl where timestamp > datetime('now', '-24 hours')"

        result = c.execute(sql).fetchone()
        conn.close()
        return result
