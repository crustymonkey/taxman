
from gdata_subm import Gdata, GdataSubmit
from libtaxman.config import TaxmanConfig
from queue import Queue, Empty
from threading import Thread, Event
from typing import Union, List

import logging

class Submitter(Thread):
    def __init__(self, res_q: Queue, config: TaxmanConfig):
        super().__init__()
        self.res_q = res_q
        self.config = config
        self._subm = GdataSubmit(
            url=self.config['main']['submission_url'],
            username=self.config['main']['submission_username'],
            password=self.config['main']['submission_password'],
        )
        self.daemon = False
        self._stop = Event()

    def run(self):
        while not self._stop.is_set():
            try:
                data = self.res_q.get(timeout=0.1)
                if not isinstance(data, (tuple, list)):
                    data = [data]
            except Empty:
                # Hit the timeout
                continue
            
            self._submit_data(data)

    def _submit_data(self, data: Union[Gdata, List[Gdata]]):
        logging.debug('Submitting all data to the server')
        try:
            self._subm.send_data(data)
        except Exception as e:
            logging.error(f'Failed to send data to the server: {e}')

    def stop(self):
        self._stop.set()
