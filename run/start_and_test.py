

from mininet.topo import Topo
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.link import Link
from mininet.link import TCIntf
from mininet.net import Mininet
from mininet.log import lg, info
from mininet.util import dumpNodeConnections
from mininet.cli import CLI
#from mininet.cli import do_net
from mininet.node import RemoteController
from mininet.node import OVSSwitch
from mininet.util import ( quietRun, dumpNodeConnections,dumpPorts,dumpNetConnections )


import sys
import os
from time import sleep, time

from subprocess import Popen,PIPE
from argparse import ArgumentParser

enable_ecn = 1
enable_red = 1
bw_receiver =1000
maxq=1000
delay=0
bw_sender = 1000
controller_address="192.168.50.8:6633"


parser = ArgumentParser(description="LLT")
parser.add_argument('--per_test', '-t',
                    dest="per_test",
                    type=int,
                    help="0:create 1:create_and_test",
                    default=0)

parser.add_argument('--dir', '-d',
                    help="Directory to store outputs",
                    default="test_result/")

parser.add_argument('--set_file', '-s',
                    help="Directory store the setting file",
                    default="~/LLT/controller/add_rate_limit.py")


args = parser.parse_args()

class MyTopo( Topo ):
    "Simple topology example."

    def __init__( self ):
        "Create custom topo."

        # Initialize topology
        Topo.__init__( self )
        
        #ECN in Linux is implemented using RED. The below set RED parameters 
        #to maintain K=20 packets where a packet size if 1500 bytes and we mark
        #packets with a probability of 1.

        switch2=self.addSwitch('s2')
        switch1=self.addSwitch('s1')
        switch0=self.addSwitch('s0')
                          
        # Add hosts and switches
        Host0 = self.addHost("h0")
        Host1 = self.addHost("h1")
        Host2 = self.addHost( 'h2' )
        Host3 = self.addHost( 'h3' )
        

        self.addLink(switch1,switch0)
        self.addLink(switch1,switch2)
        self.addLink(Host2,switch0)
        self.addLink(Host1,switch0)
        self.addLink(Host0,switch1)
        self.addLink(Host3,switch2)
        #self.addLink(Host0,Host1)

def set_controller(switch_num=3):
    os.system("echo set controller and manager")
    """
    for i in range(1,args.n):
        switch = net.get('s%s' % i)
        print "Setting switch s%d"%i
    
    for i in n:
        os.system("sudo ovs-vsctl set-controller s%s tcp:127.0.0.1;port6633" %i)
    """
    for i in range(switch_num):
        s_n=str(i)
        os.system("sudo ovs-vsctl set Bridge s%s protocol=OpenFlow13" % s_n)
        os.system("sudo ovs-vsctl set-controller s%s tcp:%s" % (s_n,controller_address))
    
    """
    os.system("ovs-vsctl set-manager ptcp:6632")
    os.system("sudo ifconfig eth1 up")
    os.system("sudo ifconfig eth2 up")

    #os.system("sudo ifconfig eth4 up")
    os.system("sudo ovs-vsctl add-port s1 eth1")
    os.system("sudo ovs-vsctl add-port s2 eth2")
    #os.system("sudo ovs-vsctl add-port s3 eth4")
    """
    os.system("sysctl -w net.ipv4.tcp_ecn=1")
    os.system("echo ECN enable")    
    os.system("sysctl -w net.ipv4.tcp_congestion_control=dctcp")
    os.system("echo DCTCP enable")
    os.system("echo now begin : cong is :")
    os.system("sudo cat /proc/sys/net/ipv4/tcp_congestion_control")
    os.system("echo now see ecn enable :")
    os.system("sudo cat /proc/sys/net/ipv4/tcp_ecn")
    

def set_ECN_prio(inter_face="s0-eth1"):
    os.system("sudo tc qdisc add dev %s root handle 1: red limit 1500000 min 4500 max 7501 avpkt 1500 burst 3 ecn probability 1 bandwidth 1000Mbit" % inter_face)
    os.system("sudo tc qdisc add dev %s parent 1: handle 2: netem limit 100" % inter_face)

    os.system("sudo tc qdisc add dev %s parent 2: handle 3: prio" % inter_face)

    os.system("sudo tc filter add dev %s protocol ip parent 3: prio 1 u32 match ip dsfield 240 0xfc flowid 3:1" % inter_face)
    os.system("sudo tc filter add dev %s protocol ip parent 3: prio 2 u32 match ip dsfield 160 0xfc flowid 3:2" % inter_face)
    os.system("sudo tc filter add dev %s protocol ip parent 3: prio 3 u32 match ip dst 0.0.0.0/0    flowid 3:3" % inter_face)
    print inter_face+" setting end"
    

def set_each_interface(net):
    switch_interface=[]    
    for switch in net.switches:
        for intf in switch.intfList():
            port=switch.ports[intf]
            if str(intf)!="lo":
                #switch_interface.append(str(intf))
                set_ECN_prio(str(intf))


def perf_test(net):
    net.pingAll()
    result=net.pingAll()
    print "***********************the result = ",result
    while result!=0.0:
        print "not ping all,check your flow entry"
        result=net.pingAll()

    os.system("cd %s && sudo rm -rf *" % args.dir)

    print "setting the flow htb , priority"
    os.system("sudo python %s" % args.set_file)


    h0=net.get('h0')
    print "Starting iperf server..."
    server = h0.popen("iperf -s -w 16m > %s/iperf-server.txt " %(args.dir),shell=True)
    print "start sockperf ..."
    sockperf_server = h0.popen("sockperf server -p 5002 --tcp")
    sleep(2)
    h1=net.get('h1')
    print "start iperf clinet h1"
    clinet = h1.popen("iperf -c %s -p 5001 -t 20 > %s/iperf_h1.txt " %(h0.IP(),args.dir), 
                      shell=True)
    sockperf_h1_client = h1.popen("sockperf pp -i %s -t 5 -p 5002 --tcp > %s/sockperf.txt" %(h0.IP(),args.dir),shell=True)

    h2=net.get('h2')
    print "start iperf clinet h2"
    clinet = h2.popen("iperf -c %s -p 5003 -t 20 > %s/iperf_h2.txt " %(h0.IP(),args.dir), 
                      shell=True)

    time_count=0
    while time_count<50:
        sleep(1)
        time_count=time_count+1

    return





def clean_qos():
    os.system("sudo ovs-vsctl --all destroy QoS")
    os.system("sudo ovs-vsctl --all destroy Queue")

def genericCreate(topo):
    clean_qos()
    os.system("sudo mn -c")
    print "clean qos and queue"
    net = Mininet(topo=topo,link=TCLink,switch=OVSSwitch,controller=RemoteController)
    net.start()
    print "hahahah"
    set_controller(switch_num=len(net.switches))
    set_each_interface(net)
    if (args.per_test):
        perf_test(net)
    else:
        CLI(net)
    net.stop()



def main():
    topo = MyTopo()
    genericCreate(topo)   

if __name__ == '__main__':
    main()