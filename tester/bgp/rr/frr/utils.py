

def print_colored(text, color):
    colors = {
        "black": "\033[30m",
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "reset": "\033[0m"
    }

    color_code = colors.get(color.lower(), colors["reset"])
    print(f"{color_code}{text}{colors['reset']}")


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
    inRRflag = test["inRRflag"]
    outRRflag = test["outRRflag"]
    inAS = test["inAS"]
    outAS = test["outAS"]

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
 network 100.0.0.0/8"""

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
