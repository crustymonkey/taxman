
from concurrent.futures import ThreadPoolExecutor, as_completed
from configparser import SectionProxy
from dataclasses import dataclass
from gdata_subm import Gdata, GdataSubmit
from importlib import import_module
from libtaxman.collector import BaseCollector
from libtaxman.config import TaxmanConfig
from libtaxman.errors import InvalidConfig
from typing import Any, List

import logging
import time


@dataclass
class PluginInfo:
    name: str
    inst: Any
    data: List[Gdata]


class CollectorManager:
    PLUGIN_BASE = 'libtaxman.plugins'

    def __init__(self, config: TaxmanConfig):
        self.config = config
        self.plugins = {}
        self._stop = False
        self._next_submit = self._get_next_submit()
        self._submitter = GdataSubmit(
            url=self.config['main']['submission_url'],
            username=self.config['main']['submission_username'],
            password=self.config['main']['submission_password'],
        )
        self._init_plugins()

    def run(self):
        while not self._stop:
            to_run = []
            now = time.time()
            for pi: PluginInfo in self.plugins.values():
                if pi.inst.next_sched > now:
                    to_run.append(pi)

            if to_run:
                # We have some plugins to be run
                w = self.config.getint('main', 'max_workers')
                self._get_data_from_plugins(to_run, w)
            
            if self._next_submit < now:
                self._submit_all_data()

    def stop(self):
        self._stop = True

    def _submit_all_data(self):
        """
        Submit all of our accumulated data to the server
        """
        to_sub = []
        for pi in self.plugins.values():
            to_sub.extend(pi.data)
            pi.data = []

        self._submitter.send_data(to_sub)

    def _get_data_from_plugins(self, to_run: List[PluginInfo], workers: int):
        """
        This will concurrently get the data from all the plugins and then
        schedule the next run of the plugin based on its interval
        """
        with ThreadPoolExecutor(max_workers=workers) as exe:
            fut_to_pi = {exe.submit(pi.get_data_for_sub): pi 
                for pi in to_run}
            for fut in as_completed:
                pi = fut_to_pi[fut]
                try:
                    pi.data.append(fut.result())
                except Exception as e:
                    logging.warning(
                        f'Failed to get data from plugin {pi.name}: {e}')
                finally:
                    pi.inst.sched_next()


    def _get_next_submit(self) -> float:
        """
        This just figures out when we should next submit data
        """
        now = time.time()
        return now + (60 - (now % 60))

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
            self.plugins[pname] = PluginInfo(
                name=pname,
                inst=inst,
                data=[]
            )
            logging.debug(f'Successfully initialized plugin: {pname}')

    def _get_plug_inst(self, plug_name: str, sp: SectionProxy) -> BaseCollector:
        """
        This is a convenience function to get the plugin class instance
        by string name
        """
        mod = import_module(f'{self.PLUGIN_BASE}.{plug_name}')
        klass = getattr(mod, sp['name'])

        return klass(sp)
