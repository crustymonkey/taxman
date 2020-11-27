
from libtaxman.collector import BaseCollector
from gdata_subm import Gdata

class NetstatCollector(BaseCollector):
    STAT_FILE = '/proc/net/netstat'

    def get_data_for_sub(self) -> Gdata:
        counters = self._get_counters()
        return Gdata(
            plugin='netstat',
            dstypes=['counter'] * len(counters),
            values=list(counters.values()),
            dsnames=list(counters.keys()),
            interval=int(self.config['interval']),
        )

    def _get_counters(self):
        """
        This will get all the current counters from netstat
        """
        ret = {}
        with open(self.STAT_FILE) as fh:
            keys = []
            values = []
            for i, line in enumerate(fh):
                if i % 2 == 0:
                    # These are keys
                    keys = [s.strip() for s in line.split()[1:]]
                else:
                    # These are the values
                    values = [s.strip() for s in line.split()[1:]]
                    ret.update(zip(keys, values))

        return ret
