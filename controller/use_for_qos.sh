



ryu-manager ofctl_rest.py rest_qos.py qos_simple_switch_13.py rest_conf_switch.py

curl -X PUT -d '"tcp:192.168.50.61:6632"' http://localhost:8080/v1.0/conf/switches/0000000000000001/ovsdb_addr

ovs-vsctl --db=tcp:192.168.50.61:6632 \
set port s1-eth1 qos=@newqos -- --id=@newqos create qos type=linux-htb \
other-config:max-rate=1000000 queues=0=@q0,1=@q1,2=@q2,3=@q3,4=@q4,5=@q5,6=@q6,7=@q7 \
-- --id=@q0 create queue other-config:priority=0 \
-- --id=@q1 create queue other-config:priority=1 \
-- --id=@q2 create queue other-config:priority=2 \
-- --id=@q3 create queue other-config:priority=3 \
-- --id=@q4 create queue other-config:priority=4 \
-- --id=@q5 create queue other-config:priority=5 \
-- --id=@q6 create queue other-config:priority=6 \
-- --id=@q7 create queue other-config:priority=7 



ovs-vsctl --db=tcp:192.168.50.61:6632 \
set port s1-eth1 qos=@newqos -- --id=@newqos create qos type=linux-htb \
other-config:max-rate=1000000 queues=0=@q0,1=@q1,2=@q2,3=@q3 \
-- --id=@q0 create queue other-config:priority=0,max-rate=100M \
-- --id=@q1 create queue other-config:priority=1,max-rate=200M \
-- --id=@q2 create queue other-config:priority=2,max-rate=300M \
-- --id=@q3 create queue other-config:priority=3,max-rate=1000M


#THE TOTAL BANDWIDTH IS 1G
#QUEUE0 IS DEFAULT : MAX 800M  PRIORITY : LOW
#QUEUE1 MAX:500M	PRIORITY : 2
#QUEUE2 MAX:200M	PRIORITY : 1													
#QUEUE3 MAX:100M  	PRIORITY : 0											
curl -X POST -d '{"port_name": "s1-eth1", "type": "linux-htb", "max_rate":"1000000000", "queues": [{"max_rate": "800000000","dscp":"10"},{"max_rate": "500000000"},{"max_rate": "200000000"},{"max_rate": "100000000"}]}' \
http://localhost:8080/qos/queue/0000000000000001






curl -X POST -d '{"priority": "1","match": {"nw_dst": "10.0.0.1", "nw_proto": "UDP", "tp_dst":"5002"}, "actions":{"queue": "1"}}' http://localhost:8080/qos/rules/0000000000000001
curl -X POST -d '{"priority": "1","match": {"nw_dst": "10.0.0.1", "nw_proto": "UDP", "tp_dst":"5003"}, "actions":{"queue": "2"}}' http://localhost:8080/qos/rules/0000000000000001
curl -X POST -d '{"priority": "1","match": {"nw_dst": "10.0.0.1", "nw_proto": "UDP", "tp_dst":"5004"}, "actions":{"queue": "3"}}' http://localhost:8080/qos/rules/0000000000000001

curl -X POST -d '{"priority": "1","match": {"nw_dst": "10.0.0.1", "nw_proto": "TCP", "tp_dst":"5002"}, "actions":{"queue": "1"}}' http://localhost:8080/qos/rules/0000000000000001
curl -X POST -d '{"priority": "1","match": {"nw_dst": "10.0.0.1", "nw_proto": "TCP", "tp_dst":"5003"}, "actions":{"queue": "2"}}' http://localhost:8080/qos/rules/0000000000000001
curl -X POST -d '{"priority": "1","match": {"nw_dst": "10.0.0.1", "nw_proto": "TCP", "tp_dst":"5004"}, "actions":{"queue": "3"}}' http://localhost:8080/qos/rules/0000000000000001



###mark the flow 
curl -X POST -d '{"match": {"nw_dst": "10.0.0.1", "nw_proto": "TCP", "tp_dst": "5001"}, "actions":{"mark": "60"}}' http://localhost:8080/qos/rules/0000000000000003

curl -X POST -d '{"match": {"nw_dst": "10.0.0.1", "nw_proto": "UDP", "tp_dst": "5002"}, "actions":{"mark": "26"}}' http://localhost:8080/qos/rules/0000000000000002 




curl -X POST -d '{"priority": "1","match": {"nw_dst": "10.0.0.1", "nw_proto": "TCP", "tp_dst":"5001"}, "actions":{"queue": "1"}}' http://localhost:8080/qos/rules/0000000000000001






tc qdisc add dev s1-eth1 parent 3:1 handle 4: htb default 30
tc class add dev s1-eth1 parent 4:  classid 4:1 htb rate 60mbit burst 15k
tc class add dev s1-eth1 parent 4:  classid 4:2 htb rate 100mbit burst 15k
tc class add dev s1-eth1 parent 4:  classid 4:3 htb rate 200mbit burst 15k


