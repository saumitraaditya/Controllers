# ipop-project
# Copyright 2016, University of Florida
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import math
import random
from controller.modules.NetworkGraph import ConnectionEdge
from controller.modules.NetworkGraph import ConnEdgeAdjacenctList

class GraphBuilder():
    """
    Creates the adjacency list of connections edges from this node that are necessary to
    maintain the Topology
    """
    def __init__(self, cfg, current_adj_list=None):
        self.overlay_id = cfg["OverlayId"]
        self._node_id = cfg["NodeId"]
        self._peers = sorted(cfg.get("Peers", []))
        # enforced is a list of peer ids that should always have a direct edge
        self._enforced = cfg.get("EnforcedEdges", {})
        # only create edges from the enforced list
        self._manual_topo = cfg.get("ManualTopology", False)
        self._max_successors = int(cfg["MaxSuccessors"])
        # the number of symphony edges that shoulb be maintained
        num_peers = len(self._peers)
        self._max_ldl_cnt = math.floor(math.log(num_peers, 2)) # int(cfg["MaxLongDistEdges"])
        # Currently active adjacency list, needed to minimize changes in chord selection
        self._curr_adj_lst = current_adj_list

    def _build_enforced(self, adj_list):
        for peer_id in self._enforced:
            ce = ConnectionEdge(peer_id, edge_type="CETypeEnforced")
            adj_list.add_connection_edge(ce)

    def _get_successors(self):
        """ Generate a list of successor UIDs from the list of peers """
        successors = []
        num_peers = len(self._peers)
        if not self._peers or (num_peers == 1 and self._node_id > self._peers[0]):
            return successors
        node_list = list(self._peers)
        node_list.append(self._node_id)
        node_list.sort()
        num_nodes = len(node_list)
        successor_index = node_list.index(self._node_id) + 1
        num_succ = self._max_successors if (num_peers >= self._max_successors) else num_peers
        for _ in range(num_succ):
            successor_index %= num_nodes
            successors.append(node_list[successor_index])
            successor_index += 1
        return successors

    def _build_successors(self, adj_list):
        successors = self._get_successors()
        for peer_id in successors:
            # ce_cnd = adj_list.conn_edge.get(peer_id)
            # exclude if peer was previously added to either adj list
            #if ce_cnd and ce_cnd.edge_type == "CETypeEnforced": continue
            #ce_cnd = transition_adj_list.conn_edge.get(peer_id)
            #if ce_cnd and (ce_cnd.edge_type == "CETypeEnforced" or
            #               ce_cnd.edge_type in EdgeType2): continue
            if peer_id not in adj_list:
                ce = ConnectionEdge(peer_id, edge_type="CETypeSuccessor")
                adj_list.add_connection_edge(ce)

    @staticmethod
    def symphony_prob_distribution(network_sz, samples):
        """exp (log(n) * (rand() - 1.0))"""
        results = [None]*(samples)
        for i in range(0, samples):
            rnd_val = random.uniform(0, 1)
            results[i] = math.exp(math.log10(network_sz) * (rnd_val - 1.0))
        return results

    def _get_long_dist_links(self, num_ldl):
        # Calculates long distance link candidates.
        long_dist_links = []
        all_nodes = sorted(self._peers + [self._node_id])
        network_sz = len(all_nodes)
        my_index = all_nodes.index(self._node_id)
        # num_peers = len(self._peers)
        node_off = GraphBuilder.symphony_prob_distribution(network_sz, num_ldl)
        for i in node_off:
            idx = math.floor(network_sz*i)
            ldl_idx = (my_index + idx)%network_sz
            long_dist_links.append(all_nodes[ldl_idx])
        return long_dist_links

    def _build_long_dist_links(self, adj_list, transition_adj_list):
        # Add potential long distance link candidates to the adjacency list
        existing_ldlnks = transition_adj_list.get_edges("CETypeLongDistance")
        num_existing_ldl = 0
        for peer_id in existing_ldlnks:
            if peer_id not in adj_list:
                adj_list[peer_id] = existing_ldlnks[peer_id]
                num_existing_ldl += 1
        num_ldl = self._max_ldl_cnt - self._max_successors - num_existing_ldl
        if num_ldl < 0:
            return
        ldl = self._get_long_dist_links(num_ldl)
        for peer_id in ldl:
            if peer_id not in adj_list:
                ce = ConnectionEdge(peer_id, edge_type="CETypeLongDistance")
                adj_list.add_connection_edge(ce)

    def _build_ondemand_links(self, adj_list, request_list, transition_adj_list):
        tmp = []
        for peer_id, op in request_list:
            if op == "ADD":
                if peer_id in self._peers and (peer_id not in adj_list or
                                               peer_id not in transition_adj_list):
                    ce = ConnectionEdge(peer_id, None, "CETypeOnDemand")
                    adj_list.add_connection_edge(ce)
                    tmp.append(peer_id)
            elif op == "REMOVE":
                if peer_id in adj_list and adj_list[peer_id].edge_type == "CETypeOnDemand":
                    adj_list.pop(peer_id)
        for peer_id in tmp:
            request_list.pop(peer_id)

    def build_adj_list(self, transition_adj_list, request_list=None):
        adj_list = ConnEdgeAdjacenctList(self.overlay_id, self._node_id,
                                         dict(MaxSuccessors=self._max_successors,
                                              MaxLongDistEdges=self._max_ldl_cnt))
        self._build_enforced(adj_list)
        if not self._manual_topo:
            self._build_successors(adj_list)
            self._build_long_dist_links(adj_list, transition_adj_list)
            #if request_list:
            #    self._build_ondemand_links(adj_list, request_list, transition_adj_list)
        return adj_list

    def build_adj_list_ata(self,):
        """
        Generates a new adjacency list from the list of available peers
        """
        adj_list = ConnEdgeAdjacenctList(self.overlay_id, self._node_id)
        for peer_id in self._peers:
            if self._enforced and peer_id in self._enforced:
                ce = ConnectionEdge(peer_id)
                ce.edge_type = "CETypeEnforced"
                adj_list.add_connection_edge(ce)
            elif not self._manual_topo and self._node_id < peer_id:
                ce = ConnectionEdge(peer_id)
                ce.edge_type = "CETypeSuccessor"
                adj_list.add_connection_edge(ce)
        return adj_list
