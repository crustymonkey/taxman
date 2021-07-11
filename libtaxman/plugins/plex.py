
from collections import defaultdict
from gdata_subm import Gdata
from libtaxman.collector import BaseCollector
from urllib.parse import urlencode
from urllib.request import urlopen
from plexapi.server import PlexServer

import json
import logging
import os


class PlexCollector(BaseCollector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._server = PlexServer(
            self.config['base_url'],
            self.config['api_token'],
        )

    def get_data_for_sub(self) -> Gdata:
        tmp = self.get_session_counts()

        return Gdata(
            plugin='plex',
            dstypes=['gauge'] * len(tmp),
            values=list(tmp.values()),
            dsnames=list(tmp.keys()),
            dtype_instance='sessions',
            interval=int(self.config['interval']),
        )

    def get_session_counts(self):
        sessions = self._server.sessions()
        # group by type
        ret = defaultdict(int)
        for s in sessions:
            ret[s.type] += 1
            ret['total'] += 1

        return ret
