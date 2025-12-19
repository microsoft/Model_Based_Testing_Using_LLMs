
import json
import os

def parse_test_case(test):
    as_r1 = test[0]
    config_r2 = test[1]
    config_r3 = test[2]
    remove_private_as_r2 = test[3]
    replace_as_r2 = test[4]
    local_pref_r2 = test[5]
    is_external_peer_r3 = test[6]
    return as_r1, config_r2, config_r3, remove_private_as_r2, replace_as_r2, local_pref_r2, is_external_peer_r3

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

def update_router2_config(as_r2, sub_as_r2, remove_private_as, replace_as, local_pref):
    new_config = f"""
router bgp {as_r2}
 bgp confederation identifier {sub_as_r2}
 bgp confederation peers {as_r2}
 neighbor 3.0.0.3 remote-as {as_r2}
 neighbor 3.0.0.3 remove-private-AS {remove_private_as}
 neighbor 3.0.0.3 replace-as {replace_as}
 neighbor 3.0.0.3 route-map SET_LOCAL_PREF out
!
route-map SET_LOCAL_PREF permit 10
 set local-preference {local_pref}
    """

    with open("router2.conf", "w") as f:
        f.write(new_config)

def update_router3_config(as_r3, sub_as_r3, is_external_peer):
    new_config = f"""
router bgp {as_r3}
 bgp confederation identifier {sub_as_r3}
 bgp confederation peers {as_r3}
 neighbor 4.0.0.2 remote-as {as_r3}
 neighbor 4.0.0.2 ebgp-multihop {is_external_peer}
    """

    with open("router3.conf", "w") as f:
        f.write(new_config)

with open("../tests.json","r") as f:
    tests = json.load(f)

g = open("results.txt","w")
g.close()
n_tests = len(tests)
for i,test in enumerate(tests):
    print(f"@@@ Running Test {i+1}/{n_tests}...\n")

    as_r1, config_r2, config_r3, remove_private_as_r2, replace_as_r2, local_pref_r2, is_external_peer_r3 = parse_test_case(test)

    update_exabgp_config(as_r1, config_r2["asNumber"])

    update_router2_config(config_r2["asNumber"], config_r2["subAS"], remove_private_as_r2, replace_as_r2, local_pref_r2)

    update_router3_config(config_r3["asNumber"], config_r3["subAS"], is_external_peer_r3)

    os.system("bash test.sh")

    isRIB2 = parse_rib("router2_RIB.txt")
    isRIB3 = parse_rib("router3_RIB.txt")

    with open("results.txt","a") as f:
        f.write(f"{isRIB2},{isRIB3}\n")
