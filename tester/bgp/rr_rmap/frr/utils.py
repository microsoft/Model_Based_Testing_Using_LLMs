

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
    route = test["route"]
    rmap = test["rmap"]
    inRRflag = test["inRRflag"]
    outRRflag = test["outRRflag"]
    inAS = test["inAS"]
    outAS = test["outAS"]

    return route, rmap, inRRflag, outRRflag, inAS, outAS


def parse_rib(ribfile):
    with open(ribfile,"r") as f:
        lines = f.readlines()

    if lines[0].strip() == "% Network not in table":
        isRIB = False
    else:
        isRIB = True
    return isRIB

def update_exabgp_config(route, ase, as1):

    localPref = route["local_pref"]
    med = route["med"]
    route_prefix = route["prefix"]

    new_config = f"""
process announce-routes {{  
    run python exabgp/example.py;
    encoder json;
}}

neighbor 2.0.0.3 {{                 # Remote neighbor to peer with
    router-id 2.0.0.2;              # Our local router-id
    local-address 2.0.0.2;          # Our local update-source
    local-as {ase};                    # Our local AS
    peer-as {as1};                     # Peer's AS

    api {{
        processes [announce-routes];
    }}
}}
    """

    with open("exabgp1/conf.ini", "w") as f:
        f.write(new_config)

    example_py_lines = f"""
#!/usr/bin/env python3

from __future__ import print_function

from sys import stdout
from time import sleep

messages = [
    "announce route {route_prefix} next-hop self local-preference {localPref} med {med}",
]

sleep(5)

#Iterate through messages
for message in messages:
    stdout.write(message + '\\n')
    stdout.flush()
    sleep(1)

#Loop endlessly to allow ExaBGP to continue running
while True:
    sleep(1)
"""
    with open("exabgp1/example.py", "w") as f:
        f.write(example_py_lines)     


def update_router1_config(ase, as1, as2, inRRflag):
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
 neighbor 2.0.0.2 remote-as {ase}
 {rr_config}
 network 2.0.0.0
 network 3.0.0.0
 exit
!
"""

    with open("frr1/frr.conf", "w") as f:
        f.write(new_config)

def update_router2_config(as2, as1, as3, rmap, inRRflag, outRRflag):

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

    pfxl_def = ""

    if "prefix_list" in rmap and rmap["prefix_list"] != []:
        prefix_list = rmap["prefix_list"]
        for prefix in prefix_list:
            pfxl_def += f"ip prefix-list PFXL {prefix['action']} {prefix['match']}\n"

    lp_match = f"  match local-preference {rmap['local_pref']}" if "local_pref" in rmap else ""
    med_match = f"  match metric {rmap['med']}" if "med" in rmap else ""
    prefix_match = f"  match ip address prefix-list PFXL" if (("prefix_list" in rmap) and (rmap["prefix_list"] != [])) else ""


    new_config = f"""
debug bgp updates
log file /var/log/frr/bgpd.log

{pfxl_def}
route-map RMap {rmap["rmap_action"]} 10
{prefix_match}
{lp_match}
{med_match}

router bgp {as2} 
  no bgp ebgp-requires-policy 
  no bgp network import-check
  neighbor 3.0.0.3 remote-as {as1}
  {in_rr_config}
  neighbor 4.0.0.3 remote-as {as3}
  {out_rr_config}
  neighbor 4.0.0.3 route-map RMap out
  neighbor 3.0.0.3 soft-reconfiguration inbound
  neighbor 4.0.0.3 soft-reconfiguration outbound
  network 3.0.0.0
  network 4.0.0.0
exit
!
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
 network 4.0.0.0
 exit
!
    """

    with open("frr3/frr.conf", "w") as f:
        f.write(new_config)
