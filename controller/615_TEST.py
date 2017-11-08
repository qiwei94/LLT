import os
import json
import struct

class mutiqueue_config():
    def __init__(self):
        self.exp_queue_msg = {}
        
    ## prepare queue messge
    def init_exp_queue_msg(self, dpid, experimenter, exp_type, exp_data):
        self.exp_queue_msg["dpid"]                = dpid
        self.exp_queue_msg["experimenter"]        = experimenter
        self.exp_queue_msg["exp_type"]            = exp_type
        self.exp_queue_msg["data_type"]           = "ascii"
        self.exp_queue_msg["data"]                = exp_data


    def strip_0x(self, string):
        if string.startswith('0x'):
            string = string[2:]
        return string

    def int32_to_str8(self, number):
        n = number
        b1 = hex((n & 0xf0000000) >> 28)
        b2 = hex((n & 0xf000000) >> 24)
        b3 = hex((n & 0xf00000) >> 20)
        b4 = hex((n & 0xf0000) >> 16)
        b5 = hex((n & 0xf000) >> 12)
        b6 = hex((n & 0xf00) >> 8)
        b7 = hex((n & 0xf0) >> 4)
        b8 = hex(n & 0xf)
        res_str4 = self.strip_0x(str(b1)) + self.strip_0x(str(b2)) + self.strip_0x(str(b3)) + self.strip_0x(str(b4)) +\
                   self.strip_0x(str(b5)) + self.strip_0x(str(b6)) + self.strip_0x(str(b7)) + self.strip_0x(str(b8))
        return res_str4

    def send_mutiqueue_qurery(self, port, queue_id):
        '''
        curl -X POST -d '{
            "dpid":1,
            "experimenter":7,
            "exp_type":0,
            "data_type": "ascii",
            "data": "00012222"}' http://localhost:8080/stats/experimenter/1
        '''
        queue_pase = (port << 6) + queue_id
        data_send = self.int32_to_str8(queue_pase)+"00000000"
        print data_send

        self.init_exp_queue_msg(1, 7, 0, data_send)
        curl_exp = json.dumps(self.exp_queue_msg)

        bashCommand = "curl -X POST -d '%s' http://localhost:8080/stats/experimenter/1"%curl_exp
        print bashCommand
        os.system(bashCommand)
 
    def send_mutiqueue_config(self, port, queue_id, weight):

        queue_pase = (port << 6) + queue_id
        data_send = self.int32_to_str8(queue_pase)+self.int32_to_str8(weight)
        print data_send

        self.init_exp_queue_msg(1, 7, 2, data_send)
        curl_exp = json.dumps(self.exp_queue_msg)

        bashCommand = "curl -X POST -d '%s' http://localhost:8080/stats/experimenter/1"%curl_exp
        print bashCommand
        os.system(bashCommand)



    def send_per_flow_qos(self,datapath_id,port_name,min_rate,max_rate):
        ###TODO:need to identify the datapath and port name automatelly

        bashCommand = "curl -X PUT -d \'\"tcp:127.0.0.1:6632\"\' http://localhost:8080/v1.0/conf/switches/"+datapath_id+"/ovsdb_addr"  
        print bashCommand
        os.system(bashCommand)



        rate_control = "curl -X POST -d \'{\"port_name\":"+port_name+", \"type\": \"linux-htb\", \"max_rate\":\"10000000000\",\"queues\": [{\"min_rate\":" \
                        +min_rate+", \"max_rate\": "+max_rate+"}]}' http://localhost:8080/qos/queue/"+datapath_id

        print rate_control
        os.system(rate_control)


    def check_per_flow_qos(self,datapath_id):

        #get the qos queue of the datapath switch
        bashCommand = "curl -X GET http://localhost:8080/qos/queue"+datapath_id
        print bashCommand
        os.system(bashCommand)




