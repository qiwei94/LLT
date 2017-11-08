class entry_struct:
    def __init__(self, in_port, src_ip, dst_ip, src_port, dst_port, priority, out_port, output_queue):
        self.pad_17 = -1
        self.port_2 = in_port
        self.type_16 = -1
        self.vid_12 = -1
        self.pcp_3 = -1
        self.srca_32 = src_ip
        self.dsta_32 = dst_ip
        self.proto_8 = -1
        self.tos_6 = -1
        self.srcp_16 = src_port
        self.dstp_16 = dst_port

        self.priority = priority

        self.output_pad_23 = 0
        self.output_queue_6 = output_queue
        self.output_port_3  = out_port + 4

    def int2bin(self, n, count=24):
        """returns the binary of integer n, using count number of digits"""
        return "".join([str((n >> y) & 1) for y in range(count-1, -1, -1)])

    def get_mask(self, x, y):
        if x == -1:
            return self.int2bin(0, y)
        else:
            return self.int2bin((2 ** y - 1), y)

    def trans_entry_to_bit_str(self):

        priority = ('{0:032b}'.format(self.priority))

        mask = (
            (self.get_mask(self.pad_17, 17)) +    \
            (self.get_mask(self.port_2, 2)) +     \
            (self.get_mask(self.type_16, 16)) +   \
            (self.get_mask(self.vid_12, 12)) +    \
            (self.get_mask(self.pcp_3, 3)) +      \
            (self.get_mask(self.srca_32, 32)) +   \
            (self.get_mask(self.dsta_32, 32)) +   \
            (self.get_mask(self.proto_8, 8)) +    \
            (self.get_mask(self.tos_6, 6)) +     \
            (self.get_mask(self.srcp_16, 16)) +  \
            (self.get_mask(self.dstp_16, 16))   \
            )

        data = (
            ('{0:017b}'.format(self.pad_17)) +   \
            ('{0:02b}'.format(self.port_2)) +    \
            ('{0:016b}'.format(self.type_16)) +   \
            ('{0:012b}'.format(self.vid_12)) +    \
            ('{0:03b}'.format(self.pcp_3)) +      \
            ('{0:032b}'.format(self.srca_322)) +   \
            ('{0:032b}'.format(self.dsta_32)) +   \
            ('{0:08b}'.format(self.proto_8)) +    \
            ('{0:06b}'.format(self.tos_6)) +     \
            ('{0:016b}'.format(self.srcp_16)) +  \
            ('{0:016b}'.format(self.dstp_16))   \
            )

        data = data.replace('-', '0')

        value =(
            ('{0:023b}'.format(self.output_pad_23)) +       \
            ('{0:06b}'.format(self.output_queue_6)) +       \
            (('{0:03b}'.format(self.output_port_3)))       \
            )

        res = {}

        res["priority"] = priority
        res["data"] = data
        res["mask"] = mask
        res["value"] = value
        return res


    def trans_32_bitstr_to_hex(self, bit_str):
        data_res = ""
        data = bit_str
        for i in range(32):
            if (i + 1) % 8 == 0:
                data_res = data_res+chr(int(data[i-7:i+1], 2))
        return data_res

    def trans_143_bitstr_to_hex(self, bit_str):
        data_res_hex20 = ""

        for i in range(160):
            if (i+1)%8 == 0:
                data_res_hex20 = data_res_hex20+chr(int(bit_str[i-7:i+1], 2))
        return data_res_hex20


    def trans_to_data_send(self):

        bit_str = self.trans_entry_to_bit_str()

        data_res = {}
        data_res["priority"] = self.trans_32_bitstr_to_hex(bit_str["priority"])
        data_res["data"] = self.trans_143_bitstr_to_hex(bit_str["data"])
        data_res["mask"] = self.trans_143_bitstr_to_hex(bit_str["mask"])
        data_res["value"] = self.trans_32_bitstr_to_hex(bit_str["value"])
        print "\nlast data_res in hex20:"
        print data_res

        data_send = ""
        data_send = data_res["priority"]+data_res["value"]+data_res["data"]+data_res["mask"]
        print "\ndata_send:"
        print data_send.encode('hex')

        return data_send.encode('hex')
