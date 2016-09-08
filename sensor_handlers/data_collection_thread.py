import threading
import multiprocessing
import timeit
import time
import logging
import datetime
logger = logging.getLogger('hh')


class DataCollectionThread(multiprocessing.Process):
    """
    Class to handle acquiring data from a sensor.  It's a subclass of the main threading.Thread class
    to handle getting the data in a separate thread.
    """
    def __init__(self, loop_delay, sensor_module, run_event, queue=None):

        multiprocessing.Process.__init__(self)

        self.loop_delay = loop_delay
        self.sensor_module = sensor_module
        self.run_event = run_event
        self.queue = queue

    def run(self):
        try:
            time_counter = 0.0
            self.report(self.get_data())

            # This will loop while the keep running event is set.  If it gets cleared (external to the thread, e.g.
            # from a KeyboardInterrupt in the calling thread, then the loop will exit and the thread will close.
            while self.run_event.is_set():
                if time_counter >= self.loop_delay:

                    start_time = timeit.default_timer()
                    data = self.get_data()
                    stop_time = timeit.default_timer()
                    elapsed = stop_time - start_time
                    self.report(data)
                    time_counter = elapsed
                time.sleep(0.1)
                time_counter += 0.1
        except KeyboardInterrupt:
            logger.info("Thread {0} closing".format(threading.currentThread().getName()))

    def get_data(self):
        return None

    def report(self, data_points):
        self.queue.put(data_points)


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
