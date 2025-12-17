
import json
import os

def parse_test_case(test):
    return tuple(test[:11])

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

def update_router2_config(as2, as1, rr_to_r1, client_to_r1, as3, rr_to_r3, client_to_r3):
    rr_config = "neighbor 3.0.0.3 route-reflector-client" if rr_to_r1 else ""
    client_config = "neighbor 3.0.0.3 route-server-client" if client_to_r1 else ""
    rr_config3 = "neighbor 4.0.0.3 route-reflector-client" if rr_to_r3 else ""
    client_config3 = "neighbor 4.0.0.3 route-server-client" if client_to_r3 else ""

    new_config = f"""
router bgp {as2}
 bgp router-id 3.0.0.2
 neighbor 3.0.0.3 remote-as {as1}
 {rr_config}
 {client_config}
 neighbor 4.0.0.3 remote-as {as3}
 {rr_config3}
 {client_config3}
    """

    with open("router2.conf", "w") as f:
        f.write(new_config)

def update_router3_config(as3, as2, rr_to_r2, client_to_r2):
    rr_config = "neighbor 4.0.0.2 route-reflector-client" if rr_to_r2 else ""
    client_config = "neighbor 4.0.0.2 route-server-client" if client_to_r2 else ""

    new_config = f"""
router bgp {as3}
 bgp router-id 4.0.0.3
 neighbor 4.0.0.2 remote-as {as2}
 {rr_config}
 {client_config}
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

    as1, as2, as3, rr_to_r2, client_to_r2, rr_to_r1, client_to_r1, rr_to_r3, client_to_r3, rr_to_r2_3, client_to_r2_3 = parse_test_case(test)

    update_exabgp_config(as1, as2)

    update_router2_config(as2, as1, rr_to_r1, client_to_r1, as3, rr_to_r3, client_to_r3)

    update_router3_config(as3, as2, rr_to_r2_3, client_to_r2_3)

    os.system("bash test.sh")

    isRIB2 = parse_rib("router2_RIB.txt")
    isRIB3 = parse_rib("router3_RIB.txt")

    with open("results.txt","a") as f:
        f.write(f"{isRIB2},{isRIB3}\n")
