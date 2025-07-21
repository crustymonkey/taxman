
#
# This plugin uses the python-opn library to pull stats from an OPNSense
# instance
#

from gdata_subm import Gdata
from libtaxman.collector import BaseCollector
from pyopn import OPNClient
from typing import List
import logging


class OPNSenseCollector(BaseCollector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._oapi = OPNClient(
            api_key=self.config['key'],
            api_secret=self.config['secret'],
            base_url=self.config['base_url'],
            ssl_verify=self.config.getboolean('ssl_verify'),
        )

    def get_data_for_sub(self) -> List[Gdata]:
        ret = []
        try:
            stats = self._get_stats()
        except Exception as e:
            logging.error(
                f'Failed to get stats from {self.config["base_url"]}: {e}')
            return ret

        ret.extend(self._get_int_gdata(stats))

        return ret

    def _get_int_gdata(self, stats) -> List[Gdata]:
        """
        Turn the interface stats into Gdata objects
        """
        ret = []

        for iface, data in stats['interface'].items():
            dsnames = []
            values = []
            dstypes = []

            for k, v in data.items():
                dsnames.append(k)
                if k == 'mtu':
                    dstypes.append('gauge')
                else:
                    dstypes.append('counter')
                values.append(float(v))

            ret.append(Gdata(
                plugin='opnsense',
                dtype='interface',
                dtype_instance=iface,
                dsnames=dsnames,
                dstypes=dstypes,
                values=values,
                interval=float(self.config['interval']),
                host=self.config['gdata_host'],
            ))

        return ret

    def _get_stats(self):
        """
        Get stats from the server
        """
        ret = {'interface': {}}

        ifaces = [i.strip() for i in self.config['interfaces'].split()]

        # First, get the interface stats
        stats = self._oapi.diagnostics.interface.get_interface_statistics()
        logging.debug(f'Got stats from opnsense: {stats}')
        if stats and stats['statistics']:
            for _, data in stats['statistics'].items():
                if data['name'] in ifaces and \
                        data['network'].startswith('<Link'):
                    # Get the link data for the interface, this will have
                    # everything.  Copy the data and delete the stuff we
                    # don't want
                    dcopy = data.copy()
                    del dcopy['name']
                    del dcopy['flags']
                    del dcopy['network']
                    del dcopy['address']

                    ret['interface'][data['name']] = dcopy
        else:
            logging.warning(
                f'Failed to get interface stats for {ifaces}')

        return ret
