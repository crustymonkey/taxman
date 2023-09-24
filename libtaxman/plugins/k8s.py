
import logging
import string
from gdata_subm import Gdata
from libtaxman.collector import BaseCollector
from kubernetes import client, config


CPU_CONV = {
    'm': 1_000,
    'n': 1_000_000_000,
    'u': 1_000_000_000_000,
}


class K8sCollector(BaseCollector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        config.load_config(config_file=self.config['conf_file'])
        self.hostname = self.config['hostname']

    def get_data_for_sub(self) -> Gdata:
        tmp = self.get_session_counts()

        if not tmp:
            tmp['total'] = 0

        return Gdata(
            plugin='k8s',
            dstypes=['gauge'] * len(tmp),
            values=list(tmp.values()),
            dsnames=list(tmp.keys()),
            dtype_instance='pods',
            host=self.hostname,
            interval=int(self.config['interval']),
        )

    def get_session_counts(self):
        ret = {}

        pods = client.CustomObjectsApi().list_cluster_custom_object(
            'metrics.k8s.io',
            'v1beta1',
            'pods',
        )

        for entry in pods['items']:
            base_name = (
                f'{entry["metadata"]["namespace"]}.'
                f'{entry["metadata"]["name"]}'
            )

            for cont in entry['containers']:
                # Get the cpu value
                logging.debug(f'Got raw cpu value of {cont["usage"]["cpu"]}')
                raw_cpu = cont['usage']['cpu']
                if raw_cpu[-1] not in string.ascii_lowercase:
                    cval = float(raw_cpu)
                else:
                    cnum = cont['usage']['cpu'][:-1]
                    cunit = cont['usage']['cpu'][-1]
                    if cunit not in CPU_CONV:
                        logging.warning(f'Unknown CPU unit for k8s: {cunit}')
                        cval = float(cnum)
                    else:
                        cval = float(cnum) / CPU_CONV[cunit]

                ret[f'{base_name}.cpu'] = cval

                # Convert to bytes
                ret[f'{base_name}.mem'] = \
                    float(cont["usage"]["memory"][:-2]) * 1024

        logging.debug(f'Collected from k8s: {ret}')

        return ret
