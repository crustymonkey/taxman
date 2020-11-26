
from configparser import ConfigParser

class TaxmanConfig(ConfigParser):
    def get_list(self, section, name):
        raw = self.get(section, name)
        return [s.strip() for s in raw.split()]
