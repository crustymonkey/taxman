
from libtaxman.collector import BaseCollector
from gdata_subm import Gdata
import subprocess as sp
import json

class SpeedtestCollector(BaseCollector):

    def get_data_for_sub(self) -> Gdata:
        counters = self._get_counters()
        if counters is None:
            return None
        return Gdata(
            plugin='bandwidth',
            dstypes=['gauge'] * 3,
            values=[counters['download'], counters['upload'], counters['ping']],
            dsnames=['down', 'up', 'ping'],
            interval=int(self.config['interval']),
        )

    def _get_counters(self):
        """
        This will get all the current counters from speedtest
        """
        cmd = [self.config['binary'], '--json']
        if self.config['server_id']:
            cmd.extend(['--server', self.config['server_id']])
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
        
        return json.loads(proc.stdout)
