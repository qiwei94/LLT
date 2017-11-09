"""Custom topology example
Two directly connected switches plus a host for each switch:
   host --- switch --- switch --- host
Adding the 'topos' dict with a key/value pair to generate our newly defined
topology enables one to pass in '--topo=mytopo' from the command line.
"""

from mininet.topo import Topo
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.link import Link
from mininet.link import TCIntf
from mininet.net import Mininet
from mininet.log import lg, info
from mininet.util import dumpNodeConnections
from mininet.cli import CLI
from mininet.node import RemoteController
from mininet.node import OVSSwitch

from argparse import ArgumentParser

import sys
import os

from subprocess import Popen,PIPE
#from time import sleep,time
#from multiprocessing import Process
#from argparse import ArgumentParser

#from monitor import monitor_qlen
#import termcolor as T

#import sys
#import os
#import math
#from math import sqrt


enable_ecn = 1
enable_red = 1
bw_receiver =1000
maxq=1000
delay=0
bw_sender = 1000

class MyTopo( Topo ):
    "Simple topology example."

    def __init__( self ):
        "Create custom topo."

        # Initialize topology
        Topo.__init__( self )
        
        #ECN in Linux is implemented using RED. The below set RED parameters 
        #to maintain K=20 packets where a packet size if 1500 bytes and we mark
        #packets with a probability of 1.
        self.red_params = {'min':6000, #K=20pkts
                           'max':6001,
                           'avpkt':1500,
                           'burst':5,
                           'prob':1,
                           'limit':150000,
                         }

        #switch3=self.addSwitch('s4')
        switch3=self.addSwitch('s3')
        switch2=self.addSwitch('s2')
        switch1=self.addSwitch('s1')



        switchConfig = {'enable_ecn': enable_ecn, 
                        'enable_red': enable_ecn, 
                        'red_params': self.red_params \
                                    if enable_ecn is 1 else None,
                        'bw':bw_receiver,
                        'delay':delay,
                        'max_queue_size':maxq}

        switchConfig2 = {'enable_ecn': 0, 
                        'enable_red': 0, 
                        'bw':bw_receiver,
                        'delay':delay,
                        'max_queue_size':maxq}


        senderConfig = {'bw':bw_sender, 
                        'delay':delay,
                        'max_queue_size':maxq}

        receiverConfig = {'bw':bw_receiver, 
                          'delay':delay,
                          'max_queue_size':maxq}

                          
        # Add hosts and switches
        Host0 = self.addHost("h0")
        Host1 = self.addHost("h1")
        Host2 = self.addHost( 'h2' )
        #Host3 = self.addHost( 'h3' )
        #Host4 = self.addHost( 'h4' )
        #Host5 = self.addHost( 'h5' )

        # Add links
        """
        self.addLink(switch2, switch3, cls=Link, cls1=TCIntf, cls2=TCIntf, 
                      params1=receiverConfig, params2=switchConfig)
        """
        
        self.addLink(switch2,switch3)
        self.addLink(Host1,switch3)
        self.addLink(Host2,switch3)
        self.addLink(Host0,switch1)
       


def set_controller():
    os.system("echo set controller and manager")
    """
    for i in range(1,args.n):
        switch = net.get('s%s' % i)
        print "Setting switch s%d"%i
    
    for i in n:
        os.system("sudo ovs-vsctl set-controller s%s tcp:127.0.0.1;port6633" %i)
    """
    

    os.system("sudo ovs-vsctl set Bridge s1 protocol=OpenFlow13")
    os.system("sudo ovs-vsctl set Bridge s2 protocol=OpenFlow13")
    os.system("sudo ovs-vsctl set Bridge s3 protocol=OpenFlow13")
    #os.system("sudo ovs-vsctl set Bridge s4 protocol=OpenFlow13")
    #os.system("sudo ovs-vsctl set Bridge s5 protocol=OpenFlow13")


    
    os.system("sudo ovs-vsctl set-controller s1 tcp:192.168.50.8:6633")
    os.system("sudo ovs-vsctl set-controller s2 tcp:192.168.50.8:6633")
    os.system("sudo ovs-vsctl set-controller s3 tcp:192.168.50.8:6633")
    #os.system("sudo ovs-vsctl set-controller s4 tcp:192.168.50.8:6633")
    #os.system("sudo ovs-vsctl set-controller s5 tcp:192.168.50.8:6633")      

    os.system("ovs-vsctl set-manager ptcp:6632")
    os.system("sudo ifconfig eth1 up")
    os.system("sudo ifconfig eth2 up")

    #os.system("sudo ifconfig eth4 up")
    os.system("sudo ovs-vsctl add-port s1 eth1")
    os.system("sudo ovs-vsctl add-port s2 eth2")
    #os.system("sudo ovs-vsctl add-port s3 eth4")
    os.system("sysctl -w net.ipv4.tcp_ecn=1")
    os.system("echo ECN enable")    
    os.system("sysctl -w net.ipv4.tcp_congestion_control=dctcp")
    os.system("echo DCTCP enable")
    os.system("echo now begin : cong is :")
    os.system("sudo cat /proc/sys/net/ipv4/tcp_congestion_control")
    os.system("echo now see ecn enable :")
    os.system("sudo cat /proc/sys/net/ipv4/tcp_ecn")


