
from gdata_subm import Gdata
from libtaxman.collector import BaseCollector
from kubernetes import client, config


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
                # Get the nanocpu value
                ret[f'{base_name}.cpu'] = \
                    float(cont["cpu"].rstrip('n')) / 1_000_000_000
                # Convert to bytes
                ret[f'{base_name}.mem'] = float(cont["memory"][:-2]) * 1024

        return ret
