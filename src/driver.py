import cPickle
import json

from cloudshell.api.cloudshell_api import CloudShellAPISession
from cloudshell.shell.core.driver_context import InitCommandContext, ResourceCommandContext, AutoLoadCommandContext, \
    AutoLoadDetails
from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface
from bp_controller.runners.bp_runner_pool import BPRunnersPool
from cloudshell.networking.devices.driver_helper import get_logger_with_thread_id
from cloudshell.shell.core.driver_context import AutoLoadDetails
from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface

from breaking_point_manager import BPS

ATTR_NUMBER_OF_PORTS = 'Number of Ports'

EXC_ATTRIBUTE_NOT_FOUND = 'Expected resource model {0} to have attribute "{1}" but did not find it'

ASSOCIATED_MODELS = ['Ixia BreakingPoint Module']
ATTR_OWNER_CHASSIS = 'Virtual Traffic Generator Chassis'


# noinspection PyAttributeOutsideInit
class IxiaBreakingpointVchassisDriver(ResourceDriverInterface):
    def __init__(self):
        """
        ctor must be without arguments, it is created with reflection at run time
        """
        self._runners_pool = BPRunnersPool()

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

        resources = cPickle.loads(resource_cache)

        if 'License Server' not in context.resource.attributes:
            raise Exception('Missing attribute "License Server" on {0}'.format(context.resource.name))
        if context.resource.attributes['License Server'] == '':
            raise Exception('Must configure public IP of Breaking Point license server on {0}'.format(context.resource.name))

        ip = context.resource.address
        username = context.resource.attributes['User']
        api = self._get_api_from_context(context)
        password = api.DecryptPassword(context.resource.attributes['Password']).Value

        bps = BPS(ip, username, password)
        bps.login_rest()

        free_slots = [x + 1 for x in range(11)]

        vblades = []
        slot_id = 0

        # first get all vblades and check who is already assigned to a slot;
        # this will give priority to assigning vblade to slot above arbitrarily assigning a slot
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
                vblade_res = api.GetResourceDetails(deployed_app.Name)
                requested_slot = (int(attr.Value) for attr in vblade_res.ResourceAttributes if
                              attr.Name == 'Slot Id').next()
                if requested_slot != 0 and requested_slot in free_slots:
                    slot_id = self._user_assign_slot(free_slots, requested_slot)
                    vblade_res.slot_id = slot_id
                vblades.append(vblade_res)

        # ok, now we can assign vblades to slot, and assign addresses to ports
        for vblade in vblades:
            number_of_ports = (attr.Value for attr in vblade.ResourceAttributes
                               if attr.Name == ATTR_NUMBER_OF_PORTS).next()

            if not hasattr(vblade, 'slot_id'):
                slot_id = self._automatic_assign_port(api, free_slots, vblade_res)
            else:
                slot_id = vblade.slot_id

            bps.assign_slots(host=vblade.Address,
                             vm_name=vblade.Name,
                             slot_id=str(slot_id),
                             number_of_test_nics=int(number_of_ports))

            for resource in vblade.ChildResources:
                # chassis  ip  i.e. THIS resource not vblade ip/ slot num / port num
                new_address = '{0}/{1}/{2}'.format(context.resource.address,
                                                   'M' + str(slot_id), 'P' + str(int(resource.Address) - 1))
                api.UpdateResourceAddress(resource.Name, new_address)

        bps.logout_rest()
        bps.add_license_server(license_server_host=context.resource.attributes['License Server'])

    def _user_assign_slot(self, free_slots, requested_slot):
        free_slots.remove(requested_slot)
        return requested_slot

    def _automatic_assign_port(self, api, free_slots, vblade_res):
        slot_id = free_slots.pop(0)
        api.SetAttributeValue(vblade_res.Name, 'Slot Id', str(slot_id))
        return slot_id

    def _set_licensing(self, context):
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
        return AutoLoadDetails([], [])

    # </editor-fold>

    def load_config(self, context, config_file_location):
        with self._runners_pool.actual_runner(context) as runner:
            return runner.load_configuration(config_file_location)

    def start_traffic(self, context, blocking):
        """
        :param context: the context the command runs on
        :type context: cloudshell.shell.core.driver_context.ResourceRemoteCommandContext
        :param blocking:
        """
        with self._runners_pool.actual_runner(context) as runner:
            return runner.start_traffic(blocking)

    def stop_traffic(self, context):
        """
        :param context: the context the command runs on
        :type context: cloudshell.shell.core.driver_context.ResourceRemoteCommandContext
        """
        with self._runners_pool.actual_runner(context) as runner:
            return runner.stop_traffic()

    def get_statistics(self, context, view_name, output_type):
        with self._runners_pool.actual_runner(context) as runner:
            return runner.get_statistics(view_name, output_type)

    def cleanup(self):
        """
        Destroy the driver session, this function is called everytime a driver instance is destroyed
        This is a good place to close any open sessions, finish writing to log files
        """
        pass
