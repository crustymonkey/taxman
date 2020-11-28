
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from libtaxman.collector import BaseCollector
from gdata_subm import Gdata
from urllib.request import urlopen

import logging


@dataclass
class Site:
    site: str
    https: bool
    url: str


class HttpHealthCollector(BaseCollector):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._site_map = {}
        self._pop_site_map()

    def get_data_for_sub(self) -> Gdata:
        health = self._get_health()
        dsnames = []
        values = []

        for url, metric in health.items():
            site = self._site_map[url]
            name = 'https.' if site.https else 'http.'
            name += site.site.replace('.', '_')

            dsnames.append(name)
            values.append(metric)

        return Gdata(
            plugin='httpcheck',
            dstypes=['gauge'] * len(health),
            values=values,
            dsnames=dsnames,
            interval=int(self.config['interval']),
        )

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
                try:
                    res = fut.result()
                except Exception as e:
                    logging.warning(
                        f'Failed to get a response for {site}')
                    ret[url] = 0
                else:
                    ret[url] = 1 if res == 200 else 0

        return ret

    def _get_rcode(self, url: str) -> int:
        try:
            resp = urlopen(url)
        except Exception as e:
            logging.warning(f'urlopen for url "{url}" failed: {e}')
            return 0

        return int(resp.getcode())

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
