#!/usr/bin/env python3

from configparser import ConfigParser, SectionProxy
from gdata_subm import Gdata
from typing import List, Union
import time


class BaseCollector:
    """
    This is the base collector class that should be used for plugins
    """
    def __init__(self, config: SectionProxy):
        self.config = config  # This is the relevant section of the config
        self.next_sched = time.time()

    def sched_next(self) -> None:
        self.next_sched += int(self.config['interval'])
    
    def get_data_for_sub(self) -> Union[Gdata, List[Gdata]]:
        """
        This is called to get the data for upstream submission and should
        return a Gdata object
        """
        raise NotImplementedError()
        