def set_PRIO(inter_face="s0-eth1"):
    #os.system("sudo tc qdisc del dev %s root" % inter_face)
    os.system("sudo tc qdisc add dev %s root handle 1: prio" % inter_face)
    #os.system("sudo tc qdisc add dev %s parent 1:1 handle 10: pfifo limit 100" % inter_face)
    #os.system("sudo tc qdisc add dev %s parent 1:2 handle 20: pfifo limit 100" % inter_face)
    #os.system("sudo tc qdisc add dev %s parent 1:3 handle 30: pfifo limit 100" % inter_face)
    os.system("sudo tc filter add dev %s protocol ip parent 1: prio 1 u32 match ip dsfield 240 0xfc flowid 1:1" % inter_face)
    os.system("sudo tc filter add dev %s protocol ip parent 1: prio 1 u32 match ip dsfield 160 0xfc flowid 1:2" % inter_face)
    os.system("sudo tc filter add dev %s protocol ip parent 1: prio 2 u32 match ip dst 0.0.0.0/0 flowid 1:3" % inter_face)

def show_tc_setting(inter_face="s0-eth1"):
    os.system("echo tc setting is : ")
    os.system("echo #######################################################################")
    os.system("echo qdisc ::::::::::::::: ")
    os.system("sudo tc -s qdisc show dev %s" % inter_face)
    os.system("echo #######################################################################")
    os.system("echo class ::::::::::::::: ")
    os.system("sudo tc -s class show dev %s" % inter_face)
    os.system("echo #######################################################################")
    os.system("echo filter ::::::::::::::: ")
    os.system("sudo tc -s filter show dev %s parent 3:" % inter_face)
    os.system("echo #######################################################################")

### can set the ECN and the queue num
### since the PRIO SETTINHG is every where , the ECN shold be after the PRIO QDISC 
### ONLY ECN ALL THREE LEVEL FLOW USE THE SAME THRESHOLD , THIS CAN BE BETTER
def set_bottleneck(inter_face="s0-eth1"):
    #os.system("sudo tc qdisc del dev s3-eth1 parent 6: handle 10:")
    #os.system("sudo tc qdisc del dev s3-eth1 parent 5:1 handle 6:")
    os.system("sudo tc qdisc add dev %s parent 1:1 handle 10: red limit 1500000 min 4500 max 7501 avpkt 1500 burst 3 ecn probability 1 bandwidth 1000Mbit" % inter_face)
    os.system("sudo tc qdisc add dev %s parent 10: handle 100: netem limit 100" % inter_face)
    os.system("sudo tc qdisc add dev %s parent 1:2 handle 20: red limit 1500000 min 4500 max 7501 avpkt 1500 burst 3 ecn probability 1 bandwidth 1000Mbit" % inter_face)
    os.system("sudo tc qdisc add dev %s parent 20: handle 200: netem limit 100" % inter_face)
    os.system("sudo tc qdisc add dev %s parent 1:3 handle 30: red limit 1500000 min 4500 max 7501 avpkt 1500 burst 3 ecn probability 1 bandwidth 1000Mbit" % inter_face)
    os.system("sudo tc qdisc add dev %s parent 30: handle 300: netem limit 100" % inter_face)
    

def set_ECN_prio(inter_face="s0-eth1"):
    os.system("sudo tc qdisc add dev %s root handle 1: red limit 1500000 min 4500 max 7501 avpkt 1500 burst 3 ecn probability 1 bandwidth 1000Mbit" % inter_face)
    os.system("sudo tc qdisc add dev %s parent 1: handle 2: netem limit 100" % inter_face)

    os.system("sudo tc qdisc add dev %s parent 2: handle 3: prio" % inter_face)

    #os.system("sudo tc qdisc add dev %s parent 3:1 handle 10: pfifo limit 100" % inter_face)
    #os.system("sudo tc qdisc add dev %s parent 3:2 handle 20: pfifo limit 100" % inter_face)
    #os.system("sudo tc qdisc add dev %s parent 3:3 handle 30: pfifo limit 100" % inter_face)

    os.system("sudo tc filter add dev %s protocol ip parent 3: prio 1 u32 match ip dsfield 240 0xfc flowid 3:1" % inter_face)
    os.system("sudo tc filter add dev %s protocol ip parent 3: prio 1 u32 match ip dsfield 160 0xfc flowid 3:2" % inter_face)
    os.system("sudo tc filter add dev %s protocol ip parent 3: prio 2 u32 match ip dst 0.0.0.0/0    flowid 3:3" % inter_face)
    print "filter end"






def clean_qos():
    os.system("sudo ovs-vsctl --all destroy QoS")
    os.system("sudo ovs-vsctl --all destroy Queue")

def genericTest(topo):
    clean_qos()
    print "clean qos and queue"
    net = Mininet(topo=topo,link=TCLink,switch=OVSSwitch,controller=RemoteController)
    net.start()
    print "hahahah"

    #set_PRIO("s3-eth1")
    #set_bottleneck("s3-eth1")
    set_ECN_prio("s3-eth1")
    set_ECN_prio("s1-eth1")
    show_tc_setting("s3-eth1")

    set_controller()
    CLI(net)

    ###setting the manager ip and port
    net.stop()

def main():
    topo = MyTopo()
    genericTest(topo)   

if __name__ == '__main__':
    main()