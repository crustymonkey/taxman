#
# This is a library for getting stats from proc files in different formats
#

import re


class UnsupportedDataFormat(Exception):
    pass


def get_stats_for_file(fname: str):
    with open(fname) as fh:
        line = fh.readline()
        for regex, func in FIRST_LINE_MATCH.items():
            if regex.search(line):
                return func(fname)

    raise UnsupportedDataFormat(f'Did not match a line format for file: {fname}')


def _get_netstat_file(fname: str):
    """
    This will return data for a file in the format of /proc/net/netstat
    """
    ret = {}
    with open(fname) as fh:
        for i, line in enumerate(fh):
            prefix, data = [s.strip() for s in line.split(':')]

            if i % 2 == 0:
                # Keys
                keys = [s.strip() for s in data.split()]
            else:
                # Values
                values = [s.strip() for s in data.split()]
                ret[prefix] = dict(zip(keys, values))

    return ret


# This is a map to first line regex -> func pointer
FIRST_LINE_MATCH = {
    re.compile(r'^\w+:\s+[a-zA-Z[\w\s]+$'): _get_netstat_file,
}