tc qdisc add dev s1-eth1 parent 3:2 handle 5: htb default 30
tc class add dev s1-eth1 parent 5:  classid 5:1 htb rate 40mbit burst 15k
tc class add dev s1-eth1 parent 5:  classid 5:2 htb rate 150mbit burst 15k
tc class add dev s1-eth1 parent 5:  classid 5:3 htb rate 250mbit burst 15k


tc qdisc add dev s1-eth1 parent 3:3 handle 5: htb default 30
tc class add dev s1-eth1 parent 6:  classid 5:1 htb rate 10mbit burst 15k
tc class add dev s1-eth1 parent 6:  classid 5:2 htb rate 300mbit burst 15k
tc class add dev s1-eth1 parent 6:  classid 5:3 htb rate 450mbit burst 15k










### queue-mapping
curl -X POST -d '{"match": {"ip_dscp": "63"}, "actions":{"queue": "0"}}' http://localhost:8080/qos/rules/0000000000000001
curl -X POST -d '{"match": {"ip_dscp": "55"}, "actions":{"queue": "1"}}' http://localhost:8080/qos/rules/0000000000000001
curl -X POST -d '{"match": {"ip_dscp": "47"}, "actions":{"queue": "2"}}' http://localhost:8080/qos/rules/0000000000000001
curl -X POST -d '{"match": {"ip_dscp": "39"}, "actions":{"queue": "3"}}' http://localhost:8080/qos/rules/0000000000000001
curl -X POST -d '{"match": {"ip_dscp": "31"}, "actions":{"queue": "4"}}' http://localhost:8080/qos/rules/0000000000000001
curl -X POST -d '{"match": {"ip_dscp": "23"}, "actions":{"queue": "5"}}' http://localhost:8080/qos/rules/0000000000000001
curl -X POST -d '{"match": {"ip_dscp": "15"}, "actions":{"queue": "6"}}' http://localhost:8080/qos/rules/0000000000000001
curl -X POST -d '{"match": {"ip_dscp": "7"}, "actions":{"queue": "7"}}' http://localhost:8080/qos/rules/0000000000000001




curl -X POST -d '{"priority": "10","match": {"nw_dst": "10.0.0.2", "nw_proto": "UDP", "tp_dst":"5001"}, "actions":{"queue": "1"}}' http://localhost:8080/qos/rules/0000000000000001
curl -X POST -d '{"priority": "11","match": {"nw_dst": "10.0.0.2", "nw_proto": "UDP", "tp_dst":"5003"}, "actions":{"queue": "0"}}' http://localhost:8080/qos/rules/0000000000000001

curl -X POST -d '{"priority": "1","match": {"nw_dst": "10.0.0.2", "nw_proto": "TCP", "tp_dst":"5003"}, "actions":{"queue": "0"}}' http://localhost:8080/qos/rules/0000000000000001





curl -X POST -d '{"priority":"10",match": {"tp_dst": "5001"}, "actions":{"queue": "0"}}' http://localhost:8080/qos/rules/0000000000000001

curl -X POST -d '{"priority":"11",match": {"tp_dst": "5003"}, "actions":{"queue": "1"}}' http://localhost:8080/qos/rules/0000000000000001




sudo tc qdisc add dev s1-eth1 parent 3:1 handle 4: htb default 30
sudo tc class add dev s1-eth1 parent 4:  classid 4:1 htb rate 60mbit burst 15k
sudo tc class add dev s1-eth1 parent 4:  classid 4:2 htb rate 100mbit burst 15k
sudo tc class add dev s1-eth1 parent 4:  classid 4:3 htb rate 200mbit burst 15k

sudo tc qdisc add dev s1-eth1 parent 3:2 handle 5: htb default 30
sudo tc class add dev s1-eth1 parent 5:  classid 5:1 htb rate 40mbit burst 15k
sudo tc class add dev s1-eth1 parent 5:  classid 5:2 htb rate 150mbit burst 15k
sudo tc class add dev s1-eth1 parent 5:  classid 5:3 htb rate 250mbit burst 15k

sudo tc qdisc add dev s1-eth1 parent 3:3 handle 6: htb default 30
sudo tc class add dev s1-eth1 parent 6:  classid 6:1 htb rate 10mbit burst 15k
sudo tc class add dev s1-eth1 parent 6:  classid 6:2 htb rate 300mbit burst 15k
sudo tc class add dev s1-eth1 parent 6:  classid 6:3 htb rate 450mbit burst 15k
sudo tc class add dev s1-eth1 parent 6:  classid 6:4 htb rate 600mbit burst 15k prio 100





sudo tc filter add dev s1-eth1 protocol ip parent 4:0 prio 1 u32 \
match ip src 10.0.0.2/24 \
match ip dst 10.0.0.1/24 \
match ip dport 5001 0xffff flowid 4:2

sudo tc filter add dev s1-eth1 protocol ip parent 6:0 prio 1 u32 \
match ip src 10.0.0.2/24 \
match ip dst 10.0.0.1/24 \
match ip dport 5003 0xffff flowid 6:3


sudo tc filter add dev s1-eth1 protocol ip parent 6:0 prio 1 u32 \
match ip src 0.0.0.0/0 flowid 6:4

##delete 
sudo tc filter del dev s1-eth1 parent 4:0 flowid 4:7