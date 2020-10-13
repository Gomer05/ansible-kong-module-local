from kong.plugin import KongPlugin
from kong.helpers import *

# Initialize output dictionary
result = {}

# Admin endpoint & auth
url = "http://127.0.0.1:8001"
auth_user = "kong_admin"
auth_pass = "kong123"

# Extract arguments
state = "present"
name = "response-transformer-advanced"
#protocols = ['http']
service = "lsl-dev-member-profile"
#service = ""
route = "lsl-dev-member-profile-profile"
#route = ""
consumer = "anonymous_user"
#consumer = ""
config = {}

def main():
    # Create KongAPI client instance
    k = KongPlugin(url, auth_user=auth_user, auth_pass=auth_pass)

    # Contact Kong status endpoint
    # kong_status_check(k)
    # Default return values
    changed = False
    resp = ''

    # Check if the Plugin is already present
    pq = k.plugin_query(name=name, service_name=service, route_name=route, consumer_name=consumer)

    if len(pq) > 1:
        msg = 'Got multiple results for Plugin query name: {}, service: {}, route: {}, consumer: {}'.format(
              name, service, route, consumer)
        print(msg)

    if len(pq) == 1:
        print(f"Got a plugin: {pq}")

    pq = k.plugin_apply(name=name, service_name=service, route_name=route, consumer_name=consumer)
    print(f"Got a plugin: {pq}")




# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()
