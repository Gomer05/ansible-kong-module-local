import requests


DOCUMENTATION = '''
---
Basic Class used by kong_service and kong_route
'''


class Kong(object):

    # List of API resources the library supports
    resources = [
        '',
        'apis',
        'certificates',
        'consumers',
        'plugins',
        'routes',
        'services',
        'status',
    ]

    def __init__(self, base_url, auth_user=None, auth_pass=None, ping=True):

        self.base_url = base_url

        self.auth = None

        self.headers = {}

        # set basic auth tuple if credentials given
        if auth_user is not None and auth_pass is not None:
            self.auth = (auth_user, auth_pass)
            self.headers["Kong-Admin-Token"] = auth_pass

            # self-check by making status call to Kong
        if ping and self.status:
            return

    def _get(self, uri, params=None):
        """
        Execute GET request using the resource and action.
        """
        url = self._url(uri)

        r = requests.get(url, params=params, auth=self.auth, headers=self.headers)

        # Expect 200 OK
        r.raise_for_status()

        return r.json()

    def _post(self, uri, data=None, headers=None):
        """
        Execute POST request using the resource, action and payload.
        """
        if headers and isinstance(headers, dict):
            self.headers.update(headers)

        url = self._url(uri)

        r = requests.post(url, data=data, auth=self.auth, headers=self.headers)

        if r.status_code == requests.codes.created:
            return r.json()
        else:
            raise Exception('Unexpected HTTP code {}, expected {} on url {}, error: {}, data: {}'
                            .format(r.status_code, requests.codes.created, url, r.json(), data))

    def _patch(self, uri, data=None, headers=None):
        """
        Execute PATCH request using the resource, action and payload.
        """
        if headers and isinstance(headers, dict):
            self.headers.update(headers)

        url = self._url(uri)

        r = requests.patch(url, data=data, auth=self.auth, headers=self.headers)

        # Expect 200 OK
        if r.status_code == requests.codes.ok:
            return r.json()
        else:
            raise Exception('Unexpected HTTP code {}, expected {} on url {}, error: {}, data: {}'
                    .format(r.status_code, requests.codes.ok, url, r.json(), data))

        return r.json()

    def _put(self, uri, data=None):
        """
        Execute PUT request using the resource, action and payload.
        """
        url = self._url(uri)

        r = requests.put(url, data=data, auth=self.auth, headers=self.headers)

        if r.status_code == requests.codes.created:
            return True

        # Raise if status is not 200 OK
        r.raise_for_status()

        # Report no change
        return r.json()

    def _delete(self, uri):
        """
        Execute DELETE request using the resource and action.
        """
        url = self._url(uri)

        r = requests.delete(url, auth=self.auth, headers=self.headers)

        if r.status_code != requests.codes.no_content:
            raise Exception('Unexpected HTTP code {}, expected {}'
                            .format(r.status_code, requests.codes.no_content))

        return True

    def _url(self, *args):
        """
        Assemble a URL based on the base_url with a URI joined by slashes.
        Trims None entries from args.
        """

        # Tolerate the first argument being a list, step into it
        if isinstance(args[0], (list, tuple)):
            args = args[0]

        # Remove None entries from args
        args = [x for x in args if x is not None]

        # Just return the base url if no arguments are given
        if not args:
            return self.base_url

        url = [self.base_url]
        url.extend(args)

        return '/'.join(url)

    @property
    def version(self):
        r = self._get("")
        return r.get('version', None)

    @property
    def status(self):
        return self._get('status')

    @property
    def healthy(self):
        return self.status.get('database', {}).get('reachable', False)
