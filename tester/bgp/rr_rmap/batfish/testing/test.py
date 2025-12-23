# Import packages
import json
from utils import *
from typing import List, Optional  # noqa: F401
import pandas as pd
import time
from IPython.display import display
import glob
import os
import ipaddress
from pandas.io.formats.style import Styler
from pybatfish.client.session import Session
from pybatfish.datamodel import *
from pybatfish.datamodel.answer import *
from pybatfish.datamodel.flow import *
from pybatfish.util import get_html

bf = Session(host="localhost")

SNAPSHOT_DIR = '../../snapshot'

preamble = """
!
version 15.2
service timestamps debug datetime msec
service timestamps log datetime msec
!
hostname R1
!
boot-start-marker
boot-end-marker
no aaa new-model
no ip icmp rate-limit unreachable
ip cef
no ip domain lookup
ip domain name lab.local
no ipv6 cef
multilink bundle-name authenticated
ip tcp synwait-time 5
!
"""


def run_batfish_example():
    NETWORK_NAME = 'example'
    SNAPSHOT_NAME = 'example_snapshot'
    SNAPSHOT_PATH = '../../snapshot'

    bf.set_network(NETWORK_NAME)
    bf.init_snapshot(SNAPSHOT_PATH, name=SNAPSHOT_NAME, overwrite=True)
    
    df1 = bf.q.bgpRib(nodes='R1').answer().frame()
    df2 = bf.q.bgpRib(nodes='R2').answer().frame()
    df3 = bf.q.bgpRib(nodes='R3').answer().frame()
    
    newdf = (pd.concat([df1, df2, df3])).reset_index(drop=True)
    
    newdf = newdf[newdf['Network'] == route["prefix"]].reset_index(drop=True)
    
    return newdf

def write_config(route, rmap, router1, router2, router3):
    router1_config_lines = []
    router2_config_lines = []
    router3_config_lines = []
    
    preamble_lines = preamble.split('\n')
    
    router1_config_lines.extend(preamble_lines)
    router2_config_lines.extend(preamble_lines)
    router3_config_lines.extend(preamble_lines)
    
    router2_config_lines[6] = 'hostname R2'
    router3_config_lines[6] = 'hostname R3'
    
    ############################### ROUTER 1 CONFIGURATION ####################

    ## Find two usable ip for the route prefix
    net = ipaddress.ip_network(route["prefix"], strict=False)
    hosts = list(net.hosts())
    r1_ip = str(hosts[0]) if len(hosts) > 0 else str(net.network_address)
    nbr_ip = str(hosts[1]) if len(hosts) > 1 else r1_ip
    netmask = str(net.netmask)

    router1_config_lines.extend([
        'interface eth0/1',
        ' ip address 3.0.0.3 255.0.0.0',
        'interface eth0/2',
        f' ip address {r1_ip} {netmask}',
        '',
        'router bgp ' + str(router1['asNumber']),
        ' neighbor 3.0.0.2 remote-as ' + str(router2['asNumber']),
        f' neighbor {nbr_ip} remote-as 512',
        f' network {route["prefix"]}',
        ' network 3.0.0.0'
    ])
    
    if router1['isRR']:
        router1_config_lines.append(' neighbor 3.0.0.2 route-reflector-client')
        
    ############################### ROUTER 2 CONFIGURATION ####################
    pfxl_def = ""

    if "prefix_list" in rmap and rmap["prefix_list"] != []:
        prefix_list = rmap["prefix_list"]
        for prefix in prefix_list:
            pfxl_def += f"ip prefix-list PFXL {prefix['action']} {prefix['match']}\n"

    prefix_match = f"  match ip address prefix-list PFXL" if (("prefix_list" in rmap) and (rmap["prefix_list"] != [])) else ""

    
    router2_config_lines.extend([
        'interface eth0/1',
        ' ip address 3.0.0.2 255.0.0.0',
        'interface eth0/2',
        ' ip address 4.0.0.2 255.0.0.0',
        '',
        pfxl_def,
        'route-map RMap ' + rmap["rmap_action"] + ' 10',
        prefix_match,
        '',
        'router bgp ' + str(router2['asNumber']),
        ' neighbor 3.0.0.3 remote-as ' + str(router1['asNumber']),
        ' neighbor 4.0.0.3 remote-as ' + str(router3['asNumber']),
        ' neighbor 4.0.0.3 next-hop-self',
        ' neighbor 4.0.0.3 route-map RMap out',
        ' network 3.0.0.0',
        ' network 4.0.0.0'
    ])
    
    if router2['isRR1']:
        router2_config_lines.append(' neighbor 3.0.0.3 route-reflector-client')
        
    if router2['isRR3']:
        router2_config_lines.append(' neighbor 4.0.0.3 route-reflector-client')
        
    ############################### ROUTER 3 CONFIGURATION ####################
    router3_config_lines.extend([
        'interface eth0/1',
        ' ip address 4.0.0.3 255.0.0.0',
        '',
        'router bgp ' + str(router3['asNumber']),
        ' neighbor 4.0.0.2 remote-as ' + str(router2['asNumber']),
        ' network 4.0.0.0'
    ])
    
    if router3['isRR']:
        router3_config_lines.append(' neighbor 4.0.0.2 route-reflector-client')
        
    if not os.path.exists(SNAPSHOT_DIR):
        os.mkdir(SNAPSHOT_DIR)
        os.mkdir(SNAPSHOT_DIR + '/configs')
        
    with open(SNAPSHOT_DIR + '/configs/R1.cfg', 'w') as f:
        f.write('\n'.join(router1_config_lines))
    
    with open(SNAPSHOT_DIR + '/configs/R2.cfg', 'w') as f:
        f.write('\n'.join(router2_config_lines))
        
    with open(SNAPSHOT_DIR + '/configs/R3.cfg', 'w') as f:
        f.write('\n'.join(router3_config_lines))

    
