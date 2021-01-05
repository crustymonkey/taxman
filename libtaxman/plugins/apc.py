
from libtaxman.collector import BaseCollector
from gdata_subm import Gdata
import subprocess as sp

class APCCollector(BaseCollector):

    def get_data_for_sub(self) -> Gdata:
        counters = self._get_counters()
        if counters is None:
            return None

        return Gdata(
            plugin='apc',
            dstypes=['gauge'] * len(counters),
            values=list(counters.values()),
            dsnames=list(counters.keys()),
            interval=int(self.config['interval']),
        )

    def _get_counters(self):
        """
        This will get all the current counters from the apcaccess binary
        """
        cmd = [self.config['binary']]
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
            line = line.strip().lower()
            if not line:
                continue
            
            try:
                key, val = [s.strip() for s in line.split(':', maxsplit=1)]
                if key == 'bcharge':
                    ret['charge.perc'] = float(val.split()[0])
                elif key == 'status':
                    ret['status'] = 1 if val == 'online' else 0
                elif key == 'timeleft':
                    t, unit = val.split()
                    ret['time_left'] = self._time2sec(t, unit)
                elif key == 'loadpct':
                    ret['load.perc'] = float(val.split()[0])
                elif key == 'tonbatt':
                    t, unit = val.split()
                    ret['tm_on_batt'] = self._time2sec(t, unit)
                elif key == 'nompower':
                    ret['nom_power.watts'] = float(val.split()[0])
            except Exception as e:
                logging.error(
                    f'Error parsing output from {self.config["binary"]} '
                    f'with line "{line}": {e}'
                )

        return ret

    def _time2sec(self, t, unit):
        if unit in ('minute', 'minutes'):
            return float(t) * 60
        elif unit in ('second', 'seconds'):
            return float(t)
        elif unit in ('hour', 'hours'):
            return float(t) * 60 * 60
