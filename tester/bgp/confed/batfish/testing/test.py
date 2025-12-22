# Import packages
import json
from utils import *
from typing import List, Optional  # noqa: F401
import pandas as pd
import time
from IPython.display import display
import glob
import os
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
    
    newdf = newdf[newdf['Network'] == '100.0.0.0/8'][["Node", "AS_Path", "Local_Pref"]].reset_index(drop=True)
    
    return newdf

def write_config(originAS, router2, router3, remove_private_as_flag, replace_as_flag, local_preference):
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
    router1_config_lines.extend([
        'interface eth0/1',
        ' ip address 3.0.0.3 255.0.0.0',
        'interface eth0/2',
        ' ip address 100.0.0.1 255.0.0.0',
        '',
        'router bgp ' + str(originAS),
        ' neighbor 3.0.0.2 remote-as ' + str(router2['asNumber']),
        ' neighbor 100.0.0.2 remote-as ' + str(originAS),
        ' network 100.0.0.0',
    ])
    
    ############################### ROUTER 2 CONFIGURATION ####################
    router2_config_lines.extend([
        'interface eth0/1',
        ' ip address 3.0.0.2 255.0.0.0',
        'interface eth0/2',
        ' ip address 4.0.0.2 255.0.0.0',
        '',
        'route-map RM1 permit 10',
        ' set local-preference ' + str(local_preference),
        '',
    ])
    
    if router2['subAS'] != 0:
        router2_config_lines.extend([
            'router bgp ' + str(router2['subAS']),
            ' bgp confederation identifier ' + str(router2['asNumber'])
        ])
        if router2['asNumber'] == router3['asNumber']:
            if router2['subAS'] != router3['subAS']:
                router2_config_lines.append(' bgp confederation peers ' + str(router3['subAS']))
                
            router2_config_lines.append(' neighbor 4.0.0.3 remote-as ' + str(router3['subAS']))
        else:
            router2_config_lines.append(' neighbor 4.0.0.3 remote-as ' + str(router3['asNumber']))     
    else:
        router2_config_lines.append(
            'router bgp ' + str(router2['asNumber'])
        )
        router2_config_lines.append(' neighbor 4.0.0.3 remote-as ' + str(router3['asNumber']))       
        
        
    router2_config_lines.append(
        ' neighbor 3.0.0.3 remote-as ' + str(originAS)
    )
    router2_config_lines.append(
        ' neighbor 4.0.0.3 route-map RM1 out'
    )
    
    if remove_private_as_flag:
        if replace_as_flag:
            router2_config_lines.append(
                ' neighbor 4.0.0.3 remove-private-as all replace-as'
            )
        else:
            router2_config_lines.append(
                ' neighbor 4.0.0.3 remove-private-as all'
            )


    ############################### ROUTER 3 CONFIGURATION ####################
    router3_config_lines.extend([
        'interface eth0/1',
        ' ip address 4.0.0.3 255.0.0.0',
        '',
    ])
    
    if router3['subAS'] != 0:
        router3_config_lines.extend([
            'router bgp ' + str(router3['subAS']),
            ' bgp confederation identifier ' + str(router3['asNumber'])
        ])
        if router2['asNumber'] == router3['asNumber']:
            if router2['subAS'] != router3['subAS']:
                router3_config_lines.append(' bgp confederation peers ' + str(router2['subAS']))
                
            router3_config_lines.append(' neighbor 4.0.0.2 remote-as ' + str(router2['subAS']))
        else:
            router3_config_lines.append(' neighbor 4.0.0.2 remote-as ' + str(router2['asNumber']))       
    else:
        router3_config_lines.append(
            'router bgp ' + str(router3['asNumber'])
        )
        router3_config_lines.append(' neighbor 4.0.0.2 remote-as ' + str(router2['asNumber']))       
        
    # print(router1_config_lines)
    # print(router2_config_lines)
    # print(router3_config_lines)

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
parsed_params = parse_test_case(test)
orig_as, r2_lp, r2_config, r3_config, remove_private_as_2, replace_as_2, is_ext_peer_3 = parsed_params
print("Parsed test case parameters")

# Update configurations (writes R1.cfg, R2.cfg, R3.cfg under snapshot/configs)
write_config(orig_as, r2_config, r3_config, remove_private_as_2, replace_as_2, r2_lp)
print("Updated Batfish configurations")

## Run Batfish test
new_df = run_batfish_example()
print(new_df)


## Save R1, R2, R3 configs for debug
with open(SNAPSHOT_DIR + "/configs/R1.cfg", "r") as f: r1_cfg = f.read(); open("R1.cfg", "w").write(r1_cfg)
with open(SNAPSHOT_DIR + "/configs/R2.cfg", "r") as f: r2_cfg = f.read(); open("R2.cfg", "w").write(r2_cfg)
with open(SNAPSHOT_DIR + "/configs/R3.cfg", "r") as f: r3_cfg = f.read(); open("R3.cfg", "w").write(r3_cfg)
print("Saved R1.cfg, R2.cfg, R3.cfg for debug")


# Save the result to a file

isRIB2, aspath2, isRIB3, aspath3 = get_results_from_newdf(new_df)

with open("result.json", "w") as f:
    json.dump({
        "isRIB2": isRIB2,
        "aspath2": aspath2,
        "isRIB3": isRIB3,
        "aspath3": aspath3
    }, f, indent=2)