## prepare data 
class entry_struct:
    def __init__(self):
        self.pad_17   =-1
        self.port_2  =-1
        self.type_16 =-1
        self.vid_12  =-1
        self.pcp_3   =-1
        self.srca_32 =-1
        self.dsta_32 =-1
        self.proto_8 =-1
        self.tos_6   =-1
        self.srcp_16 =-1
        self.dstp_16 =-1

        self.priority   = 3

        self.output_pad_23  = 0
        self.output_queue_6 = 10
        self.output_port_3  = 2


    def init_flow_entry(self, inport, vlan, src_ip, dst_ip, src_port, dst_port, priority, output_port, output_queue):
        self.port_2  = inport
        self.vid_12  = vlan
        self.srca_32 = src_ip
        self.dsta_32 = dst_ip
        self.srcp_16 = src_port
        self.dstp_16 = dst_port
        self.priority   = priority
        self.output_queue_6 = output_queue
        self.output_port_3  = output_port+4

    def int2bin(self, n, count=24):  
        """returns the binary of integer n, using count number of digits"""  
        return "".join([str((n >> y) & 1) for y in range(count-1, -1, -1)])  

    def get_mask(self,x,y):
        if (x==-1):
            return self.int2bin(0,y)
        else:
            return self.int2bin((2**y-1),y)

    def trans_entry_to_bit_str(self):
        # entry = entry_struct()

        priority = ('{0:032b}'.format(self.priority))


        mask=(
            (self.get_mask(self.pad_17,17))+    \
            (self.get_mask(self.port_2,2))+     \
            (self.get_mask(self.type_16,16))+   \
            (self.get_mask(self.vid_12,12))+    \
            (self.get_mask(self.pcp_3,3))+      \
            (self.get_mask(self.srca_32,32))+   \
            (self.get_mask(self.dsta_32,32))+   \
            (self.get_mask(self.proto_8,8))+    \
            (self.get_mask(self.tos_6,6))+     \
            (self.get_mask(self.srcp_16,16))+  \
            (self.get_mask(self.dstp_16,16))   \
            )

        data=(
            ('{0:017b}'.format(self.pad_17))+   \
            ('{0:02b}'.format(self.port_2))+    \
            ('{0:016b}'.format(self.type_16))+   \
            ('{0:012b}'.format(self.vid_12))+    \
            ('{0:03b}'.format(self.pcp_3))+      \
            ('{0:032b}'.format(self.srca_32))+   \
            ('{0:032b}'.format(self.dsta_32))+   \
            ('{0:08b}'.format(self.proto_8))+    \
            ('{0:06b}'.format(self.tos_6))+     \
            ('{0:016b}'.format(self.srcp_16))+  \
            ('{0:016b}'.format(self.dstp_16))   \
            )

        data = data.replace('-', '0')
        print data 


        value =(
            ('{0:023b}'.format(self.output_pad_23))+       \
            ('{0:06b}'.format(self.output_queue_6))+       \
            (('{0:03b}'.format(self.output_port_3)))       \
            )

        res = {}

        res["priority"]  =  priority
        res["data"]      = data
        res["mask"]      = mask
        res["value"]     = value
        return res


    def trans_32_bitstr_to_hex(self, bit_str):
        data_res=""
        data=bit_str
        for i in range(32):
            if (i+1)%8==0:
                data_res=data_res+chr(int(data[i-7:i+1],2))
        return data_res

    def trans_143_bitstr_to_hex(self, bit_str):
        data_res_hex20=""

        # for i in range(160):
        #     if (i+1)%32==0:
        #         strs32 = bit_str[i-31:i+1]
        #         strs32_re = strs32[::-1]
        #         for j in range(32):
        #             if (j+1)%8==0:
        #                 # print hex(int(data[i-7:i+1],2))
        #                 data_res_hex20=data_res_hex20+chr(int(strs32_re[j-7:j+1],2))
                    
        for i in range(160):
            if (i+1)%8==0:
                data_res_hex20=data_res_hex20+chr(int(bit_str[i-7:i+1],2))
        return data_res_hex20


    def trans_to_data_send(self):

        bit_str = self.trans_entry_to_bit_str()
        # print "\nbit string:"
        # print bit_str

        data_res = {}
        data_res["priority"] = self.trans_32_bitstr_to_hex(bit_str["priority"])
        data_res["data"]     = self.trans_143_bitstr_to_hex(bit_str["data"])
        data_res["mask"]     = self.trans_143_bitstr_to_hex(bit_str["mask"])
        data_res["value"]    = self.trans_32_bitstr_to_hex(bit_str["value"])
        print "\nlast data_res in hex20:" 
        print data_res

        data_send = ""
        data_send = data_res["priority"]+data_res["value"]+data_res["data"]+data_res["mask"]
        print "\ndata_send:"
        print data_send.encode('hex')

        return data_send.encode('hex')



class mutiqueue_switch_add_entry:
    def __init__(self):
        self.exp_msg = {}

    ## prepare messge
    def init_ryu_exp_msg(self, dpid, experimenter, exp_type, exp_data):

        self.exp_msg["dpid"]                = dpid
        self.exp_msg["experimenter"]        = experimenter
        self.exp_msg["exp_type"]            = exp_type
        self.exp_msg["data_type"]           = "ascii"
        self.exp_msg["data"]                = exp_data

    ## send data
    def add_exp_entry(self, inport, vlan, src_ip, dst_ip, src_port, dst_port, priority, output_port, output_queue):

        flow_entry = entry_struct()
        flow_entry.init_flow_entry(inport, vlan, src_ip, dst_ip, src_port, dst_port, priority, output_port, output_queue)
        data_send = flow_entry.trans_to_data_send() 

        ## init a exp message
        dpid         = 1
        experimenter = 7
        exp_type     = 4
        self.init_ryu_exp_msg(dpid, experimenter, exp_type, data_send)
        print self.exp_msg
        curl_exp = json.dumps(self.exp_msg)

        bashCommand = "curl -X POST -d '%s' http://localhost:8080/stats/experimenter/1"%curl_exp
        print bashCommand
        os.system(bashCommand)





###set the ovs queue


