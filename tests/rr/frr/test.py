
import json
import os

debug = False

def parse_test_case(test):
    """
    [
        2, ## inRRflag : 0 : R2 is a client to R1 (RR), 1 : R2 is a route reflector to R1, 2 : R2 is a non-client to R1 (RR)
        1, ## outRRflag : 0 : R2 is a client to R3 (RR), 1 : R2 is a route reflector to R3, 2 : R2 is a non-client to R3 (RR)
        false, ## inAS : True : if AS of R2 is same as AS of R1, False : if AS of R2 is different from AS of R1
        true, ## outAS : True : if AS of R2 is same as AS of R3, False : if AS of R2 is different from AS of R3
        {
            "isReceived": false, ## if route is received at R2
            "isAdvertised": false ## if route is received at R3
        }
    ]
    """
    inRRflag = test[0]
    outRRflag = test[1]
    inAS = test[2]
    outAS = test[3]

    return inRRflag, outRRflag, inAS, outAS


def parse_rib(ribfile):
    with open(ribfile,"r") as f:
        lines = f.readlines()

    if lines[0].strip() == "% Network not in table":
        isRIB = False
    else:
        isRIB = True

    return isRIB

def update_router1_config(as1, as2, inRRflag):
    # rr_config = "neighbor 3.0.0.2 route-reflector-client" if inRRflag else ""

    if inRRflag == 0: ## R2 is a client to R1 (RR) --> R1 is a RR, R2 is a client
        rr_config = "neighbor 3.0.0.2 route-reflector-client"
    elif inRRflag == 1: ## R2 is a route reflector to R1 --> R1 is a client, R2 is a RR
        rr_config = ""
    elif inRRflag == 2: ## R2 is a non-client to R1 (RR)
        rr_config = ""

    new_config = f"""
router bgp {as1}
 no bgp ebgp-requires-policy
 no bgp network import-check
 bgp router-id 3.0.0.3
 neighbor 3.0.0.2 remote-as {as2}
 {rr_config}
 network 100.10.1.0/24"""

    with open("frr1/frr.conf", "w") as f:
        f.write(new_config)

def update_router2_config(as2, as1, as3, inRRflag, outRRflag):
    # rr_config = "neighbor 3.0.0.3 route-reflector-client" if rr_to_r1 else ""
    # client_config = "neighbor 3.0.0.3 route-server-client" if client_to_r1 else ""
    # rr_config3 = "neighbor 4.0.0.3 route-reflector-client" if rr_to_r3 else ""
    # client_config3 = "neighbor 4.0.0.3 route-server-client" if client_to_r3 else ""

    if inRRflag == 0: ## R2 is a client to R1 (RR) --> R1 is a RR, R2 is a client
        in_rr_config = ""
    elif inRRflag == 1: ## R2 is a route reflector to R1 --> R1 is a client, R2 is a RR
        in_rr_config = "neighbor 3.0.0.3 route-reflector-client"
    elif inRRflag == 2: ## R2 is a non-client to R1 (RR)
        in_rr_config = ""
    
    if outRRflag == 0: ## R2 is a client to R3 (RR) --> R3 is a RR, R2 is a client
        out_rr_config = ""
    elif outRRflag == 1: ## R2 is a route reflector to R3 --> R3 is a client, R2 is a RR
        out_rr_config = "neighbor 4.0.0.3 route-reflector-client"
    elif outRRflag == 2: ## R2 is a non-client to R3 (RR)
        out_rr_config = ""


    new_config = f"""
router bgp {as2}
 no bgp ebgp-requires-policy
 no bgp network import-check
 bgp router-id 3.0.0.2
 neighbor 3.0.0.3 remote-as {as1}
 {in_rr_config}
 neighbor 4.0.0.3 remote-as {as3}
 {out_rr_config}
    """

    with open("frr2/frr.conf", "w") as f:
        f.write(new_config)

def update_router3_config(as3, as2, outRRflag):
    # rr_config = "neighbor 4.0.0.2 route-reflector-client" if rr_to_r2 else ""
    # client_config = "neighbor 4.0.0.2 route-server-client" if client_to_r2 else ""

    if outRRflag == 0: ## R2 is a client to R3 (RR) --> R3 is a RR, R2 is a client
        rr_config = "neighbor 4.0.0.2 route-reflector-client"
    elif outRRflag == 1: ## R2 is a route reflector to R3 --> R3 is a client, R2 is a RR
        rr_config = ""
    elif outRRflag == 2: ## R2 is a non-client to R3 (RR)
        rr_config = ""

    new_config = f"""
router bgp {as3}
 no bgp ebgp-requires-policy
 no bgp network import-check
 bgp router-id 4.0.0.3
 neighbor 4.0.0.2 remote-as {as2}
 {rr_config}
    """

    with open("frr3/frr.conf", "w") as f:
        f.write(new_config)

################# MAIN #################
with open("../tests.json","r") as f:
    tests = json.load(f)

if debug:
    with open("debug_test.json","r") as f:
        tests = json.load(f)

g = open("results.txt","w")
g.close()
n_tests = len(tests)
for i,test in enumerate(tests):
    print(f"@@@ Running Test {i+1}/{n_tests}...\n")

    inRRflag, outRRflag, inAS, outAS = parse_test_case(test)
    as2 = 200 ## hardcoded
    as1 = 200 if inAS else 100
    as3 = 200 if outAS else 300

    update_router1_config(as1, as2, inRRflag)

    update_router2_config(as2, as1, as3, inRRflag, outRRflag)

    update_router3_config(as3, as2, outRRflag)

    os.system("bash test.sh")

    isRIB2 = parse_rib("router2_RIB.txt")
    isRIB3 = parse_rib("router3_RIB.txt")

    with open("results.txt","a") as f:
        f.write(f"{isRIB2},{isRIB3}\n")
