def get_assign_slot_request(host_address, vm_name, slot_id, number_of_test_nics):
    """

    :param host_address:
    :param vm_name:
    :param slot_id: must be string!
    :param number_of_test_nics: must be int!
    :return:
    """
    assign_slot_request = [{
        "slotId": slot_id,
        "ipAddress": host_address,
        "vmName": vm_name,
        "hostInfo": {
            "hostType": 'kUnknown',
            "hostName": "Unavailable",
            "hostUsername": "",
            "hostPassword": ""
        },
        "deleting": False,
        "testNics": number_of_test_nics
    }]
    return assign_slot_request
