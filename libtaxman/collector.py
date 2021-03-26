#!/usr/bin/env python3

from configparser import ConfigParser, SectionProxy
from gdata_subm import Gdata
from threading import Thread, Event
from queue import Queue
from typing import List, Union
import time


class BaseCollector(Thread):
    """
    This is the base collector class that should be used for plugins
    """
    def __init__(self, res_q: Queue, config: SectionProxy):
        super().__init__()
        self.config = config  # This is the relevant section of the config
        self.next_sched = time.time()
        self.run_ev = Event()
        self._res_q = res_q
        self.daemon = True
        self._stop = Event()

    def run(self):
        while not self._stop.is_set():
            # Wait for the run event
            self.run_ev.wait()
            # Reset the run event
            self.run_ev.clear()

            data = self.get_data_for_sub()
            self._res_q.put(data, timeout=1)

    def run_now(self):
        """
        This basically triggers a run event for the thread
        """
        self.run_ev.set()
        self.sched_next()

    def stop(self):
        self._stop.set()

    def sched_next(self) -> None:
        self.next_sched += int(self.config['interval'])
    
    def get_data_for_sub(self) -> Union[Gdata, List[Gdata]]:
        """
        This is called to get the data for upstream submission and should
        return a Gdata object
        """
        raise NotImplementedError()
        
