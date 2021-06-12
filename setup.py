#!/usr/bin/env python3

from setuptools import setup
import os

def get_requirements():
    cur_dir = os.path.dirname(__file__)
    with open(os.path.join(cur_dir, 'requirements.txt')) as fh:
        return [s.strip() for s in fh.readlines() if s.strip()]

setup(
    name='taxman',
    version='0.2.7',
    author='Jay Deiman',
    author_email='admin@splitstreams.com',
    description=(
        'A customizable data submitter compatible with collectd\'s '
        'write_http module'
    ),
    license='GPLv2',
    keywords='grafana http',
    packages=['libtaxman'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Programming Language :: Python :: 3',
        'Topic :: System :: Monitoring',
    ],
    scripts=['taxman.py'],
    include_package_data=True,
    package_data={'': [
        'taxman.ini.default',
        'tsd.sql',
        'LICENSE',
        'README.md',
        'plugin_data',
    ]},
)
