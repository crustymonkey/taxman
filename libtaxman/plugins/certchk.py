
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from gdata_subm import Gdata
from io import StringIO
from libtaxman.collector import BaseCollector
from OpenSSL import crypto
import logging
import string
import subprocess as sp


@dataclass
class Site:
    host: str
    port: int
    
    def cmd(self, openssl):
        return [
            openssl, 's_client',
            '-connect', f'{self.host}:{self.port}',
            '-servername', self.host,
        ]

    def __str__(self):
        return f'{self.host}:{self.port}'


class CertChk(BaseCollector):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sites = []
        self._init_sites()

    def get_data_for_sub(self) -> Gdata:
        counters = None
        try:
            counters = self._get_counters()
        except Exception:
            logging.exception("Failed to get counters for certchk")

        if not counters:
            return None

        return Gdata(
            plugin='cert',
            dstypes=['gauge'] * len(counters),
            values=list(counters.values()),
            dsnames=list(counters.keys()),
            interval=int(self.config['interval']),
        )

    def _get_counters(self):
        """
        This will get the map of Site -> time in seconds to expiration
        """
        ret = {}
        workers = int(self.config['max_workers'])

        with ThreadPoolExecutor(max_workers=workers) as exe:
            fut_to_site = {
                exe.submit(self._get_cert_exp, s): s
                for s in self._sites
            }

            for fut in as_completed(fut_to_site):
                site = fut_to_site[fut]
                remaining = None

                try:
                    remaining = fut.result()
                except Exception as e:
                    logging.warning(
                        f'Failed to get a response for {site}: {e}')
                else:
                    ret[str(site)] = remaining

        return ret

    def _get_cert_exp(self, site: Site):
        proc = sp.run(
            site.cmd(self.config['openssl']),
            stdin=sp.DEVNULL,
            stdout=sp.PIPE,
            stderr=sp.PIPE,
            encoding='utf-8',
            errors='replace',
        )

        if proc.returncode != 0:
            logging.warning(
                f'{cmd} exited with code {proc.returncode}: {proc.stderr}')

            return None

        return self._parse_cert_interval(proc.stdout)

    def _parse_cert_interval(self, cert_txt):
        """
        We need to parse the cert after stripping the header and footer
        """
        tmp = StringIO()
        in_cert = False
        for line in cert_txt.split('\n'):
            if 'BEGIN' in line:
                in_cert = True
            elif not in_cert:
                continue

            tmp.write(f'{line}\n')

            if 'END ' in line:
                break

        na = self._get_not_after(tmp.getvalue())
        interval = na - datetime.now()

        return interval.total_seconds()

    def _get_not_after(self, pem):
        c = crypto.load_certificate(crypto.FILETYPE_PEM, pem)

        na_tmp = c.get_notAfter().decode('utf-8')
        na_str = na_tmp.rstrip(string.ascii_letters)
        
        return datetime.strptime(na_str, '%Y%m%d%H%M%S')

    def _init_sites(self):
        for host_port in self.config['services'].split():
            host, port = host_port.split(':')
            self._sites.append(Site(host, int(port)))
            
