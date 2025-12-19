
import json
import os

def parse_test_case(test):
    router1 = test[0]
    router2 = test[1]
    router3 = test[2]
    return router1, router2, router3

def parse_rib(ribfile):
    with open(ribfile,"r") as f:
        lines = f.readlines()

    if lines[0].strip() == "% Network not in table":
        isRIB = False
    else:
        isRIB = True

    return isRIB

def update_exabgp_config(local_as, peer_as):
    new_config = f"""
process announce-routes {{  
    run python exabgp/example.py;
    encoder json;
}}

neighbor 3.0.0.2 {{                 
    router-id 3.0.0.3;              
    local-address 3.0.0.3;          
    local-as {local_as};                    
    peer-as {peer_as};                     

    api {{
        processes [announce-routes];
    }}
}}
    """

    with open("exabgp1/conf.ini", "w") as f:
        f.write(new_config)

def update_router2_config(router2, router1_as):
    new_config = f"""
router bgp {router2['asNumber']}
 bgp router-id 3.0.0.2
 neighbor 3.0.0.3 remote-as {router1_as}
 neighbor 4.0.0.3 remote-as {router2['asNumber']}
    """
    if router2['isRR']:
        new_config += " neighbor 3.0.0.3 route-reflector-client\n"
    with open("router2.conf", "w") as f:
        f.write(new_config)

def update_router3_config(router3, router2_as):
    new_config = f"""
router bgp {router3['asNumber']}
 bgp router-id 4.0.0.3
 neighbor 4.0.0.2 remote-as {router2_as}
    """
    if router3['isRR']:
        new_config += " neighbor 4.0.0.2 route-reflector-client\n"
    with open("router3.conf", "w") as f:
        f.write(new_config)

with open("../tests.json","r") as f:
    tests = json.load(f)

g = open("results.txt","w")
g.close()
n_tests = len(tests)
for i,test in enumerate(tests):
    print(f"@@@ Running Test {i+1}/{n_tests}...\n")

    router1, router2, router3 = parse_test_case(test)

    update_exabgp_config(router1['asNumber'], router2['asNumber'])

    update_router2_config(router2, router1['asNumber'])

    update_router3_config(router3, router2['asNumber'])

    os.system("bash test.sh")

    isRIB2 = parse_rib("router2_RIB.txt")
    isRIB3 = parse_rib("router3_RIB.txt")

    with open("results.txt","a") as f:
        f.write(f"{isRIB2},{isRIB3}\n")
