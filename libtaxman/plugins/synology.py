
#
# This uses python-synology to gather stats from a synology NAS
#

import logging
from concurrent.futures import ThreadPoolExecutor, wait
from gdata_subm import Gdata
from libtaxman.collector import BaseCollector
from synology_dsm import SynologyDSM
from typing import List, Dict, Union


class SynologyCollector(BaseCollector):
    # These are the submodules to update when gathering stats
    MOD_MAP = {
        'information': [
            'temperature',
            'uptime',
        ],
        'utilisation': [
            'cpu_1min_load',
            'cpu_5min_load',
            'cpu_15min_load',
            'memory_real_usage',
        ],
        'storage': [],  # This will be done manually
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._conn = SynologyDSM(
            self.config['host'],
            self.config['port'],
            self.config['username'],
            self.config['password'],
        )

    def get_data_for_sub(self) -> List[Gdata]:
        ret = []
        self._update()
        try:
            stats = self._get_stats()
        except Exception as e:
            logging.error(
                f'Failed to get stats from {self.config["host"]}: {e}')
            logging.exception(e)
            return ret

        ret.append(Gdata(
            plugin='syn',
            dsnames=list(stats.keys()),
            dstypes=['gauge'] * len(stats),
            values=list(stats.values()),
            interval=float(self.config['interval']),
            host=self.config['data_hostname'],
        ))

        return ret

    def _get_stats(self) -> Dict[str, float]:
        ret = {}
        for k, v in self.MOD_MAP.items():
            for key in v:
                ret_key = f'{k}.{key}'
                ret[ret_key] = float(getattr(getattr(self._conn, k), key))

            if k == 'utilisation':
                ret.update(self._get_network_usage())
            if k == 'storage':
                ret.update(self._get_storage_stats())

        return ret

    def _update(self) -> None:
        with ThreadPoolExecutor(max_workers=len(self.MOD_MAP)) as exe:
            fut_to_mod = {
                exe.submit(self._update_mod, m): m
                for m in self.MOD_MAP
            }

            ret = wait(list(fut_to_mod.keys()), timeout=3)
            for fut in ret.not_done:
                logging.warning(
                    f'Failed to update synology module: {fut_to_mod[fut]}')

            for fut in ret.done:
                try:
                    fut.result()
                except Exception as e:
                    logging.warning(
                        'Failed to update synology module '
                        f'{fut_to_mod[fut]}: {e}'
                    )

    def _update_mod(self, module) -> None:
        getattr(self._conn, module).update()

    def _get_network_usage(self) -> Dict[str, float]:
        return {
            f'utilisation.net.up':
                float(self._conn.utilisation.network_up() * 8),  # bytes -> bits
            f'utilisation.net.down':
                float(self._conn.utilisation.network_down() * 8),
        }

    def _get_storage_stats(self) -> Dict[str, float]:
        ret = {}

        for vol in self._conn.storage.volumes:
            pref = f'storage.{vol["deploy_path"]}'
            tot_size = float(vol['size']['total'])
            used = float(vol['size']['used'])
            ret[f'{pref}.disk_failure_number'] = \
                float(vol['disk_failure_number'])
            ret[f'{pref}.used'] = used
            ret[f'{pref}.free'] = tot_size - used
            ret[f'{pref}.perc_used'] = (used / tot_size) * 100
        
        return ret

