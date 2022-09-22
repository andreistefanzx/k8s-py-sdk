from kubernetes import client, config
import logging
import time


class K8sClass:

    """
    Deletes Pods in Pending state across all namespaces that have error message in Events.
    """

    config.load_incluster_config()  # inside cluster authentication
    # config.load_kube_config()   # outside cluster authentication
    logging.basicConfig(format='%(levelname)s:%(asctime)s:%(message)s', level=logging.INFO)

    def __init__(self):

        # Init Kubernetes
        self.core_api = client.CoreV1Api()
        self.namespaces = []
        self._k8s_client_connected = False

    def _initialise_client(self):
        if not self._k8s_client_connected:
            try:
                client.CoreV1Api
            except Exception as e:
                logging.info(e)
                raise
            else:
                logging.debug('Connection to K8s client was established.')
                self._k8s_client_connected = True
                return True
        else:
            return True

    def get_namespaces(self):
        """"Returns a list of namespaces in the cluster."""
        if self._initialise_client():
            try:
                result = self.core_api.list_namespace()
            except Exception as e:
                logging.info(e)
                raise
            else:
                for i in result.items:
                    self.namespaces.append(i.metadata.name)
            logging.debug(f'Namespaces: {self.namespaces}')
            return self.namespaces
        else:
            logging.info('Connection to K8s client failed.')

    def verify_pod_exists(self, pod_name, pod_namespace):
        """
        Verifies if Pod exists.
        returns: bool
        """
        if self._initialise_client():
            logging.debug(f'Verifies if Pod {pod_namespace}/{pod_name} exists.')
            try:
                self.core_api.read_namespaced_pod(pod_name, pod_namespace)
            except Exception as e:
                logging.debug(e)
                return False
            else:
                return True
        else:
            logging.info('Connection to K8s client failed.')

    def delete_pending_pod(self, pod_name, pod_namespace):
        """Deletes Pod."""
        if self._initialise_client():
            try:
                self.core_api.delete_namespaced_pod(pod_name, pod_namespace)
            except Exception as e:
                logging.info(e)
                raise
            else:
                logging.info(f'Deleted Pod {pod_namespace} in namespace {pod_namespace}')
        else:
            logging.info('Connection to K8s client failed.')

    def get_pod_status(self, pod_name, pod_namespace):
        """"Returns Pod status."""
        if self._initialise_client():
            logging.debug(f'Getting {pod_namespace}/{pod_name} Pod status')
            try:
                result = self.core_api.read_namespaced_pod_status(pod_name, pod_namespace)
            except Exception as e:
                logging.info(e)
                raise
            else:
                pod_status = result.status.phase
                logging.debug(f' Pod {pod_namespace}/{pod_name} status is: {pod_status}')
                return pod_status
        else:
            logging.info('Connection to K8s client failed.')

    def get_pods_with_error_event(self, error_message):
        """
        Returns a list of existing Pods with error message in events.
        return: {(pod_name, pod_namespace),...}
        """
        if self._initialise_client():
            self.namespaces = self.get_namespaces()
            errored_pods = []
            for namespace in self.namespaces:
                try:
                    result = self.core_api.list_namespaced_event(namespace)
                except Exception as e:
                    logging.info(e)
                    raise
                else:
                    for i in result.items:
                        if error_message in i.message:
                            event_type = i.type
                            event_reason = i.reason
                            event_message = i.message
                            event_pod = i.involved_object.name
                            event_namespace = i.involved_object.namespace
                            logging.debug(f'{event_type} {event_reason} {event_pod} {event_namespace} \n{event_message}')
                            if self.verify_pod_exists(event_pod, event_namespace):
                                errored_pods.append((event_pod, event_namespace))
                            else:
                                logging.debug(f"Pod {event_pod} in namespace {event_namespace} doesn't exist anymore!")
            if len(errored_pods) > 0:
                logging.info(f'There are {len(errored_pods)} Pods with Error Event {error_message} in Pending state: \n{errored_pods}')
            else:
                logging.info(f'There are {len(errored_pods)} Pods with Error Event {error_message} in Pending state.')
            return errored_pods
        else:
            logging.info('Connection to K8s client failed.')

    def delete_pending_pods(self, error_message):
        """Deletes Pending Pods with error message from all namespaces."""
        if self._initialise_client():
            pods_in_pending_state = self.get_pods_with_error_event(error_message)
            if len(pods_in_pending_state) >= 1:
                for pod_name, pod_namespace in pods_in_pending_state:
                    # verify Pod exists
                    if self.verify_pod_exists(pod_name, pod_namespace):
                        # delete Pod if in Pending state
                        if self.get_pod_status(pod_name, pod_namespace) == 'Pending':
                            self.delete_pending_pod(pod_name, pod_namespace)
                    else:
                        logging.info(f"Pod {pod_name} in namespace {pod_namespace} doesn't exist anymore!")
        else:
            logging.info('Connection to K8s client failed.')


def main():

    error_message = 'Failed to pull image "wrongimage"'
    sleep_time = 30
    while True:
        job = K8sClass()
        # job.get_pods_with_error_event(error_message)
        job.delete_pending_pods(error_message)
        time.sleep = sleep_time


if __name__ == '__main__':
    main()