turn into run/start_and_test.py

# steps
step 1: 
create the topo you need in function MyTopo( Topo )

step 2: 
set the controller address at the beginning of the file

step 3:
sudo pyhton run/start_and_test.py

step 4:
use the add_rate_limit.py in controller to add rate-limit
	
	turn into controller/add_rate_limit.py

	step 0:
	change the user_name , passwd and user_ip at the top of the file

	step 1: add the interface of the link  
	add_htb("s1-eth1")
	
	step 2: add rate_limit
	add_flow_rate_limit("s1-eth1",priority=0,flow_id=7,rate=50,\
    					ip_src="10.0.0.2",\
    					ip_dst="10.0.0.1",\
    					port_src="0",\
    					port_dst="5010",\
    					protocol="TCP")
 	
 	explaination:
	dev : the dev need to add rate-limiter
	priority : the flow priority , which is in {0,1,2.....}
	flow_id : used to identify the flow , each flow_id is unique
	rate : the bandwitch : mbps
	
	5-tuple:
		ip_src
		ip_dst
		port_src
		port_dst
		protocol 
	the any match is :
	ip : 0.0.0.0/0
	port : 0
	protocol : 0

	filter_prio : the priority of filter , 0 is the default and highest priority

	step 3: delete some rate limit if need
	delete_flow_rate_limit("s1-eth1",priority=0,flow_id=7)