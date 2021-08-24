
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from libtaxman.collector import BaseCollector
from gdata_subm import Gdata
from typing import List

import logging
import multiprocessing as mp
import re
import subprocess as sp


LOSS_REG = re.compile(r'([\d\.]+)% packet loss')
LAT_REG = re.compile(r'time=(\S+)\s')


@dataclass
class PingResult:
    latency: float
    loss: float


class PingCollector(BaseCollector):

    def get_data_for_sub(self) -> Gdata:
        health = None
        try:
            health = self._get_health()
        except Exception:
            logging.exception("Failed to get health in httpcheck")
            return None

        ret = []

        for host, results in health.items():
            lats = [r.latency for r in results]
            ret.append(
                Gdata(
                    plugin='ping',
                    dtype=host,
                    dstypes=['gauge'] * len(lats),
                    values=lats,
                    dsnames=['lat'] * len(lats),
                    interval=int(self.config['interval']),
                )
            )
            ret.append(
                Gdata(
                    plugin='ping',
                    dtype=host,
                    dstypes=['gauge'],
                    values=[results[0].loss],
                    dsnames=['loss'],
                    interval=int(self.config['interval']),
                )
            )

        return ret

    def _get_health(self):
        """
        This will check the health of all the sites in parallel
        """
        ret = {}
        workers = int(self.config['max_workers'])
        hosts = [s.strip() for s in self.config['hosts'].split('\n')
            if s.strip()]
        '''
        args = [(h, int(self.config['interval']), self.config['binary'])
            for h in hosts]
        with mp.Pool(len(hosts)) as pool:
            results = pool.starmap(_get_ping_results, args)
            return dict(zip(hosts, results))
        '''
        with ThreadPoolExecutor(max_workers=workers) as exe:
            fut_to_host = {
                exe.submit(_get_ping_results,
                    h, self.config['interval'], self.config['binary']): h
                for h in hosts
            }

            for fut in as_completed(fut_to_host.keys()):
                host = fut_to_host[fut]

                try:
                    results = fut.result()
                except Exception as e:
                    logging.exception(
                        f'Failed to get a response for {host}')
                    continue

                ret[host] = results

        return ret


def _get_ping_results(host, interval, binary) -> List[PingResult]:
    ret = []
    deadline = '{}'.format(int(interval) - 1)
    cmd = [
        binary,
        '-c', deadline,
        '-w', deadline,
        host,
    ]
    res = sp.run(cmd, stdout=sp.PIPE, stderr=sp.DEVNULL, encoding='utf-8')
    lines = res.stdout.strip().split('\n')


    loss_perc = 0.0
    for line in lines[-3:]:
        m = LOSS_REG.search(line)
        if m:
            loss_perc = float(m.group(1))
            break

    for line in lines:
        m = LAT_REG.search(line)
        if m:
            lat = float(m.group(1))
            ret.append(PingResult(
                latency=lat,
                loss=loss_perc,
            ))

    return ret
