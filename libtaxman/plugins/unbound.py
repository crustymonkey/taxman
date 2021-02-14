
from libtaxman.collector import BaseCollector
from gdata_subm import Gdata
import logging
import subprocess as sp

class UnboundCollector(BaseCollector):

    def get_data_for_sub(self) -> Gdata:
        counters = self._get_counters()
        if counters is None:
            return None

        return Gdata(
            plugin='unbound',
            dstypes=['gauge'] * len(counters),
            values=list(counters.values()),
            dsnames=list(counters.keys()),
            interval=int(self.config['interval']),
        )

    def _get_counters(self):
        """
        This will get all the current counters from the apcaccess binary
        """
        cmd = [self.config['binary'], '-c', self.config['config'], 'stats']
        proc = sp.run(
            cmd,
            stdout=sp.PIPE,
            stderr=sp.PIPE,
            encoding='utf-8',
            errors='replace',
        )

        if proc.returncode != 0:
            logging.warning(
                f'{cmd} exited with code {proc.returncode}: {proc.stderr}')

            return None

        return self._parse_counters(proc.stdout)

    def _parse_counters(self, raw_counters):
        ret = {}

        for line in raw_counters.split('\n'):
            line = line.strip()
            if not line:
                continue

            k, v = line.split('=', maxsplit=1)
            ret[k] = float(v)

        return ret
