
from gdata_subm import Gdata
from libtaxman.collector import BaseCollector

import json
import logging
import os
import re
import subprocess as sp


class SSDCollector(BaseCollector):
    ATA_ATTR_KEY = 'ata_smart_attributes'
    NVME_ATTR_KEY = 'nvme_smart_health_information_log'
    DRV_REG = re.compile(r'^(sd[a-z]|nvme\d)$')
    DRV_LIST = None

    def get_data_for_sub(self) -> Gdata:
        ret = None

        try:
            metrics = self._get_ssd_metrics()
        except Exception:
            logging.exception("Failed to get ssd data")
            return None

        ret = []
        for drv, data in metrics.items():
            ret.append(Gdata(
                plugin='ssd',
                dtype_instance=drv,
                dstypes=['gauge'] * len(data),
                dsnames=list(data.keys()),
                values=list(data.values()),
                interval=int(self.config['interval']),
            ))

        return ret

    def _get_ssd_metrics(self):
        """
        This will query the SSDs via `smartctl` to get wear level and power
        on hours
        """
        ret = {}
        drv_list = self._get_drv_list()

        for drv in drv_list:
            try:
                data = self._get_drv_data(drv)
            except Exception as e:
                logging.error(f'Error getting data for {drv}: {e}')
                continue

            name = os.path.basename(drv)
            if name.startswith('sd'):
                ret[name] = self._get_ssd_data(data)
            else:
                ret[name] = self._get_nvme_data(data)

        return ret

    def _get_ssd_data(self, data):
        """
        This will extract the desired data from the raw data provided by
        smartctl
        """
        ret = {}

        if not data['trim']['supported']:
            # Trim is only supported on SSDs, not spinning disks
            return None

        for item in data[self.ATA_ATTR_KEY]['table']:
            if item['name'] == 'Power_On_Hours':
                ret['power_on_hours'] = item['raw']['value']
            elif item['name'] == 'Wear_Leveling_Count':
                ret['perc_used'] = 100 - item['value']

        return ret

    def _get_nvme_data(self, data):
        """
        This will extract the desired data from the raw data provided by
        smartctl
        """
        ret = {}

        ret['power_on_hours'] = data[self.NVME_ATTR_KEY]['power_on_hours']
        ret['perc_used'] = data[self.NVME_ATTR_KEY]['percentage_used']

        return ret

    def _get_drv_list(self):
        """
        This will only return SSD or NVME drives.  All others will be skipped.
        """
        if self.DRV_LIST:
            return self.DRV_LIST

        ret = []
        for dev in os.listdir('/dev'):
            if m := self.DRV_REG.match(dev):
                if self._is_ssd_nvme(m.group(1)):
                    ret.append(os.path.join('/dev', m.group(1)))

        self.DRV_LIST = ret

        return ret

    def _is_ssd_nvme(self, drv_name):
        if drv_name.startswith('nvme'):
            # This is simple
            return True

        path = os.path.join('/sys/block', drv_name, 'queue/rotational')
        with open(path) as fh:
            res = fh.read()

        return res.strip() == '0'

    def _get_drv_data(self, drv):
        """
        This runs smartctl to get the information for the local drive
        """
        cmd = ['sudo', 'smartctl', '--json', '-x', drv]
        p = sp.run(cmd, capture_output=True, encoding='utf-8',
            errors='replace', check=True)

        return json.loads(p.stdout)
