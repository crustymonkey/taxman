
from collections import defaultdict
from gdata_subm import Gdata
from libtaxman.collector import BaseCollector
from typing import Dict
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
        aqi_types = []
        try:
            for norm_city, city in self.cities.items():
                wthr_data = self._get_remote_data_by_id(city['_id'])
                aqi_data = self._get_remote_aqi_data(
                    city['coord']['lat'],
                    city['coord']['lon'],
                )
                aqi_types = list(aqi_data.keys()) if aqi_types == [] else []
                if wthr_data and aqi_data:
                    tmp[norm_city] = {'weather': wthr_data, 'aqi': aqi_data}
        except Exception as e:
            logging.exception(f"Failed to get weather/aqi data: {e}")
            return None

        dtype_inst = 'temp_f' if self.config['units'] == 'imperial' \
            else 'temp_c'

        ret = [
            Gdata(
                plugin='weather',
                dstypes=['gauge'] * len(tmp),
                values=[v['main']['temp'] for v in tmp['weather'].values()],
                dsnames=list(tmp.keys()),
                dtype_instance=dtype_inst,
                interval=int(self.config['interval']),
            ),
        ]

        for dtype_inst in aqi_types:
            ret.append(Gdata(
                plugin='weather',
                dstypes=['gauge'] * len(tmp),
                values=[v[dtype_inst] for v in tmp['aqi'].values()],
                dsnames=list(tmp.keys()),
                dtype_instance=dtype_inst,
                interval=int(self.config['interval']),
            ))

        return ret

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
        res = urlopen(url, timeout=10)

        if res.status < 200 or res.status >= 300:
            logging.error(
                f'Failed to get weather info with status {res.status}'
            )
            return None

        return json.loads(res.read().decode('utf-8'))

    def _get_remote_aqi_data(lat: float, lon: float) -> Dict[str, float]:
        ret = {}
        req_dict = {
            'APPID': self.config['api_key'],
            'lat': lat,
            'lon': lon,
        }

        url = f'{self._url}?{urlencode(req_dict)}'
        res = urlopen(url, timeout=10)

        if res.status < 200 or res.status >= 300:
            logging.error(
                f'Failed to get aqi info with status {res.status}'
            )
            return None

        # Pull what I want out of the raw data
        data = json.loads(res.read().decode('utf-8'))
        ret['aqi'] = data['list'][0]['main']['aqi']
        ret.update(data['list'][0]['components'])

        return ret

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
