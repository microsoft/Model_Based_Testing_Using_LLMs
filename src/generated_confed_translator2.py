
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

def update_router2_config(config_r2, remove_private_as_r2, replace_as_r2, local_pref_r2):
    new_config = f"""
router bgp {config_r2['asNumber']}
 bgp confederation identifier {config_r2['subAS']}
 neighbor 3.0.0.3 remote-as {config_r2['asNumber']}
 neighbor 3.0.0.3 remove-private-AS {str(remove_private_as_r2).lower()}
 neighbor 3.0.0.3 replace-as {str(replace_as_r2).lower()}
 neighbor 3.0.0.3 route-map SET_LOCAL_PREF out
!
route-map SET_LOCAL_PREF permit 10
 set local-preference {local_pref_r2}
    """

    with open("router2.conf", "w") as f:
        f.write(new_config)

def update_router3_config(config_r3, is_external_peer_r3):
    new_config = f"""
router bgp {config_r3['asNumber']}
 bgp confederation identifier {config_r3['subAS']}
 neighbor 4.0.0.2 remote-as {config_r3['asNumber']} { 'external' if is_external_peer_r3 else ''}
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

    update_exabgp_config(as_r1, config_r2['asNumber'])

    update_router2_config(config_r2, remove_private_as_r2, replace_as_r2, local_pref_r2)

    update_router3_config(config_r3, is_external_peer_r3)

    os.system("bash test.sh")

    isRIB2 = parse_rib("router2_RIB.txt")
    isRIB3 = parse_rib("router3_RIB.txt")

    with open("results.txt","a") as f:
        f.write(f"{isRIB2},{isRIB3}\n")