### Execute Test Case ###

# load the test
with open("test.json", "r") as f:
    test = json.load(f)
print("Loaded test case")

# Parse the test case
route, rmap, p_inRRflag, p_outRRflag, p_inAS, p_outAS = test["route"], test["rmap"], test["inRRflag"], test["outRRflag"], test["inAS"], test["outAS"]
router2_asnum = 200; 
router1_asnum = router2_asnum if p_inAS else 100
router3_asnum = router2_asnum if p_outAS else 300
print("Parsed test case parameters")

if p_inRRflag == 0:
    isRR1 = False
    isClient1 = True
    isRR_router1 = True
    isClient_router1 = False
elif p_inRRflag == 1:
    isRR1 = True
    isClient1 = False
    isRR_router1 = False
    isClient_router1 = True
else:
    isRR1 = False
    isClient1 = False
    isRR_router1 = False
    isClient_router1 = False
    
if p_outRRflag == 0:
    isRR3 = False
    isClient3 = True
    isRR_router3 = True
    isClient_router3 = False
elif p_outRRflag == 1:
    isRR3 = True
    isClient3 = False
    isRR_router3 = False
    isClient_router3 = True
else:
    isRR3 = False
    isClient3 = False
    isRR_router3 = False
    isClient_router3 = False
    
router1 = {
    'asNumber': router1_asnum,
    'isRR': isRR_router1,
    'isClient': isClient_router1
}

router2 = {
    'asNumber': router2_asnum,
    'isRR1': isRR1,
    'isClient1': isClient1,
    'isRR3': isRR3,
    'isClient3': isClient3
}

router3 = {
    'asNumber': router3_asnum,
    'isRR': isRR_router3,
    'isClient': isClient_router3
}

write_config(route, rmap, router1, router2, router3)
new_df = run_batfish_example()
print("Batfish run completed. The results are:")
new_df_dict = new_df.to_dict(orient="records")
print(new_df_dict)
with open("output_df.json", "w", encoding="utf-8") as f:
    json.dump(new_df_dict, f, indent=4, default=str)



isReceivedR2 = False
isReceivedR3 = False

if 'r2' in new_df['Node'].tolist(): isReceivedR2 = True
if 'r3' in new_df['Node'].tolist(): isReceivedR3 = True


## Save R1, R2, R3 configs for debug
with open(SNAPSHOT_DIR + "/configs/R1.cfg", "r") as f: r1_cfg = f.read(); open("R1.cfg", "w").write(r1_cfg)
with open(SNAPSHOT_DIR + "/configs/R2.cfg", "r") as f: r2_cfg = f.read(); open("R2.cfg", "w").write(r2_cfg)
with open(SNAPSHOT_DIR + "/configs/R3.cfg", "r") as f: r3_cfg = f.read(); open("R3.cfg", "w").write(r3_cfg)
print("Saved R1.cfg, R2.cfg, R3.cfg for debug")


## Save the result 

with open("result.json", "w") as f:
    json.dump({
        "isRIB2": isReceivedR2,
        "isRIB3": isReceivedR3
    }, f, indent=2)



