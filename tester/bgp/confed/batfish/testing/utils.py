import os
import pandas as pd


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


def get_results_from_newdf(newdf):
    # defaults
    isRIB2 = False
    aspath2 = ""
    isRIB3 = False
    aspath3 = ""

    if newdf is None or newdf.empty:
        return isRIB2, aspath2, isRIB3, aspath3

    # iterate rows
    for _, row in newdf.iterrows():
        node = str(row.get("Node", "")).strip().lower()
        aspath = str(row.get("AS_Path", "")).strip()
        if node == "r2":
            isRIB2 = True
            aspath2 = aspath
        elif node == "r3":
            isRIB3 = True
            aspath3 = aspath

    return isRIB2, aspath2, isRIB3, aspath3
