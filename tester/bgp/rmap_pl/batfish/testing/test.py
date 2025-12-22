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
SNAPSHOT_DIR = '../networks/route-analysis'


def run_batfish_example(route):
    bf = Session(host="localhost")
    NETWORK_NAME = "example_network"
    SNAPSHOT_NAME = "example_snapshot"
    bf.set_network(NETWORK_NAME)
    bf.init_snapshot(SNAPSHOT_DIR, name=SNAPSHOT_NAME, overwrite=True)
    print("Initialized Batfish session with network and snapshot")

    inRoute1 = BgpRoute(network=route["prefix"], 
                        originatorIp="4.4.4.4", 
                        originType="egp", 
                        protocol="bgp",
                        localPreference=int(route["local_pref"]),
                        metric=int(route["med"]),
                        nextHopIp="3.0.0.3")
    print(f"Input route: network={inRoute1.network}, AsPath={inRoute1.asPath}, Communities={inRoute1.communities}, LocalPreference={inRoute1.localPreference}, Metric={inRoute1.metric}, NextHopIp={inRoute1.nextHopIp}")

    # Test how our policy treats this route
    result = bf.q.testRoutePolicies(policies="Rmap", 
                                    direction="in", 
                                    inputRoutes=[inRoute1]).answer().frame()
    print("\nExecuted route policy test...")

    # Display the result
    result.to_json("output.json", orient="records", indent=2)
    with open(SNAPSHOT_DIR + "/configs/R2.cfg", "r") as f:
        config = f.read()
    with open("R2.cfg", "w") as f:
        f.write(config)
    print("Saved test result to output.json and R2.cfg for debug")

    # Save the result to a file  
    # print(f"result['Action'] = {result['Action']}")
    router_decision = result["Action"][0].lower()
    print(f"Router decision based on route-map: {router_decision}")
    isRIB2 = True if router_decision == "permit" else False

    with open("result.json", "w") as f:
        json.dump({
            "isRIB2": isRIB2
        }, f, indent=2)


def write_config(rmap):
    router2_config_lines = []
    router2_config_lines.extend([
        '!',
        'hostname R2',
        ''
    ])
    if rmap["prefix_list"] != []:
        for prefix in rmap["prefix_list"]:
            router2_config_lines.extend([
                f'ip prefix-list PFXL {prefix["action"]} {prefix["match"]}',
                ''
            ])
    router2_config_lines.extend([
        'route-map RMap ' + rmap["rmap_action"] + ' 10',
        ''
    ])
    if rmap["prefix_list"] != []:
        router2_config_lines.extend([
            ' match ip address prefix-list PFXL',
            ''
        ])
    router2_config_lines.extend([
        'end\n'
    ]) 
    
    if not os.path.exists(SNAPSHOT_DIR):
        os.mkdir(SNAPSHOT_DIR)
        os.mkdir(SNAPSHOT_DIR + '/configs')
            
    with open(SNAPSHOT_DIR + '/configs/R2.cfg', 'w') as f:
        f.write('\n'.join(router2_config_lines))
    print("\n @@@ Wrote Batfish router2 configuration @@@\n")
    print('\n'.join(router2_config_lines))
        


### Execute Test Case ###

# load the test
with open("test.json", "r") as f:
    test = json.load(f)
print("Loaded test case")

# Parse the test case
rmap = test["rmap"]
route = test["route"]
print("Parsed test case parameters")

# Update configurations 
write_config(rmap)
print("Updated Batfish configurations")

## Run Batfish test
run_batfish_example(route)
print("Batfish test executed")






