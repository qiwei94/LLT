# TrafficControl
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.topology import event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER, HANDSHAKE_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, arp, ipv4, tcp, udp, ether_types
from ryu.topology.api import get_link
from webob import Response
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from collections import defaultdict
import network_monitor
import entry_struct
import json
from copy import deepcopy


class TrafficControl(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {
        "Network_Monitor": network_monitor.Network_Monitor,
        "wsgi": WSGIApplication
    }

    def __init__(self, *args, **kwargs):
        super(TrafficControl, self).__init__(*args, **kwargs)

        # common variable
        self.mac_to_port = {}
        self.topology_api_app = self
        self.check_ip_dpid = defaultdict(list)
        self.ip_to_mac = {}
        self.mac_to_dpid = {}  # {mac:(dpid,port)}
        self.datapaths = defaultdict(lambda: None)
        self.src_links = defaultdict(lambda: defaultdict(lambda: None))
        self.network_monitor = kwargs["Network_Monitor"]
        self.strategy = defaultdict(lambda: None)
        self.paths = defaultdict(lambda: defaultdict(lambda: None))
        self.port_name_to_num = defaultdict(lambda: None)
        wsgi = kwargs['wsgi']

        wsgi.register(TrafficControlRestAPI, {'datapaths': self.datapaths, 'flow_speed': self.network_monitor.flow_speed, 'port_speed': self.network_monitor.port_speed, 'strategy': self.strategy})

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None, idle_timeout=0, hard_timeout=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    idle_timeout=idle_timeout,
                                    hard_timeout=hard_timeout,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    idle_timeout=idle_timeout,
                                    hard_timeout=hard_timeout,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes", ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        pkt_arp = pkt.get_protocol(arp.arp)
        pkt_ipv4 = pkt.get_protocol(ipv4.ipv4)

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dst = eth.dst
        src = eth.src
        dpid = datapath.id

        self.logger.info('dpid: %s', dpid)

        # self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        # in rest_topology, self.mac_to_port is for the find for host
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src] = in_port

        # arp handle
        if pkt_arp and pkt_arp.opcode == arp.ARP_REQUEST:
            if pkt_arp.src_ip not in self.ip_to_mac:
                self.ip_to_mac[pkt_arp.src_ip] = src
                self.mac_to_dpid[src] = (dpid, in_port)

            if pkt_arp.dst_ip in self.ip_to_mac:
                self.handle_arpre(datapath=datapath, port=in_port, src_mac=self.ip_to_mac[pkt_arp.dst_ip], dst_mac=src,
                                  src_ip=pkt_arp.dst_ip, dst_ip=pkt_arp.src_ip)
            else:
                # to avoid flood when the dst ip not in the network
                if datapath.id not in self.check_ip_dpid[pkt_arp.dst_ip]:
                    self.check_ip_dpid[pkt_arp.dst_ip].append(datapath.id)
                    out_port = ofproto.OFPP_FLOOD
                    actions = [parser.OFPActionOutput(out_port)]
                    data = None
                    if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                        data = msg.data
                    out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                              in_port=in_port, actions=actions, data=data)
                    datapath.send_msg(out)
            return

        elif pkt_arp and pkt_arp.opcode == arp.ARP_REPLY:
            if pkt_arp.src_ip not in self.ip_to_mac:
                self.ip_to_mac[pkt_arp.src_ip] = src
                self.mac_to_dpid[src] = (dpid, in_port)
            dst_mac = self.ip_to_mac[pkt_arp.dst_ip]
            (dst_dpid, dst_port) = self.mac_to_dpid[dst_mac]
            self.handle_arpre(datapath=self.datapaths[dst_dpid], port=dst_port, src_mac=src, dst_mac=dst_mac,
                              src_ip=pkt_arp.src_ip, dst_ip=pkt_arp.dst_ip)
            return

        if pkt_ipv4 and src in self.mac_to_dpid and dst in self.mac_to_dpid:
            self.install_path(ev=ev, src=src, dst=dst)

    def send_pkt(self, datapath, port, pkt):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        pkt.serialize()
        data = pkt.data
        actions = [parser.OFPActionOutput(port=port)]
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=ofproto.OFP_NO_BUFFER, in_port=ofproto.OFPP_CONTROLLER,
                                  actions=actions, data=data)
        datapath.send_msg(out)

    def handle_arpre(self, datapath, port, src_mac, dst_mac, src_ip, dst_ip):
        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(ethertype=0x0806, dst=dst_mac, src=src_mac))
        pkt.add_protocol(arp.arp(opcode=arp.ARP_REPLY, src_mac=src_mac, src_ip=src_ip, dst_mac=dst_mac, dst_ip=dst_ip))
        self.send_pkt(datapath, port, pkt)

    def install_path(self, ev, src, dst):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        pkt = packet.Packet(msg.data)
        pkt_ipv4 = pkt.get_protocol(ipv4.ipv4)
        pkt_tcp = pkt.get_protocol(tcp.tcp)
        pkt_udp = pkt.get_protocol(udp.udp)

        (src_dpid, src_port) = self.mac_to_dpid[src]
        (dst_dpid, dst_port) = self.mac_to_dpid[dst]

        # when the path is not exist, recalculate the path
        if not self.paths[src_dpid][dst_dpid]:
            mid_path = self.short_path(src=src_dpid, dst=dst_dpid)
            if mid_path is None:
                return
            self.paths[src_dpid][dst_dpid] = mid_path
        path = [(src_dpid, src_port)] + self.paths[src_dpid][dst_dpid] + [(dst_dpid, dst_port)]

        if pkt_tcp:
            value = self.strategy.get((pkt_ipv4.src, pkt_ipv4.dst, 'tcp', 0, pkt_tcp.dst_port), None) or self.strategy.get((pkt_ipv4.src, pkt_ipv4.dst, '*', pkt_tcp.src_port, pkt_tcp.dst_port), None)
            if value:
                # value -- (priority, bandwidth)
                # flow priority map to queue id
                queue_id = value[0]
                for i in xrange(len(path) - 2, -1, -2):
                    datapath_path = self.datapaths[path[i][0]]
                    dpid = path[i][0]
                    idle_timeout = 5

                    # physical switch
                    if dpid == 1:
                        idle_timeout = 0
                        flow_entry = entry_struct(in_port=path[i][1], src_ip=pkt_ipv4.src,
                                                  dst_ip=pkt_ipv4.dst, src_port=pkt_tcp.src_port,
                                                  dst_port=pkt_tcp.dst_port, out_port=path[i+1][1],
                                                  queue_id=queue_id)
                        exp_msg = parser.OFPExperimenter(datapath_path, 7, 4, flow_entry.trans_to_data_send().encode('ascii'))
                        datapath_path.send_msg(exp_msg)

                    match = parser.OFPMatch(in_port=path[i][1], eth_src=src, eth_dst=dst, eth_type=0x0800,
                                            ipv4_src=pkt_ipv4.src, ipv4_dst=pkt_ipv4.dst, ip_proto=6,
                                            tcp_src=pkt_tcp.src_port, tcp_dst=pkt_tcp.dst_port)
                    actions = [parser.OFPActionSetQueue(queue_id=queue_id), parser.OFPActionOutput(path[i + 1][1])]
                    if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                        self.add_flow(datapath_path, 100, match, actions, msg.buffer_id, idle_timeout=idle_timeout, hard_timeout=0)
                    else:
                        self.add_flow(datapath_path, 100, match, actions, idle_timeout=idle_timeout, hard_timeout=0)
                return
        elif pkt_udp:
            value = self.strategy.get((pkt_ipv4.src, pkt_ipv4.dst, 'udp', pkt_udp.src_port, pkt_udp.dst_port), None) or self.strategy.get((pkt_ipv4.src, pkt_ipv4.dst, '*', pkt_udp.src_port, pkt_udp.dst_port), None)
            if value:
                queue_id = value[0]
                for i in xrange(len(path) - 2, -1, -2):
                    datapath_path = self.datapaths[path[i][0]]
                    dpid = path[i][0]
                    idle_timeout = 5

                    # physical switch
                    if dpid == 1:
                        idle_timeout = 0
                        flow_entry = entry_struct(in_port=path[i][1], src_ip=pkt_ipv4.src, dst_ip=pkt_ipv4.dst, src_port=pkt_udp.src_port, dst_port=pkt_udp.dst_port, out_port=path[i+1][1], queue_id=queue_id)
                        exp_msg = parser.OFPExperimenter(datapath_path, 7, 4, flow_entry.trans_to_data_send().encode('ascii'))
                        datapath_path.send_msg(exp_msg)

                    match = parser.OFPMatch(in_port=path[i][1], eth_src=src, eth_dst=dst, eth_type=0x0800, ipv4_src=pkt_ipv4.src, ipv4_dst=pkt_ipv4.dst, ip_proto=17, udp_src=pkt_udp.src_port, udp_dst=pkt_udp.dst_port)
                    actions = [parser.OFPActionSetQueue(queue_id=queue_id), parser.OFPActionOutput(path[i + 1][1])]
                    if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                        self.add_flow(datapath_path, 100, match, actions, msg.buffer_id, idle_timeout=idle_timeout, hard_timeout=0)
                    else:
                        self.add_flow(datapath_path, 100, match, actions, idle_timeout=idle_timeout, hard_timeout=0)
                return

        for i in xrange(len(path) - 2, -1, -2):
            datapath_path = self.datapaths[path[i][0]]
            dpid = path[i][0]
            idle_timeout = 5

            # physical switch
            if dpid == 1:
                idle_timeout = 0
                flow_entry = entry_struct(in_port=path[i][1], src_ip=pkt_ipv4.src, dst_ip=pkt_ipv4.dst, src_port=-1, dst_port=-1, out_port=path[i+1][1], queue_id=0)
                exp_msg = parser.OFPExperimenter(datapath_path, 7, 4, flow_entry.trans_to_data_send().encode('ascii'))
                datapath_path.send_msg(exp_msg)
            match = parser.OFPMatch(in_port=path[i][1], eth_src=src, eth_dst=dst, eth_type=0x0800, ipv4_src=pkt_ipv4.src, ipv4_dst=pkt_ipv4.dst)
            actions = [parser.OFPActionOutput(path[i + 1][1])]
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath_path, 1, match, actions, msg.buffer_id, idle_timeout=idle_timeout, hard_timeout=0)
            else:
                self.add_flow(datapath_path, 1, match, actions, idle_timeout=idle_timeout, hard_timeout=0)

    def re_install_path(self, flow, old_paths):
        match = flow[0]
        actions = flow[1]
        priority = flow[2]
        (src_dpid, src_port) = self.mac_to_dpid[match.get('eth_src')]
        (dst_dpid, dst_port) = self.mac_to_dpid[match.get('eth_dst')]

        old_path = old_paths[src_dpid][dst_dpid]

        src = match.get('eth_src')
        dst = match.get('eth_dst')
        ipv4_src = match.get('ipv4_src')
        ipv4_dst = match.get('ipv4_dst')
        ip_proto = match.get('ip_proto')

        # delete the old flow
        for i in range(0, len(old_path)-1, 2):
            datapath_path = self.datapaths[old_path[i][0]]
            ofproto = datapath_path.ofproto
            parser = datapath_path.ofproto_parser
            if ip_proto == 6:
                tcp_src = match.get('tcp_src')
                tcp_dst = match.get('tcp_dst')
                del_match = parser.OFPMatch(eth_src=src, eth_dst=dst, eth_type=0x0800, ipv4_src=ipv4_src, ipv4_dst=ipv4_dst, ip_proto=6, tcp_src=tcp_src, tcp_dst=tcp_dst)
            elif ip_proto == 17:
                udp_src = match.get('udp_src')
                udp_dst = match.get('udp_dst')
                del_match = parser.OFPMatch(eth_src=src, eth_dst=dst, eth_type=0x0800, ipv4_src=ipv4_src, ipv4_dst=ipv4_dst, ip_proto=17, udp_src=udp_src, udp_dst=udp_dst)
            else:
                del_match = parser.OFPMatch(eth_src=src, eth_dst=dst, eth_type=0x0800, ipv4_src=ipv4_src, ipv4_dst=ipv4_dst)
            mod = parser.OFPFlowMod(datapath=datapath_path, match=del_match, command=ofproto.OFPFC_DELETE, priority=priority, out_port=ofproto.OFPP_ANY, out_group=ofproto.OFPG_ANY)
            datapath_path.send_msg(mod)

        mid_path = self.short_path(src=src_dpid, dst=dst_dpid)
        if mid_path is None:
            return
        self.paths[src_dpid][dst_dpid] = mid_path
        path = [(src_dpid, src_port)] + self.paths[src_dpid][dst_dpid] + [(dst_dpid, dst_port)]
        self.logger.info('path: %s', path)
        for i in xrange(len(path) - 2, -1, -2):
            datapath_path = self.datapaths[path[i][0]]
            dpid = path[i][0]
            parser = datapath_path.ofproto_parser
            idle_timeout = 5
            if ip_proto == 6:
                tcp_src = match.get('tcp_src')
                tcp_dst = match.get('tcp_dst')
                queue_id = actions[-2].queue_id
                if dpid == 1:
                    idle_timeout = 0
                    flow_entry = entry_struct(in_port=path[i][1], src_ip=ipv4_src, dst_ip=ipv4_dst, src_port=tcp_src, dst_port=tcp_dst, out_port=path[i+1][1], queue_id=queue_id)
                    exp_msg = parser.OFPExperimenter(datapath_path, 7, 4, flow_entry.trans_to_data_send().encode('ascii'))
                    datapath_path.send_msg(exp_msg)
                match_item = parser.OFPMatch(in_port=path[i][1], eth_src=src, eth_dst=dst, eth_type=0x0800, ipv4_src=ipv4_src, ipv4_dst=ipv4_dst, ip_proto=6, tcp_src=tcp_src, tcp_dst=tcp_dst)
                action_item = [parser.OFPActionSetQueue(queue_id=queue_id), parser.OFPActionOutput(path[i + 1][1])]
            elif ip_proto == 17:
                udp_src = match.get('udp_src')
                udp_dst = match.get('udp_dst')
                queue_id = actions[-2].queue_id
                if dpid == 1:
                    idle_timeout = 0
                    flow_entry = entry_struct(in_port=path[i][1], src_ip=ipv4_src, dst_ip=ipv4_dst, src_port=udp_src, dst_port=udp_dst, out_port=path[i+1][1], queue_id=queue_id)
                    exp_msg = parser.OFPExperimenter(datapath_path, 7, 4, flow_entry.trans_to_data_send().encode('ascii'))
                    datapath_path.send_msg(exp_msg)
                match_item = parser.OFPMatch(in_port=path[i][1], eth_src=src, eth_dst=dst, eth_type=0x0800, ipv4_src=ipv4_src, ipv4_dst=ipv4_dst, ip_proto=17, udp_src=udp_src, udp_dst=udp_dst)
                action_item = [parser.OFPActionSetQueue(queue_id=queue_id), parser.OFPActionOutput(path[i + 1][1])]
            else:
                if dpid == 1:
                    idle_timeout = 0
                    flow_entry = entry_struct(in_port=path[i][1], src_ip=ipv4_src, dst_ip=ipv4_dst, src_port=-1, dst_port=-1, out_port=path[i+1][1], queue_id=queue_id)
                    exp_msg = parser.OFPExperimenter(datapath_path, 7, 4, flow_entry.trans_to_data_send().encode('ascii'))
                    datapath_path.send_msg(exp_msg)
                match_item = parser.OFPMatch(in_port=path[i][1], eth_src=src, eth_dst=dst, eth_type=0x0800, ipv4_src=ipv4_src, ipv4_dst=ipv4_dst)
                action_item = [parser.OFPActionOutput(path[i + 1][1])]
            self.add_flow(datapath_path, priority, match_item, action_item, idle_timeout=idle_timeout, hard_timeout=0)

    def short_path(self, src, dst):
        if src == dst:
            return []
        result = defaultdict(lambda: defaultdict(lambda: None))
        distance = defaultdict(lambda: defaultdict(lambda: None))

        # the node is checked
        seen = [src]

        # the distance to src
        distance[src] = 0

        w = 1  # weight

        while len(seen) < len(self.src_links):
            node = seen[-1]
            if node == dst:
                break
            for (temp_src, temp_dst) in self.src_links[node]:
                if temp_dst not in seen:
                    temp_src_port = self.src_links[node][(temp_src, temp_dst)][0]
                    temp_dst_port = self.src_links[node][(temp_src, temp_dst)][1]

                    if (distance[temp_dst] is None) or (distance[temp_dst] > distance[temp_src] + w):
                        distance[temp_dst] = distance[temp_src] + w
                        result[temp_dst] = (temp_src, temp_src_port, temp_dst, temp_dst_port)
            min_node = None
            min_path = 999
            # get the min_path node
            for temp_node in distance:
                if (temp_node not in seen) and (distance[temp_node] is not None):
                    if distance[temp_node] < min_path:
                        min_node = temp_node
                        min_path = distance[temp_node]
            if min_node is None:
                break
            seen.append(min_node)

        path = []

        if dst not in result:
            return None

        while (dst in result) and (result[dst] is not None):
            path = [result[dst][2:4]] + path
            path = [result[dst][0:2]] + path
            dst = result[dst][0]
        return path

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                del self.datapaths[datapath.id]
        # self.logger.info("datapaths : %s", self.datapaths)

    @set_ev_cls(ofp_event.EventOFPPortStatus, [CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER, HANDSHAKE_DISPATCHER])
    def failure_recovery(self, ev):
        msg = ev.msg
        desc = msg.desc
        name = desc.name
        datapath = msg.datapath
        dpid = datapath.id

        port = self.port_name_to_num.get(name)
        key = (dpid, port)
        flowList = self.network_monitor.dpidport_to_flow.get(key, [])

        # save the old paths to delete the flow
        old_paths = deepcopy(self.paths)

        if (dpid, port) in self.src_links[dpid]:
            del self.src_links[dpid][(dpid, port)]

        for flow in flowList:
            self.re_install_path(flow, old_paths)

    @set_ev_cls([event.EventSwitchEnter, event.EventSwitchLeave, event.EventPortAdd, event.EventPortDelete,
                 event.EventPortModify, event.EventLinkAdd, event.EventLinkDelete])
    def get_topology(self, ev):
        links_list = get_link(self.topology_api_app, None)

        self.src_links.clear()

        for link in links_list:
            sw_src = link.src.dpid
            sw_dst = link.dst.dpid
            src_port = link.src.port_no
            dst_port = link.dst.port_no
            src_port_name = link.src.name
            dst_port_name = link.dst.name
            self.port_name_to_num[src_port_name] = src_port
            self.port_name_to_num[dst_port_name] = dst_port
            self.src_links[sw_src][(sw_src, sw_dst)] = (src_port, dst_port)
            self.src_links[sw_dst][(sw_dst, sw_src)] = (dst_port, src_port)


