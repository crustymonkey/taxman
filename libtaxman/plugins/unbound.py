
from libtaxman.collector import BaseCollector
from gdata_subm import Gdata
from unbound_console import RemoteControl
import logging
import re
import subprocess as sp

class UnboundCollector(BaseCollector):

    def get_data_for_sub(self) -> Gdata:
        counters = None
        try:
            self._set_blocklist()
            counters = self._get_counters()
        except Exception as e:
            logging.exception("Failed to get unbound counters")

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
        counter_str = ''
        if self.config.getboolean('use_lib'):
            counter_str = self._get_counters_lib()
        else:
            counter_str = sefl._get_counters_bin()

        return self._parse_counters(counter_str)

    def _get_counters_bin(self):
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

        return proc.stdout

    def _get_counters_lib(self):
        cak = {
            'srv_cert': self.config['ub_server_cert'],
            'cl_cert': self.config['ub_client_cert'],
            'cl_key': self.config['ub_client_key'],
        }

        # Do a path check for the cert/key files and set them to the data
        # dir if it's not a full path
        for k, v in cak.items():
            if not v.startswith('/'):
                # Set this to the data dir
                cak[k] = os.path.join(self.config['data_dir'], v)

        rc = RemoteControl(
            host=self.config['ub_control_host'],
            port=self.config.getint('ub_control_port'),
            server_cert=cak['srv_cert'],
            client_cert=cak['cl_cert'],
            client_key=cak['cl_key'],
        )

        return rc.send_command('stats')

    def _parse_counters(self, raw_counters):
        ret = {}

        for line in raw_counters.split('\n'):
            line = line.strip()
            if not line:
                continue

            k, v = line.split('=', maxsplit=1)

            skip = False
            for bl in self.blocklist:
                if bl.search(k):
                    skip = True
                    break
            if skip:
                continue

            ret[k] = float(v)

        return ret

    def _set_blocklist(self):
        self.blocklist = []
        for bl in self.config['blocklist'].split(';'):
            bl = bl.strip()
            if not bl:
                continue

            self.blocklist.append(re.compile(bl, re.I))
