
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from libtaxman.collector import BaseCollector
from gdata_subm import Gdata
from typing import List

import logging
import re
import socket

@dataclass
class ConnTest:
    host: str
    ip_vers: int
    proto: str
    port: int
    timeout: float
    to_send: bytes
    exp_resp: re.Pattern

class ConnTestCollector(BaseCollector):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tests = self._get_tests()
        self.name_map = {self._get_name(t): t for t in self.tests}

    def get_data_for_sub(self) -> Gdata:
        health = None
        try:
            health = self._get_health()
        except Exception:
            logging.exception("Failed to get health in conntest")
            return None

        return [
            Gdata(
                plugin='conncheck',
                dstypes=['gauge'] * len(health),
                values=list(health.values()),
                dsnames=list(health.keys()),
                interval=int(self.config['interval']),
            ),
        ]

    def _get_name(self, test: ConnTest):
        name = (
            f'{test.host.replace(".", "_")}:'
            f'{test.ip_vers}:{test.proto}:{test.port}'
        )

        return name

    def _get_health(self):
        """
        This will check the health of all the sites in parallel
        """
        ret = {}
        workers = int(self.config['max_workers'])
        with ThreadPoolExecutor(max_workers=workers) as exe:
            fut_to_test = {
                exe.submit(self._get_conn_result, t): t
                for t in self.tests
            }

            for fut in as_completed(fut_to_test.keys()):
                test = fut_to_test[fut]

                res = 0
                try:
                    res = fut.result()
                except Exception as e:
                    logging.warning(
                        f'Failed to get a response for {test}: {e}')

                ret[self._get_name(test)] = res

        return ret

    def _get_conn_result(self, test: ConnTest) -> int:
        """
        Returns a 1 on success, 0 otherwise
        """
        fam = socket.AF_INET if test.ip_vers == 4 else socket.AF_INET6
        stype = socket.SOCK_STREAM if test.proto == 'tcp' else socket.SOCK_DGRAM
        addr = (test.host, test.port) if test.ip_vers == 4 else \
            (test.host, test.port, 0, 0)

        sock = socket.socket(fam, stype)
        sock.settimeout(test.timeout)
        try:
            sock.connect(addr)
        except Exception:
            logging.debug(f'Failed to connect to {test}')
            return 0

        try:
            if test.to_send is not None:
                sock.sendall(test.to_send)

            if test.exp_resp is not None:
                resp = sock.recv(4096)
                if test.exp_resp.search(resp.decode('utf-8', errors='ignore')):
                    return 1
        except Exception as e:
            sock.close()
            logging.info(f'Failed the send/resp portion of: {test}')
            return 0

        sock.close()
        return 1

    def _get_tests(self) -> List[ConnTest]:
        ret = []
        checks = [s.strip() for s in self.config['checks'].split('\n')
            if s.strip()]

        for check in checks:
            chk = self._validate_and_get_check(check)
            if chk is not None:
                ret.append(chk)

        return ret

    def _validate_and_get_check(self, check_str) -> ConnTest:
        c = check_str.split(';')
        if c[2].lower() not in ('tcp', 'udp'):
            logging.warning(f'Invalid proto for test, skipping: {check_str}')
            return None

        if len(c) < 5:
            logging.warning(f'Invalid test, skipping: {check_str}')
            return None

        if c[2].lower() == 'udp' and (len(c) < 7):
            logging.warning(
                'Invalid UDP test, you must supply a send and resp: '
                f'{check_str}'
            )
            return None

        try:
            ip_v = int(c[1])
        except Exception:
            logging.warning(f'Invalid IP version, must be an int: {check_str}')
            return None
        if ip_v not in (4, 6):
            logging.warning(
                f'Invalid IP version, must be 4 or 6: {check_str}')
            return None

        try:
            port = int(c[3])
        except Exception:
            logging.warning(f'Invalid test, port is not an int: {check_str}')
            return None

        try:
            timeout = float(c[4])
        except Exception:
            logging.warning(
                f'Invalid test, timeout is not a float: {check_str}')
            return None

        to_send = None
        resp_reg = None
        if len(c) > 5:
            to_send = c[5]
        if len(c) > 6:
            resp_reg = re.compile(c[6])

        return ConnTest(
            host=c[0],
            ip_vers=ip_v,
            proto=c[2].lower(),
            port=port,
            timeout=timeout,
            to_send=to_send.encode('utf-8'),
            exp_resp=re.compile(resp_reg),
        )