class TrafficControlRestAPI(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(TrafficControlRestAPI, self).__init__(req, link, data, **config)
        self.datapaths = data['datapaths']
        self.flow_speed = data['flow_speed']
        self.port_speed = data['port_speed']
        self.strategy = data['strategy']

    @route('portspeed', '/speed/port/{dpid}', methods=['GET'])
    def get_port_speed(self, req, **kwargs):
        dpid = kwargs['dpid']
        port_speed_dpid = self.port_speed.get(int(dpid), None)
        if port_speed_dpid is None:
            body = {}
        else:
            body = json.dumps({dpid: port_speed_dpid})
        return Response(content_type='application/json', body=body)

    @route('flowspeed', '/speed/flow/{dpid}', methods=['GET'])
    def get_flow_speed_dpid(self, req, **kwargs):
        dpid = kwargs['dpid']
        flow_speed_dpid = self.flow_speed.get(int(dpid), None)
        if flow_speed_dpid is None:
            body = {}
        else:
            flow_speed_list = []
            for keys in flow_speed_dpid:
                match = {}
                for key in keys:
                    if key[1] is not None:
                        match[key[0]] = key[1]
                flow_speed_list.append({'match': match, 'speed': flow_speed_dpid[keys]})
            body = json.dumps({dpid: flow_speed_list})
        return Response(content_type='application/json', body=body)

    @route('showstrategy', '/strategy/strategies', methods=['GET'])
    def show_strategy(self, req, **kwargs):
        strategy_list = []
        for key in self.strategy:
            item = {'nw_src': key[0], 'nw_dst': key[1], 'tp_proto': key[2], 'tp_src': key[3],
                    'tp_dst': key[4], 'priority': self.strategy[key][0], 'bandwidth': self.strategy[key][1]}
            strategy_list.append(item)
        body = json.dumps(strategy_list)
        return Response(content_type='application/json', body=body)

    @route('addstrategy', '/strategy/add', methods=['POST'])
    def set_strategy(self, req, **kwargs):
        try:
            strategy = req.json if req.body else {}
        except ValueError:
            return Response(status=400, content_type='application/json', body=json.dumps({'result': 'illegal'}))
        # TODO
        self.strategy[(strategy.get('nw_src', '*'), strategy.get('nw_dst', '*'), strategy.get('tp_proto', '*'), 0, int(strategy.get('tp_dst', 0)))] = (int(strategy.get('priority', 0)), int(strategy.get('bandwidth', 0)))
        return Response(content_type='application/json', body=json.dumps({'result': 'success'}))

    @route('delstrategy', '/strategy/delete', methods=['POST'])
    def del_strategy(self, req, **kwargs):
        try:
            strategy = req.json if req.body else {}
        except ValueError:
            return Response(status=400, content_type='application/json', body=json.dumps({'result': 'illegal'}))
        del self.strategy[(strategy.get('nw_src', '*'), strategy.get('nw_dst', '*'), strategy.get('tp_proto', '*'), int(strategy.get('tp_src', 0)), int(strategy.get('tp_dst', 0)))]
        return Response(content_type='application/json', body=json.dumps({'result': 'success'}))
