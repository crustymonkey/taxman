
from configparser import SectionProxy
from dataclasses import dataclass
from importlib import import_module
from libtaxman.collector import BaseCollector
from libtaxman.config import TaxmanConfig
from libtaxman.errors import InvalidConfig
from libtaxman.submitter import Submitter
from queue import Queue
from typing import Any, List

import logging
import time


@dataclass
class PluginInfo:
    name: str
    inst: Any


class CollectorManager:
    PLUGIN_BASE = 'libtaxman.plugins'

    def __init__(self, config: TaxmanConfig):
        self.config = config
        self.plugins = {}
        self._stop = False
        self._submitter = None
        self._res_q = Queue()
        self._init_submitter()
        self._init_plugins()

    def run(self):
        while not self._stop:
            now = time.time()
            for pi in self.plugins.values():
                if pi.inst.next_sched <= now:
                    pi.inst.run_now()

            sl_time = self._get_next_sleep()
            logging.debug(f'Sleeping for {sl_time:.02f}')
            time.sleep(sl_time)

        # If we get here, stop was set so we stop the plugin threads and
        # the submitter
        self._stop_all()

    def stop(self):
        self._stop = True

    def _stop_all(self):
        """
        Stop all other threads
        """
        for pi in self.plugins.values():
            pi.inst.stop()

        self._submitter.stop()

    def _get_next_sleep(self):
        """
        Calculate how long we need to sleep based on when a plugin is
        next scheduled to run
        """
        now = time.time()

        sl_time = 60
        for pi in self.plugins.values():
            tmp = pi.inst.next_sched - now
            # Make sure we're not going backwards
            tmp = 0.1 if tmp < 0.1 else tmp

            if tmp < sl_time:
                sl_time = tmp

        return sl_time

    def _init_submitter(self):
        self._submitter = Submitter(self._res_q, self.config)
        self._submitter.start()

    def _init_plugins(self):
        """
        Initialize and register all the enabled plugins
        """
        # Loop over the enabled plugins
        for pname in self.config.get_list('main', 'plugins_enabled'):
            # First, validate the config data
            if not self.config.has_section(pname):
                raise InvalidConfig(
                    f'Enabled plugin "{pname}" does not have a '
                    'corresponding config section'
                )
            if not self.config.has_option(pname, 'name'):
                raise InvalidConfig(
                    f'Enabled pluging "{pname}" does not have a config entry '
                    'for the "name" of the plugin class'
                )

            # If we get here, we should have a valid config for the plugin
            sp = self.config[pname]  # Returns a SectionProxy
            logging.debug(f'Initializing plugin: {pname}')
            inst = self._get_plug_inst(pname, sp)
            if not inst:
                logging.error(f'Gave up on initializing {pname}')
                continue

            inst.start()
            self.plugins[pname] = PluginInfo(
                name=pname,
                inst=inst,
            )
            logging.debug(f'Successfully initialized plugin: {pname}')

    def _get_plug_inst(self, plug_name: str, sp: SectionProxy) -> BaseCollector:
        """
        This is a convenience function to get the plugin class instance
        by string name
        """
        ret = None
        mod = import_module(f'{self.PLUGIN_BASE}.{plug_name}')
        klass = getattr(mod, sp['name'])

        max_retries = 5
        tries = 0
        while tries < max_retries:
            # Try to get the plugin instance while catching any startup
            # exceptions
            tries += 1
            try:
                ret = klass(self._res_q, sp)
            except Exception:
                logging.exception(f'Failed to initialize plugin {plug_name}')
                time.sleep(tries ** 2)
            else:
                break

        return ret
