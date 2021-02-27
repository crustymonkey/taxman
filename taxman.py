#!/usr/bin/env python3

import logging
import os
import sys
from argparse import ArgumentParser
from libtaxman.config import TaxmanConfig
from libtaxman.manager import CollectorManager


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


def main():
    args = get_args()
    setup_logging(args)

    conf = get_conf(args)

    mgr = CollectorManager(conf)
    mgr.run()

    return 0


if __name__ == '__main__':
    sys.exit(main())
