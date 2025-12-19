import json
import os

debug = False

# """
# Topology:

# Originating Router ----------------- R2 ----------------- R3

# """

def parse_test_case(test):
    orig_as = test[0]
    r2_lp = test[5]
    r2_config = test[1]
    r3_config = test[2]
    remove_private_as_2 = test[3]
    replace_as_2 = test[4]
    is_ext_peer_3 = test[6]

    return orig_as, r2_lp, r2_config, r3_config, remove_private_as_2, replace_as_2, is_ext_peer_3

def parse_rib(ribfile):
    with open(ribfile,"r") as f:
        lines = f.readlines()

    if lines[0].strip() == "% Network not in table":
        isRIB = False
        aspath = ""
        lp = ""
    else:
        isRIB = True
        aspath = lines[-4].strip()
        lp_line = lines[-2].strip()
        if "localpref" in lp_line:
            lp = lp_line.split("localpref ")[1].split(",")[0]
        else:
            lp = ""

    return isRIB, aspath, lp


def update_exabgp_config(local_as, peer_as):

    new_config = f"""
process announce-routes {{  
    run python exabgp/example.py;
    encoder json;
}}

neighbor 3.0.0.2 {{                 # Remote neighbor to peer with
    router-id 3.0.0.3;              # Our local router-id
    local-address 3.0.0.3;          # Our local update-source
    local-as {local_as};                    # Our local AS
    peer-as {peer_as};                     # Peer's AS

    api {{
        processes [announce-routes];
    }}
}}
    """

    with open("exabgp1/conf.ini", "w") as f:
        f.write(new_config)


def update_frr2_config(r2_config, orig_as, r3_config, remove_private_as_2, replace_as_2, r2_lp):
    remove_private_as_word = "remove-private-as all" if remove_private_as_2 else ""
    replace_as_word = "replace-as" if replace_as_2 else ""
    peer_as = 0
    confed_peer_line = ""
    if (r2_config["subAS"] != 0) and (r3_config["subAS"] != 0) and r2_config["asNumber"] == r3_config["asNumber"]:
        peer_as = r3_config["subAS"]
        confed_peer_line = f"\n  bgp confederation peers {peer_as}"
    else:
        peer_as = r3_config["asNumber"]
    

    is_confed = r2_config["subAS"] != 0
    confed_line = f"\n  bgp confederation identifier {r2_config['asNumber']}" if is_confed else ""
    router_id = f"{r2_config['subAS']}" if is_confed else f"{r2_config['asNumber']}" 
    new_config = f"""
router bgp {router_id}  
  no bgp ebgp-requires-policy{confed_line}{confed_peer_line}
  neighbor 3.0.0.3 remote-as {orig_as}
  neighbor 4.0.0.3 remote-as {peer_as} {remove_private_as_word} {replace_as_word}
  neighbor 4.0.0.3 route-map SET_LOCAL_PREF out
exit
!

route-map SET_LOCAL_PREF permit 10
    set local-preference {r2_lp}
exit
!
    """

    with open("frr2/frr.conf", "w") as f:
        f.write(new_config)

def update_frr3_config(r3_config, r2_config, is_ext_peer_3):
    is_confed = r3_config["subAS"] != 0
    confed_line = f"\n  bgp confederation identifier {r3_config['asNumber']}" if is_confed else ""
    router_id = f"{r3_config['subAS']}" if is_confed else f"{r3_config['asNumber']}" 
    peer_as = 0
    confed_peer_line = ""
    if (r2_config["subAS"] != 0) and (r3_config["subAS"] != 0) and r2_config["asNumber"] == r3_config["asNumber"]:
        peer_as = r2_config["subAS"]
        confed_peer_line = f"\n  bgp confederation peers {peer_as}"
    else:
        peer_as = r2_config["asNumber"]

    if is_ext_peer_3:
        peer_as = "external"

    new_config = f"""
router bgp {router_id}
  no bgp ebgp-requires-policy{confed_line}{confed_peer_line}
  neighbor 4.0.0.2 remote-as {peer_as}
exit
!
    """

    with open("frr3/frr.conf", "w") as f:
        f.write(new_config)


################ Main ################
with open("../tests.json","r") as f:
    tests = json.load(f)

if debug:
    with open("debug_test.json","r") as f:
        tests = json.load(f)

## Origin AS, origin LP, router 2, router 3, remove-private-as 2, replace-as 2, isExtpeer 3, 

g = open("results.txt","w")
g.close()
n_tests = len(tests)
for i,test in enumerate(tests):
    print(f"@@@ Running Test {i+1}/{n_tests}...\n")

    ## Parse test case
    
    parsed_params = parse_test_case(test)
    orig_as, r2_lp, r2_config, r3_config, remove_private_as_2, replace_as_2, is_ext_peer_3 = parsed_params

    update_exabgp_config(orig_as, r2_config["asNumber"])
    update_frr2_config(r2_config, orig_as, r3_config, remove_private_as_2, replace_as_2, r2_lp)
    update_frr3_config(r3_config, r2_config, is_ext_peer_3)

    os.system("bash test.sh")

    ### Parse RIBs ###

    isRIB2, aspath2, lp2 = parse_rib("router2_RIB.txt")
    isRIB3, aspath3, lp3 = parse_rib("router3_RIB.txt")

    with open("results.txt","a") as f:
        f.write(f"{isRIB2},{isRIB3},{aspath2},{aspath3},{lp2},{lp3}\n")






