import cPickle
import json


from cloudshell.api.cloudshell_api import CloudShellAPISession
from cloudshell.shell.core.driver_context import InitCommandContext, ResourceCommandContext, AutoLoadCommandContext, \
    AutoLoadDetails
from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface
# from debug_utils import debugger
from breaking_point_manager import BPS

EXC_ATTRIBUTE_NOT_FOUND = 'Expected resource model {0} to have attribute "{1}" but did not find it'

ASSOCIATED_MODELS = ['Ixia BreakingPoint Module']
ATTR_OWNER_CHASSIS = 'Virtual Traffic Generator Chassis'


# todo Handle slot id not arbitrarily - sort by attribute or some other rule


# noinspection PyAttributeOutsideInit
class IxiaBreakingpointVchassisDriver(ResourceDriverInterface):
    def __init__(self):
        """
        ctor must be without arguments, it is created with reflection at run time
        """
        pass

    def initialize(self, context):
        """
        Initialize the driver session, this function is called everytime a new instance of the driver is created
        This is a good place to load and cache the driver configuration, initiate sessions etc.
        :param InitCommandContext context: the context the command runs on
        """
        self.app_request = json.loads(context.resource.app_context.app_request_json)
        self.deployed_app = json.loads(context.resource.app_context.deployed_app_json)

    def configure_device_command(self, context, resource_cache):
        """
        A simple example function
        :param ResourceCommandContext context: the context the command runs on
        :type resource_cache: str
        """

        # IMPORTANT : will only work with deployed apps, as receives a params of resource_cache
        #  which only includes such resources
        # chassis will become associated with vBlades that were deployed but not preexisting

        # debugger.attach_debugger()
        resources = cPickle.loads(resource_cache)

        ip = context.resource.address
        username = context.resource.attributes['User']
        api = self._get_api_from_context(context)
        password = api.DecryptPassword(context.resource.attributes['Password']).Value

        bps = BPS(ip, username, password)
        bps.login()

        slot_id = 1

        for key in resources.keys():
            deployed_app = resources[key]

            if deployed_app.ResourceModelName not in ASSOCIATED_MODELS:
                continue

            try:
                chassis_name = (attr.Value for attr in deployed_app.ResourceAttributes if
                                attr.Name == ATTR_OWNER_CHASSIS).next()
            except StopIteration:
                raise Exception(EXC_ATTRIBUTE_NOT_FOUND.format(deployed_app.ResourceModelName, ATTR_OWNER_CHASSIS))

            if chassis_name == self.app_request['name']:
                host = api.GetResourceDetails(deployed_app.Name).Address
                bps.assign_slots(host=host,
                                 vm_name=deployed_app.Name,
                                 slot_id=str(slot_id),
                                 number_of_test_nics=2)
                slot_id += 1

                # stub for licensing
        pass

    def _get_api_from_context(self, context):
        token_id = context.connectivity.admin_auth_token
        host = context.connectivity.server_address
        domain = context.reservation.domain
        return CloudShellAPISession(host=host, domain=domain, token_id=token_id)

    # <editor-fold desc="Discovery">

    def get_inventory(self, context):
        """
        Discovers the resource structure and attributes.
        :param AutoLoadCommandContext context: the context the command runs on
        :return Attribute and sub-resource information for the Shell resource you can return an AutoLoadDetails object
        :rtype: AutoLoadDetails
        """
        # See below some example code demonstrating how to return the resource structure
        # and attributes. In real life, of course, if the actual values are not static,
        # this code would be preceded by some SNMP/other calls to get the actual resource information
        '''
           # Add sub resources details
           sub_resources = [ AutoLoadResource(model ='Generic Chassis',name= 'Chassis 1', relative_address='1'),
           AutoLoadResource(model='Generic Module',name= 'Module 1',relative_address= '1/1'),
           AutoLoadResource(model='Generic Port',name= 'Port 1', relative_address='1/1/1'),
           AutoLoadResource(model='Generic Port', name='Port 2', relative_address='1/1/2'),
           AutoLoadResource(model='Generic Power Port', name='Power Port', relative_address='1/PP1')]


           attributes = [ AutoLoadAttribute(relative_address='', attribute_name='Location', attribute_value='Santa Clara Lab'),
                          AutoLoadAttribute('', 'Model', 'Catalyst 3850'),
                          AutoLoadAttribute('', 'Vendor', 'Cisco'),
                          AutoLoadAttribute('1', 'Serial Number', 'JAE053002JD'),
                          AutoLoadAttribute('1', 'Model', 'WS-X4232-GB-RJ'),
                          AutoLoadAttribute('1/1', 'Model', 'WS-X4233-GB-EJ'),
                          AutoLoadAttribute('1/1', 'Serial Number', 'RVE056702UD'),
                          AutoLoadAttribute('1/1/1', 'MAC Address', 'fe80::e10c:f055:f7f1:bb7t16'),
                          AutoLoadAttribute('1/1/1', 'IPv4 Address', '192.168.10.7'),
                          AutoLoadAttribute('1/1/2', 'MAC Address', 'te67::e40c:g755:f55y:gh7w36'),
                          AutoLoadAttribute('1/1/2', 'IPv4 Address', '192.168.10.9'),
                          AutoLoadAttribute('1/PP1', 'Model', 'WS-X4232-GB-RJ'),
                          AutoLoadAttribute('1/PP1', 'Port Description', 'Power'),
                          AutoLoadAttribute('1/PP1', 'Serial Number', 'RVE056702UD')]

           return AutoLoadDetails(sub_resources,attributes)
        '''
        pass

    # </editor-fold>

    def cleanup(self):
        """
        Destroy the driver session, this function is called everytime a driver instance is destroyed
        This is a good place to close any open sessions, finish writing to log files
        """
        pass
