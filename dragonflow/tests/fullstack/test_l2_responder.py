#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import re

import eventlet

from neutron.agent.linux import utils

from dragonflow.controller.common import constants as const
from dragonflow.tests.common import utils as test_utils
from dragonflow.tests.fullstack import test_base
from dragonflow.tests.fullstack import test_objects as objects


class ArpResponderTest(test_base.DFTestBase):

    def _find_arp_responder_flow_by_ip(self, flows, ip_str):
            for flow in flows:
                match = flow['match']
                if not re.search('\\barp\\b', match):
                    continue
                if not re.search(
                        '\\barp_tpa=%s\\b' % ip_str.replace('.', '\\.'),
                        match):
                    continue
                if not re.search('\\barp_op=1\\b', match):
                    continue
                return flow
            return None

    def _get_arp_table_flows(self):
        ovs_flows_parser = test_utils.OvsFlowsParser()
        flows = ovs_flows_parser.dump()
        flows = [flow for flow in flows
                if flow['table'] == str(const.ARP_TABLE)]
        return flows

    def _check_arp_flow_removal(self, ip):
        arp_flows = self._get_arp_table_flows()
        flow = self._find_arp_responder_flow_by_ip(arp_flows, ip)
        if not flow:
            return True
        return False

    def test_arp_responder(self):
        """
        Add a VM. Verify it's ARP flow is there.
        """
        network = self.store(objects.NetworkTestObj(self.neutron, self.nb_api))
        network_id = network.create(network={'name': 'arp_responder_test'})
        subnet_obj = self.store(objects.SubnetTestObj(
            self.neutron,
            self.nb_api,
            network_id,
        ))

        subnet = {'network_id': network_id,
            'cidr': '10.10.10.0/24',
            'gateway_ip': '10.10.10.1',
            'ip_version': 4,
            'name': 'arp_responder_test',
            'enable_dhcp': True}
        subnet = subnet_obj.create(subnet)

        flows_before = self._get_arp_table_flows()
        vm = self.store(objects.VMTestObj(self, self.neutron))
        vm.create(network=network)
        ip = vm.get_first_ipv4()
        self.assertIsNotNone(ip)

        flows_middle = self._get_arp_table_flows()

        vm.server.stop()
        vm.close()
        eventlet.sleep(test_utils.DEFAULT_CMD_TIMEOUT)
        flows_delta = [flow for flow in flows_middle
                if flow not in flows_before]
        self.assertIsNotNone(
            self._find_arp_responder_flow_by_ip(flows_delta, ip)
        )

        condition = lambda: self._check_arp_flow_removal(ip)
        try:
            utils.wait_until_true(
                condition, timeout=40, sleep=1,
                exception=RuntimeError(
                    "Timed out waiting for arp responedr flow from  %(ip)s"
                    " to be removed" % {'ip': ip}))
        except Exception as e:
            self.assertIsNone(e)
        finally:
            network.close()
