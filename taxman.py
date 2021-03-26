#!/usr/bin/env python3

import logging
import os
import sys
from argparse import ArgumentParser
from libtaxman.config import TaxmanConfig
from libtaxman.manager import CollectorManager
from signal import signal, SIGINT, SIGTERM, SIGHUP

MANAGER = None


def get_args():
    p = ArgumentParser()
    p.add_argument('-c', '--config', default='/etc/taxman/taxman.ini',
        help='The path to the config file [default: %(default)s]')
    p.add_argument('-D', '--debug', action='store_true', default=False,
        help='Add debug output [default: %(default)s]')

    args = p.parse_args()

    return args


def get_conf(args):
    conf = TaxmanConfig(allow_no_value=True)
    conf.read(args.config)

    if 'APPDIR' in os.environ:
        conf['DEFAULT']['data_dir'] = os.path.join(
            os.environ['APPDIR'],
            'plugin_data',
        )

    return conf


def setup_logging(args):
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        format=(
            '%(asctime)s - %(levelname)s - '
            '%(filename)s:%(lineno)d %(funcName)s - %(message)s'
        ),
        level=level,
    )


def sig_handler(num, frame):
    MANAGER.stop()


def setup_signals():
    for sig in (SIGINT, SIGTERM, SIGHUP):
        signal(sig, sig_handler)

def main():
    global MANAGER
    args = get_args()
    setup_logging(args)
    setup_signals()

    conf = get_conf(args)
    
    mgr = CollectorManager(conf)
    MANAGER = mgr
    mgr.run()

    return 0


if __name__ == '__main__':
    sys.exit(main())
