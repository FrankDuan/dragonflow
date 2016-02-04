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

from neutron.agent.common import utils
import re


class OvsFlowsParser(object):

    def _get_ovs_flows(self):
        full_args = ["ovs-ofctl", "dump-flows", 'br-int', '-O Openflow13']
        flows = utils.execute(full_args, run_as_root=True,
                              process_input=None)
        return flows

    def _parse_ovs_flows(self, flows):
        flow_list = flows.split("\n")[1:]
        flows_as_dicts = []
        for flow in flow_list:
            if len(flow) == 0:
                continue
            fs = flow.split(' ')
            res = {}
            res['table'] = fs[3].split('=')[1]
            res['match'] = fs[-2]
            res['actions'] = fs[-1].split('=')[1]
            res['cookie'] = fs[1].split('=')[1]
            m = re.search('priority=(\d+)', res['match'])
            if m:
                res['priority'] = m.group(1)
                res['match'] = re.sub(r'priority=(\d+),?', '', res['match'])
            flows_as_dicts.append(res)
        return flows_as_dicts

    def diff_flows(self, list1, list2):
        result = [v for v in list2 if v not in list1]
        return result

    def dump(self):
        flows = self._get_ovs_flows()
        return self._parse_ovs_flows(flows)