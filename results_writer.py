import csv
import os

class ResultsWriter(csv.DictWriter):
    def __init__(self, filename, fieldnames, fp=None):

        append = False

        if filename is not None:
            if os.path.exists(filename):
                append = True
        if fp is None:
            self.fp = open(filename, "ab")
        else:
            self.fp = fp

        csv.DictWriter.__init__(self, self.fp, fieldnames=fieldnames)
        if append is False:
            self.writeheader()
            self.flush()
        return

    def flush(self):
        self.fp.flush()

    def close(self):
        self.fp.close()
        self.fp = None

    def __del__(self):
        self.flush()
        self.close()
