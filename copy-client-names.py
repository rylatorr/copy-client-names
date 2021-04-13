#!/usr/bin/python3

READ_ME = '''
=== PREREQUISITES ===
Run in Python 3

Assign network tag "copy_client_names_src" to the network with the custom client names already applied.
Assign network tag "copy_client_names_dst" to the network where the names need to be configured.

Install both requests & Meraki Dashboard API Python modules:
pip[3] install --upgrade requests
pip[3] install --upgrade meraki

=== DESCRIPTION ===
Assign network tag "copy_client_names_src" to the network with the custom client names already applied.
Assign network tag "copy_client_names_dst" to the network where the names need to be configured.
Remove the network tags/labels afterwards.

=== USAGE ===
python[3] copy-client-names.py -k <api_key> -o <org_id>
'''

from datetime import datetime
import getopt
import logging
import sys
import time
import meraki
import requests

# Prints READ_ME help message for user to read
def print_help():
    lines = READ_ME.split('\n')
    for line in lines:
        print('# {0}'.format(line))

logger = logging.getLogger(__name__)

def configure_logging():
    logging.basicConfig(
        filename='{}_log_{:%Y%m%d_%H%M%S}.txt'.format(sys.argv[0].split('.')[0], datetime.now()),
        level=logging.DEBUG,
        format='%(asctime)s: %(levelname)7s: [%(name)s]: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

# https://developer.cisco.com/meraki/api-v1/#!get-network-clients
# https://developer.cisco.com/meraki/api-v1/#!provision-network-clients

def main(argv):
    # Set default values for command line arguments
    api_key = org_id = arg_mode = None

    # Get command line arguments
    try:
        opts, args = getopt.getopt(argv, 'hk:o:')
    except getopt.GetoptError:
        print_help()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print_help()
            sys.exit()
        elif opt == '-k':
            api_key = arg
        elif opt == '-o':
            org_id = arg

    # Check if all required parameters have been input
    if api_key == None or org_id == None:
        print_help()
        sys.exit(2)

    # Instantiate a Meraki dashboard API session
    dashboard = meraki.DashboardAPI(
        api_key,
        output_log=False
        #log_file_prefix=os.path.basename(__file__)[:-3],
        #log_path='',
        #print_console=False
    )

    # Get list of current networks in org
    networks = dashboard.organizations.getOrganizationNetworks(org_id)

    # Iterate through all networks and load client lists
    # initialize variables
    clientDetailsDst = []
    clientDetailsSrc = []
    for network in networks:
        #print(f"Evaluating network {network['id']} : {network['name']}")
        # Skip if network does not have the tag "update_whitelist"
        if 'copy_client_names_src' in network['tags']:
            # Get client details for src network
            print(f"Matched source network {network['name']}")
            netIdSrc = network['id']
            clientDetailsSrc = dashboard.networks.getNetworkClients(network['id'], timespan=2678400, perPage=1000)
        elif 'copy_client_names_dst' in network['tags']:
            print(f"Matched dest network {network['name']}")
            netIdDst = network['id']
            clientDetailsDst = dashboard.networks.getNetworkClients(network['id'], timespan=2678400, perPage=1000)
        elif network['tags'] is None or 'copy_client_names' not in network['tags']:
            continue

    # Iterate through each client in dst network and attempt to match from src
    #print(f'source client json: \n {clientDetailsSrc}')
    #print(f'destination client json: \n {clientDetailsDst}')
    for client in clientDetailsDst:
        print(f"Current Client: {client['mac']}, {client['description']}")
        matchedItem = next((item for item in clientDetailsSrc if item["mac"] == client["mac"]), None)
        if matchedItem is None:
            continue
        else:
            toProvision = [{'mac': matchedItem['mac'], 'name': matchedItem['description']}]
            dashboard.networks.provisionNetworkClients(netIdDst, toProvision, 'Normal')

if __name__ == "__main__":
    # Configure logging to stdout
    configure_logging()
    # Define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    # Set a format which is simpler for console use
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    # Tell the handler to use this format
    console.setFormatter(formatter)
    # Add the handler to the root logger
    logging.getLogger('').addHandler(console)

    # Output to logfile/console starting inputs
    start_time = datetime.now()
    logger.info('Started script at {0}'.format(start_time))
    inputs = sys.argv[1:]
    try:
        key_index = inputs.index('-k')
    except ValueError:
        print_help()
        sys.exit(2)
    inputs.pop(key_index+1)
    inputs.pop(key_index)
    logger.info('Input parameters: {0}'.format(inputs))

    main(sys.argv[1:])

    # Finish output to logfile/console
    end_time = datetime.now()
    logger.info('Ended script at {0}'.format(end_time))
    logger.info(f'Total run time = {end_time - start_time}')
