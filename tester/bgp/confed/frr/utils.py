

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
    Accepts a test dict with keys:
      "originAS", "router2", "router3", "removePrivateAS", "replaceAS", "localPref", "isExternalPeer"
    Returns a tuple in the exact order expected by test.py:
      (orig_as, r2_lp, r2_config, r3_config, remove_private_as_2, replace_as_2, is_ext_peer_3)
    (This preserves the original function signature / unpacking in test.py.)
    """
    orig_as = test.get("originAS")
    r2_config = test.get("router2", {"asNumber": 0, "subAS": 0})
    r3_config = test.get("router3", {"asNumber": 0, "subAS": 0})
    remove_private_as_2 = bool(test.get("removePrivateAS", False))
    replace_as_2 = bool(test.get("replaceAS", False))
    r2_lp = test.get("localPref", None)
    is_ext_peer_3 = bool(test.get("isExternalPeer", True))
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

neighbor 6.0.0.2 {{                 # Remote neighbor to peer with
    router-id 6.0.0.3;              # Our local router-id
    local-address 6.0.0.3;          # Our local update-source
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
  neighbor 6.0.0.3 remote-as {orig_as}
  neighbor 8.0.0.3 remote-as {peer_as} {remove_private_as_word} {replace_as_word}
  neighbor 8.0.0.3 route-map SET_LOCAL_PREF out
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
  neighbor 8.0.0.2 remote-as {peer_as}
exit
!
    """

    with open("frr3/frr.conf", "w") as f:
        f.write(new_config)



