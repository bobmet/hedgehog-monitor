import threading
import multiprocessing
import timeit
import time
import logging

logger = logging.getLogger('hh')


class DataCollectionThread(multiprocessing.Process):
    """
    Class to handle acquiring data from a sensor.  It's a subclass of the main threading.Thread class
    to handle getting the data in a separate thread.
    """
    def __init__(self, loop_delay, callback, sensor_module, run_event, queue=None):

        multiprocessing.Process.__init__(self)

        self.loop_delay = loop_delay
        self.callback = callback
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
