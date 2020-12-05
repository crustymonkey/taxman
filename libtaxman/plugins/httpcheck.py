
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from libtaxman.collector import BaseCollector
from gdata_subm import Gdata
from urllib.request import urlopen

import logging
import time


@dataclass
class Site:
    site: str
    https: bool
    url: str


@dataclass
class Result:
    result: int  # 1 or 0
    latency: float


class HttpHealthCollector(BaseCollector):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._site_map = {}
        self._pop_site_map()

    def get_data_for_sub(self) -> Gdata:
        health = self._get_health()

        health_dsnames = []
        latency_dsnames = []
        health_values = []
        latency_values = []

        for url, res in health.items():
            site = self._site_map[url]
            name = 'https.' if site.https else 'http.'
            name += site.site.replace('.', '_')

            health_dsnames.append(f'{name}.health')
            latency_dsnames.append(f'{name}.latency')
            health_values.append(res.result)
            latency_values.append(res.latency)


        return [
            Gdata(
                plugin='httpcheck',
                dstypes=['gauge'] * len(health),
                values=health_values,
                dsnames=health_dsnames,
                interval=int(self.config['interval']),
            ),
            Gdata(
                plugin='httpcheck',
                dstypes=['gauge'] * len(health),
                values=latency_values,
                dsnames=latency_dsnames,
                interval=int(self.config['interval']),
            ),

        ]

    def _get_health(self):
        """
        This will check the health of all the sites in parallel
        """
        ret = {}
        workers = int(self.config['max_workers'])
        with ThreadPoolExecutor(max_workers=workers) as exe:
            fut_to_url = {
                exe.submit(self._get_rcode, k): k
                for k in self._site_map
            }

            for fut in as_completed(fut_to_url.keys()):
                url = fut_to_url[fut]
                health = 0
                latency = 0

                try:
                    code, latency = fut.result()
                except Exception as e:
                    logging.warning(
                        f'Failed to get a response for {url}')
                else:
                    health = 1 if code == 200 else 0

                ret[url] = Result(result=health, latency=latency)

        return ret

    def _get_rcode(self, url: str) -> int:
        start = time.time()
        try:
            resp = urlopen(url, timeout=2)
        except Exception as e:
            logging.warning(f'urlopen for url "{url}" failed: {e}')
            return (0, time.time() - start)

        latency = time.time() - start

        return (int(resp.getcode()), latency)

    def _pop_site_map(self):
        for site in self.config['sites_https'].split():
            site = site.strip()
            url = f'https://{site}'
            self._site_map[url] = Site(
                site=site,
                https=True,
                url=url,
            )

        for site in self.config['sites_http'].split():
            site = site.strip()
            url = f'http://{site}'
            self._site_map[url] = Site(
                site=site,
                https=False,
                url=url,
            )
