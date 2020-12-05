
#
# This plugin uses pfsense-fauxapi to gather stats from pfsense
#

from gdata_subm import Gdata
from libtaxman.collector import BaseCollector
from PfsenseFauxapi.PfsenseFauxapi import PfsenseFauxapi
from typing import List


class PfsenseCollector(BaseCollector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fapi = PfsenseFauxapi(
            self.config['api_host'],
            self.config['key'],
            self.config['secret'],
        )

    def get_data_for_sub(self) -> List[Gdata]:
        ret = []
        try:
            stats = self._get_stats()
        except Exception as e:
            logging.error(
                f'Failed to get stats from {self.config["api_host"]}: {e}')
            return ret
        
        ret.extend(self._get_int_gdata(stats))
        ret.append(self._get_sys_gdata(stats))

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
                values.append(v)

            ret.append(Gdata(
                plugin='pfsense',
                dtype='interface',
                dtype_instance=iface,
                dsnames=dsnames,
                dstypes=dstypes,
                values=values,
                interval=float(self.config['interval']),
                host=self.config['gdata_host'],
            ))
        
        return ret

    def _get_sys_gdata(self, stats) -> Gdata:
        return Gdata(
            plugin='pfsense',
            dtype='system',
            dsnames=list(stats['system'].keys()),
            dstypes=['gauge'] * len(stats['system']),
            values=list(stats['system'].values()),
            interval=float(self.config['interval']),
            host=self.config['gdata_host'],
        )

    def _get_stats(self):
        """
        Get stats from the server
        """
        ret = {}
        # First, get the interface stats
        for iface in self.config['interfaces'].split():
            iface = iface.strip()
            stats = self._fapi.interface_stats(iface)
            if stats and stats['message'] == 'ok':
                ret['interface'] = {iface: stats['data']['stats']}
            else:
                logging.warning(
                    f'Failed to get interface stats for {iface}')

        # Now get the system stats
        stats = self._fapi.system_stats()
        if stats and stats['message'] == 'ok':
            ret['system'] = {
                'load_avg_1': float(stats['data']['stats']['load_average'][0]),
                'load_avg_5': float(stats['data']['stats']['load_average'][1]),
                'load_avg_15': float(stats['data']['stats']['load_average'][2]),
                'pfstateperc': float(stats['data']['stats']['pfstatepercent']),
                'mbufperc': float(stats['data']['stats']['mbufpercent']),
                'temp': float(stats['data']['stats']['temp']),
            }

        return ret
