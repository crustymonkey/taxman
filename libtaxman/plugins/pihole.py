
from libtaxman.collector import BaseCollector
from gdata_subm import Gdata
from urllib.request import urlopen
import json
import logging
import os

class PiholeCollector(BaseCollector):

    def get_data_for_sub(self) -> Gdata:
        counters = None
        try:
            counters = self._get_counters()
        except Exception as e:
            logging.exception("Failed to get pihole counters")

        if counters is None:
            return None

        logging.debug(f'Got counters: {json.dumps(counters, indent=4)}')

        ret = []
        for host, data in counters.items():
            cdata = {k: v for k, v in data.items() if k != 'enabled'}

            ret.append(Gdata(
                plugin='pihole',
                host=host,
                dstypes=['counter'] * len(cdata) + ['gauge'],
                values=list(cdata.values()) + [data['enabled']],
                dsnames=list(cdata.keys()) + ['enabled'],
                interval=int(self.config['interval']),
            ))

        return ret

    def _get_counters(self):
        """
        This will get all the current counters from the apcaccess binary
        """
        hosts = [h.strip() for h in self.config['hosts'].split(',')]
        ret = {}

        for host in hosts:
            url = self._gen_url(host)
            with urlopen(url) as resp:
                data = json.loads(resp.read())

            parsed = self._parse_data(data)

            ret[host] = parsed

        return ret

    def _gen_url(self, host):
        api_key = self.config[host]
        url = f'http://{host}/api.php?auth={api_key}&summaryRaw'

        return url

    def _parse_data(self, data):
        ret = {}

        ret['queries'] = data['dns_queries_all_types']
        ret['ads_today'] = data['ads_blocked_today']
        ret['last_updated'] = data['gravity_last_updated']['absolute']
        ret['enabled'] = 1 if data['status'] == 'enabled' else 0

        for key in (
                'queries_cached',
                'queries_forwarded',
                'reply_CNAME',
                'reply_IP',
                'reply_NODATA',
                'reply_NXDOMAIN',
                'unique_domains'):
            ret[key] = data[key]

        return ret
