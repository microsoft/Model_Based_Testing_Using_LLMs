

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

import ipaddress

def int_to_prefix(value: int, prefix_len: int) -> str:
    """
    Convert an integer IPv4 address and prefix length to CIDR notation.

    Example:
        int_to_prefix(1671446532, 24) -> '99.151.128.0/24'
    """
    ip = ipaddress.IPv4Address(value)
    network = ipaddress.IPv4Network(f"{ip}/{prefix_len}", strict=False)
    return str(network)

def int_to_community(value: int) -> str:
    """
    Convert an integer BGP community to 'X:Y' format.

    Example:
        655379 -> '10:10'
    """
    high = (value >> 16) & 0xFFFF
    low = value & 0xFFFF
    return f"{high}:{low}"



def parse_rib(ribfile):
    with open(ribfile,"r") as f:
        lines = f.readlines()

    print("@@@ FRR RIB File Contents:")
    for line in lines:
        print(line.strip())

    if lines[0].strip() == "% Network not in table":
        isRIB = False

    else:
        isRIB = True
        aspath = lines[-4].strip()
        lp_line = lines[-2].strip()
        if "localpref" in lp_line:
            lp = lp_line.split("localpref ")[1].split(",")[0]
        else:
            lp = ""

    return isRIB

def update_exabgp_config(route):

    localPref = route["local_pref"]
    med = route["med"]
    route_prefix = route["prefix"]

    new_config = f"""
process announce-routes {{  
    run python exabgp/example.py;
    encoder json;
}}

neighbor 6.0.0.2 {{                 # Remote neighbor to peer with
    router-id 6.0.0.3;              # Our local router-id
    local-address 6.0.0.3;          # Our local update-source
    local-as 40;                    # Our local AS
    peer-as 40;                     # Peer's AS

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
    
def update_frr_config(rmap):
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

router bgp 40 
  no bgp ebgp-requires-policy 
  no bgp network import-check
  neighbor 6.0.0.3 remote-as 40
  neighbor 6.0.0.3 route-map RMap in
  neighbor 6.0.0.3 soft-reconfiguration inbound
  network 6.0.0.0
exit
!
"""

    with open("frr2/frr.conf", "w") as f:
        f.write(new_config)