## query queue stats
mutiqueue = mutiqueue_config()
"""
mutiqueue.send_mutiqueue_qurery(port=1, queue_id=10)
"""
## config queue stats


mutiqueue.send_mutiqueue_config(port=0, queue_id=0, weight=100)
mutiqueue.send_mutiqueue_config(port=1, queue_id=0, weight=100)

mutiqueue.send_mutiqueue_config(port=0, queue_id=1, weight=100)
mutiqueue.send_mutiqueue_config(port=1, queue_id=1, weight=100)


mutiqueue.send_mutiqueue_config(port=0, queue_id=2, weight=84)
mutiqueue.send_mutiqueue_config(port=1, queue_id=2, weight=84)


mutiqueue.send_mutiqueue_config(port=0, queue_id=3, weight=84)
mutiqueue.send_mutiqueue_config(port=1, queue_id=3, weight=84)

mutiqueue.send_mutiqueue_config(port=0, queue_id=4, weight=84)
mutiqueue.send_mutiqueue_config(port=1, queue_id=4, weight=84)


mutiqueue.send_mutiqueue_config(port=0, queue_id=5, weight=84)
mutiqueue.send_mutiqueue_config(port=1, queue_id=5, weight=84)

mutiqueue.send_mutiqueue_config(port=0, queue_id=6, weight=84)
mutiqueue.send_mutiqueue_config(port=1, queue_id=6, weight=84)

mutiqueue.send_mutiqueue_config(port=0, queue_id=7, weight=20000)
mutiqueue.send_mutiqueue_config(port=1, queue_id=7, weight=20000)



#mutiqueue.send_mutiqueue_config(port=0, queue_id=20, weight=200)
#mutiqueue.send_mutiqueue_config(port=1, queue_id=20, weight=200)


#mutiqueue.send_mutiqueue_config(port=0, queue_id=20, weight=200)
#mutiqueue.send_mutiqueue_config(port=1, queue_id=20, weight=200)



## add entry
send = mutiqueue_switch_add_entry()







send.add_exp_entry(inport=1, vlan=-1, src_ip=-1, dst_ip=-1, src_port=5001, dst_port=-1,\
                   priority=3, output_port=0, output_queue=1)

send.add_exp_entry(inport=1, vlan=-1, src_ip=-1, dst_ip=-1, src_port=-1, dst_port=5001,\
                   priority=4, output_port=0, output_queue=1)

send.add_exp_entry(inport=0, vlan=-1, src_ip=-1, dst_ip=-1, src_port=-1, dst_port=5001, \
                   priority=5, output_port=1, output_queue=1)

send.add_exp_entry(inport=0, vlan=-1, src_ip=-1, dst_ip=-1, src_port=5001, dst_port=-1, \
                   priority=6, output_port=1, output_queue=1)





send.add_exp_entry(inport=1, vlan=-1, src_ip=-1, dst_ip=-1, src_port=5002, dst_port=-1,\
                   priority=7, output_port=0, output_queue=7)

send.add_exp_entry(inport=1, vlan=-1, src_ip=-1, dst_ip=-1, src_port=-1, dst_port=5002,\
                   priority=8, output_port=0, output_queue=7)

send.add_exp_entry(inport=0, vlan=-1, src_ip=-1, dst_ip=-1, src_port=-1, dst_port=5002, \
                   priority=9, output_port=1, output_queue=7)

send.add_exp_entry(inport=0, vlan=-1, src_ip=-1, dst_ip=-1, src_port=5002, dst_port=-1, \
                   priority=10, output_port=1, output_queue=7)







send.add_exp_entry(inport=0, vlan=-1, src_ip=-1, dst_ip=-1, src_port=-1, dst_port=-1, \
                   priority=11, output_port=1, output_queue=0)

send.add_exp_entry(inport=1, vlan=-1, src_ip=-1, dst_ip=-1, src_port=-1, dst_port=-1, \
                   priority=12, output_port=0, output_queue=0)

"""
send.add_exp_entry(inport=2, vlan=-1, src_ip=-1, dst_ip=-1, src_port=-1, dst_port=-1, \
                   priority=5, output_port=3, output_queue=1)

send.add_exp_entry(inport=3, vlan=-1, src_ip=-1, dst_ip=-1, src_port=-1, dst_port=-1, \
                   priority=6, output_port=2, output_queue=1)
"""




## config queue stats
print "status:::::::::::::::::::::::::::::::::::::"
mutiqueue.send_mutiqueue_qurery(port=1, queue_id=1)
mutiqueue.send_mutiqueue_qurery(port=0, queue_id=7)

mutiqueue.send_mutiqueue_qurery(port=1, queue_id=1)
mutiqueue.send_mutiqueue_qurery(port=0, queue_id=7)

mutiqueue.send_mutiqueue_qurery(port=1, queue_id=0)
mutiqueue.send_mutiqueue_qurery(port=0, queue_id=0)


##send_per_flow_qos("0000000000000001","s1-eth1","20000000","20000000")

##check_per_flow_qos("0000000000000001")