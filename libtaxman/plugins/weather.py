
from collections import defaultdict
from gdata_subm import Gdata
from libtaxman.collector import BaseCollector
from urllib.parse import urlencode
from urllib.request import urlopen

import json
import logging
import os


class WeatherCollector(BaseCollector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._url = '{}/{}'.format(
            self.config['base_url'].rstrip('/'),
            self.config['base_path'].rstrip('/'),
        )

        self.city_data = defaultdict(list)
        self._load_city_data()

        self.cities = {}
        self._populate_cities()

    def get_data_for_sub(self) -> Gdata:
        ret = None
        tmp = {}
        try:
            for norm_city, city in self.cities.items():
                data = self._get_remote_data_by_id(city['_id'])
                tmp[norm_city] = data
        except Exception:
            logging.exception("Failed to get weather data")
            return None
        
        dtype_inst = 'temp_f' if self.config['units'] == 'imperial' \
            else 'temp_c'

        return Gdata(
            plugin='weather',
            dstypes=['gauge'] * len(tmp),
            values=[v['main']['temp'] for v in tmp.values()],
            dsnames=list(tmp.keys()),
            dtype_instance=dtype_inst,
            interval=int(self.config['interval']),
        )

    def _get_remote_data_by_id(self, city_id):
        """
        Queries the remote service for the city data
        """
        req_dict = {
            'id': city_id,
            'APPID': self.config['api_key'],
            'units': self.config['units'],
        }
        url = f'{self._url}?{urlencode(req_dict)}'
        res = urlopen(url, timeout=55)
        
        if res.status < 200 or res.status >= 300:
            logging.error(
                f'Failed to get weather info with status {res.status}'
            )

        return json.loads(res.read().decode('utf-8'))

    def _load_city_data(self):
        """
        Loads the city location data from a file.  This is used for the queries
        """
        path = os.path.join(
            self.config['data_dir'],
            self.config['data_file'],
        )
        with open(path) as fh:
            for line in fh:
                o = json.loads(line)
                self.city_data[o['name'].lower()].append(o)

    def _populate_cities(self):
        """
        This will populate self.cities with a list of city dictionaries.
        These are what we will be gathering data for
        """
        # First, get the cities by name
        city_names = [s.strip() for s in self.config['cities'].split(';')]
        for city_country in city_names:
            city, country = [s.strip() for s in city_country.split(',')]
            lcity = city.lower()
            if lcity in self.city_data:
                for item in self.city_data[lcity]:
                    if item['country'].lower() == country.lower():
                        norm_name = '{}_{}'.format(
                            lcity.replace(' ', '_'),
                            country.lower(),
                        )
                        self.cities[norm_name] = item
                        break
            else:
                logging.warning(f'Configured city "{city}" not found in '
                    'the city data')

        # Now go through the ones with explicit IDs
        city_names = [s.strip() for s in self.config['city_ids'].split(';')]
        for city_country_id in city_names:
            city, country, cid = [s.strip() for s in city_country_id.split(',')]
            lcity = city.lower()
            if lcity in self.city_data:
                for item in self.city_data[lcity]:
                    if int(item['_id']) == int(cid):
                        norm_name = '{}_{}'.format(
                            lcity.replace(' ', '_'),
                            country.lower(),
                        )
                        self.cities[norm_name] = item
                        break
            else:
                logging.warning(f'Configured city "{city}" not found in '
                    'the city data')
