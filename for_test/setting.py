#!/usr/bin/python

from mininet.topo import Topo
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.link import Link
from mininet.link import TCIntf
from mininet.net import Mininet
from mininet.log import lg, info
from mininet.util import dumpNodeConnections
from mininet.cli import CLI

from subprocess import Popen,PIPE
from time import sleep,time
from multiprocessing import Process
from argparse import ArgumentParser

from monitor import monitor_qlen
import termcolor as T

import sys
import os
import math
from math import sqrt


os.system("echo hahahahahhah")
os.system("sudo ovs-vsctl set Bridge s2 protocol=OpenFlow13")
os.system("sudo ovs-vsctl set Bridge s3 protocol=OpenFlow13")
#os.system("sudo ovs-vsctl set Bridge s4 protocol=OpenFlow13")
#os.system("sudo ovs-vsctl set Bridge s5 protocol=OpenFlow13")
#os.system("sudo ovs-vsctl set Bridge s6 protocol=OpenFlow13")
#os.system("sudo ovs-vsctl set Bridge s1 protocol=OpenFlow13")

#os.system("sudo ovs-vsctl add-port s2 eth1")
#os.system("sudo ovs-vsctl add-port s3 eth2")

os.system("ovs-vsctl set-manager ptcp:6632")



"""
os.system("ovs-ofctl -O OpenFlow13 add-flow s2 in_port=1,actions=output:2")
os.system("ovs-ofctl -O OpenFlow13 add-flow s2 in_port=2,actions=output:1")
os.system("ovs-ofctl -O OpenFlow13 add-flow s3 in_port=1,actions=output:2")
os.system("ovs-ofctl -O OpenFlow13 add-flow s3 in_port=2,actions=output:1")



os.system("sudo ovs-vsctl set Bridge s4 protocol=OpenFlow13")
os.system("sudo ovs-vsctl set Bridge s5 protocol=OpenFlow13")
os.system("sudo ovs-vsctl set Bridge s6 protocol=OpenFlow13")
os.system("sudo ovs-vsctl set Bridge s7 protocol=OpenFlow13")
os.system("sudo ovs-vsctl set Bridge s8 protocol=OpenFlow13")
os.system("sudo ovs-vsctl set Bridge s9 protocol=OpenFlow13")
os.system("sudo ovs-vsctl set Bridge s10 protocol=OpenFlow13")

"""


"""
os.system("")
os.system("")
os.system("")
os.system("")
os.system("")

os.system("")

"""
