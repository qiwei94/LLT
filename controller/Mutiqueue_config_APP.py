import re
import copy
import time
import struct
 
from ryu.ofproto import ofproto_v1_3_parser
from ryu.ofproto import ofproto_v1_3

from ryu import utils

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.app.wsgi import ControllerBase, WSGIApplication

class MutiqExperimenter(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(MutiqExperimenter, self).__init__(*args, **kwargs)

    @set_ev_cls(ofp_event.EventOFPExperimenter, MAIN_DISPATCHER)
    def mutiqueue_experimenter_handler(self, ev):
        msg = ev.msg

        dp = msg.datapath
        
        unif_queue_id, queue_stats = struct.unpack('>LL', bytes(msg.data))

        # queue_pase = (port << 6) + unif_queue_id
        
        port_num = unif_queue_id >> 6
        queue_num = unif_queue_id & 0x0000003f

        print "\n[MQ]: Got the queue stats msg, (port, queue, stats) = (%d, %d, %d)\n"%(port_num, queue_num, queue_stats)

