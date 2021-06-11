
from gdata_subm import Gdata
from libtaxman.collector import BaseCollector
from urllib.parse import urlencode
from urllib.request import urlopen

import json
import logging


class SabCollector(BaseCollector):

    def get_data_for_sub(self) -> Gdata:
        ret = None

        try:
            data = self._get_remote_data()
        except Exception:
            logging.exception("Failed to get sab data")
            return None

        return Gdata(
            plugin='sab',
            dstypes=['gauge'],
            # Invert the paused value
            values=[int(not data['queue']['paused'])],
            dsnames=['queue_running'],
            interval=int(self.config['interval']),
        )

    def _get_remote_data(self):
        """
        Queries the remote service for the queue data
        """
        req_dict = {
            'output': 'json',
            'apikey': self.config['api_key'],
            'mode': 'queue',
        }
        base = self.config['base_url'].rstrip('/')
        url = f'{base}/api?{urlencode(req_dict)}'
        res = urlopen(url, timeout=55)

        if res.status < 200 or res.status >= 300:
            logging.error(
                f'Failed to get sab queue info with status {res.status}'
            )

        return json.loads(res.read().decode('utf-8'))
