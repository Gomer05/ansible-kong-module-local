import uuid
from kong import Kong
from kong.service import KongService
from kong.route import KongRoute
from kong.consumer import KongConsumer
from six import iteritems


class KongPlugin(KongRoute, KongConsumer, KongService, Kong):
    """
    KongPlugin manages Plugin objects in Kong.
    Uses KongServie, KongRoute and KongConsumer as mixins to query Services, Routes
    and Consumers.
    """

    @staticmethod
    def _prepare_config(config):
        """
        Takes a dictionary and prefixes the keys with 'config.'.
        The Kong Plugin endpoint does not support a native dictionary for config.

        :param config: the input config dictionary
        :type config: dict
        :return: dictionary with keys prefixed with 'config.'
        :rtype: dict
        """

        return {'config.' + k: v for k, v in iteritems(config)}

    def plugin_list(self):
        """
        Get a list of Plugins configured in Kong.

        :return: a dictionary of Plugin info
        :rtype: dict
        """

        return self._get('plugins')

    def plugin_query(self, name, service_name=None, route_name=None, consumer_name=None, plugin_id=None):
        """
        Query Kong for a Plugin matching the given properties.
        Raises requests.HTTPError and ValueError.

        :param plugin_id: 'id' field (UUID)
        :type plugin_id: str
        :param name: 'name' field
        :type name: str
        :param service_name: name of the Service to resolve
        :type service_name: str
        :param route_name:  name or id of the Route to resolve
        :type route_name: str
        :param consumer_name: name of the Consumer to resolve
        :type consumer_name: str
        :return: dictionary with 'total' and 'data' keys
        :rtype: dict
        """

        service_id = None
        route_id = None
        consumer_id = None

        if plugin_id is name is None:
            raise ValueError("Need at least one of 'plugin_id' or 'name'")

        uri = ['plugins']
        if plugin_id:
            uri = ['plugins', plugin_id]

        if service_name:
            uri = ['services', service_name, 'plugins']
            # Check if Service exists
            service_name = self.service_get(service_name)
            service_id = service_name.get('id')
            uuid.UUID(service_id)
            if service_name is None:
                raise ValueError("Service '{}' not found. Has it been created?".format(service_name))

        if route_name:
            uri = ['routes', route_name, 'plugins']
            # Check if Route exists
            route_name = self.route_get(route_name)
            route_id = route_name.get('id')
            uuid.UUID(route_id)
            if route_name is None:
                raise ValueError("Route '{}' not found. Has it been created?".format(route_name))

        if consumer_name:
            uri = ['consumers', consumer_name, 'plugins']
            consumer_name = self.consumer_get(consumer_name)
            consumer_id = consumer_name.get('id')
            uuid.UUID(consumer_id)
            if consumer_name is None:
                raise ValueError('Consumer {} not found. Has it been created?'.format(consumer_name))

        # Can raise requests.HTTPError
        plugins = res = self._get(uri)
        while res['next']:
            uri = res['next'].strip('/')
            res = self._get(uri)
            plugins['data'] += res['data']

        result = []

        for plugin in plugins['data']:

            plugin_consumer = plugin.get('consumer')
            plugin_service = plugin.get('service')
            plugin_route = plugin.get('route')
            # print(f"consumer: {plugin_consumer}, service: {plugin_service}, route: {plugin_route}")

            if plugin.get('name') != name:
                continue

            # Require the Plugin's consumer to be set if consumer is provided.
            if bool(plugin_consumer) != bool(consumer_id):
                continue
            # Require the Plugin's consumer ID to match if given.
            if plugin_consumer and plugin_consumer.get('id') != consumer_id:
                continue

            # Require the Plugin's service to be set if service is provided.
            if bool(plugin_service) != bool(service_id):
                continue
            # Require the Plugin's service ID to match if given.
            if plugin_service and plugin_service.get('id') != service_id:
                continue

            # Require the Plugin's route to be set if route is provided.
            if bool(plugin_route) != bool(route_id):
                continue
            # Require the Plugin's route ID to match if given.
            if plugin_route and plugin_route.get('id') != route_id:
                continue

            result.append(plugin)

        return result

    def plugin_apply(self, name, config=None, service_name=None, route_name=None, consumer_name=False):
        """
        Idempotently apply the Plugin configuration on the server.
        See Kong API documentation for more info on the arguments of this method.

        We want to manage one resource at a time only. If consumer_name is not given
        to this function, we want to eliminate entries from the plugin query that have
        `consumer_id` set. This behaviour is triggered by setting `consumer_name=False`
        to plugin_query().

        :param name: name of the Plugin to configure
        :type name: str
        :param config: configuration parameters for the Plugin
        :type config: dict
        :param service_name: name of the Service to configure the Plugin on
        :type service_name: str
        :param route_name: name of id of the Route to configure the Plugin on
        :type route_name: str
        :param consumer_name: name of the Consumer to configure the plugin for
        :type consumer_name: str
        :return: whether the Plugin resource was touched or not
        :rtype: bool
        """

        data = {
            'name': name,
        }

        if config is not None:
            if not isinstance(config, dict):
                raise ValueError("'config' parameter is not a dict")
            # merge config entries into payload
            data.update(self._prepare_config(config))

        if service_name:
            s = self.service_get(service_name)
            if s is None:
                raise ValueError("Service '{}' not found".format(service_name))

            data['service.id'] = s['id']

        if route_name:
            r = self.route_get(route_name)
            if r is None:
                raise ValueError("Route '{}' not found".format(route_name))

            data['route.id'] = r['id']

        if consumer_name:
            c = self.consumer_get(consumer_name)
            if c is None:
                raise ValueError(
                    "Consumer '{}' not found".format(consumer_name))

            data['consumer.id'] = c['id']

        # Query the plugin with the given attributes.
        p = self.plugin_query(name=name, service_name=service_name,
                              route_name=route_name, consumer_name=consumer_name)

        if len(p) > 1:
            raise ValueError("Multiple Plugin records for name: '{}', service: '{}', route: '{}', consumer: '{}'".
                             format(name, service_name, route_name, consumer_name))

        if p:
            # Update existing Plugin.
            return self._patch(['plugins', p[0].get('id')], data=data)

        # Insert new Plugin.
        return self._post(['plugins'], data=data)

    def plugin_delete(self, name, service_name=None, route_name=None, consumer_name=False):
        """
        Delete the API if it exists.

        :param name: name of the API to remove the Plugin configuration from
        :type name: str
        :param consumer_name: name of the Consumer to delete the Plugin from
        :type consumer_name: str
        :param route_name: attributes of the Route to delete the Plugin from
        :type route_name: dict
        :param service_name: name of the Service to delete the Plugin from
        :type service_name: str
        :return: True on a successful delete, False if no action taken
        :rtype: bool
        """

        p = self.plugin_query(name=name, service_name=service_name,
                              route_name=route_name, consumer_name=consumer_name)
        if len(p) > 1:
            raise ValueError("Found multiple Plugin records for name: '{}', service: '{}', route: '{}', consumer: '{}'".
                             format(name, service_name, route_name, consumer_name))

        # Delete the Plugin configuration if it exists
        if p:
            return self._delete(['plugins', p[0].get('id')])

        return False
