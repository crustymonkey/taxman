
from gdata_subm import Gdata
from libtaxman.plugins.libprocstats import get_stats_for_file
from libtaxman.collector import BaseCollector
from typing import List

import logging


class NetstatCollector(BaseCollector):
    STAT_FILE = '/proc/net/netstat'

    def get_data_for_sub(self) -> List[Gdata]:
        try:
            counters = self._get_counters()
        except Exception as e:
            logging.warning(f'Failed to get netstat counters: {e}')
            raise
        ret = []

        for prefix, data in counters.items():
            ret.append(Gdata(
                plugin='netstat',
                dtype=prefix,
                dstypes=['counter'] * len(data),
                values=list(data.values()),
                dsnames=list(data.keys()),
                interval=int(self.config['interval']),
            ))

        return ret

    def _get_counters(self):
        """
        This will get all the current counters from netstat
        """
        stats = get_stats_for_file(self.STAT_FILE)

        return stats
