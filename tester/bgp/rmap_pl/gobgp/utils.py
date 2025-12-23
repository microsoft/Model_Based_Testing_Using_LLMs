
import yaml
import json
from argparse import ArgumentParser
import os

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

def update_exabgp_config(route):

    localPref = route["local_pref"]
    med = route["med"]
    route_prefix = route["prefix"]

    new_config = f"""
process announce-routes {{  
    run python exabgp/example.py;
    encoder json;
}}

neighbor 3.0.0.2 {{                 # Remote neighbor to peer with
    router-id 3.0.0.3;              # Our local router-id
    local-address 3.0.0.3;          # Our local update-source
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
   
def parse_ple(ple):
    ple_match = ple["match"]
    ple_match_split = ple_match.split(" ")
    ple_prefix = ple_match_split[0].split("/")[0]
    ple_mask = int(ple_match_split[0].split("/")[1]) if "/" in ple_match_split[0] else ""
    ple_le = 32
    if "le" in ple_match:
        ple_le = int(ple_match_split[ple_match_split.index("le")+1])
    ple_ge = int(ple_match_split[ple_match_split.index("ge")+1]) if "ge" in ple_match else ple_mask
    ple_permit = True if ple["action"] == "permit" else False
    return ple_prefix, ple_mask, ple_le, ple_ge, ple_permit



def update_gobgp_config(data):

    pl_flag = False
    com_flag = False
    as_flag = False

    route_map = [
        {
            "match": {},
            "set": {},
            "permit": True if data["rmap_action"] == "permit" else False
        }
    ]

    prefix_list = []
    pl_valid = True
    if "prefix_list" in data and len(data["prefix_list"]) > 0:
        for i in range(len(data["prefix_list"])):
            ple_prefix, ple_mask, ple_le, ple_ge, ple_permit = parse_ple(data["prefix_list"][i])
            p0 = {
                "prefix": ple_prefix,
                "mask": ple_mask,
                "le": ple_le,
                "ge": ple_ge,
                "permit": ple_permit
            }
            if p0["mask"] == "":
                pl_valid = False
            prefix_list.append(p0)
        pl_flag = True
        # print(prefix_list)
        if pl_valid:
            try:
                prefix_list = convert_prefix_list_to_prefix_set(prefix_list)
            except Exception as e:
                print(f"Error converting prefix list: {e}")
        route_map[0]["match"]["Prefix List"] = "ps1"

        # print("Prefix Set: ", prefix_list)

    community_list = []
    if "community_list" in data and len(data["community_list"]) > 0:
        for i in range(len(data["community_list"])):
            c = {
                "RegularExpression": data["community_list"][i]["match"],
                "permit": True if data["community_list"][i]["action"] == "permit" else False
            }
            community_list.append(c)
        com_flag = True
        route_map[0]["match"]["Community List"] = "c1"

    aspath_list = []
    if "as_path_list" in data and len(data["as_path_list"]) > 0:
        for i in range(len(data["as_path_list"])):
            c = {
                "RegularExpression": data["as_path_list"][i]["match"],
                "permit": True if data["as_path_list"][i]["action"] == "permit" else False
            }
            aspath_list.append(c)
        as_flag = True
        route_map[0]["match"]["As Path List"] = "a1"

    print("Route map: ", route_map)

    ############# GLOBAL CONFIGURATION ###########
    d = dict()
    d["global"] = dict()
    d["global"]["config"] = {"as": 40, "router-id": "192.2.3.4"}
    d["global"]["apply-policy"] = {
        "config": {
            "import-policy-list": ["example-policy"],
            "default-import-policy": "reject-route"
        }
    }



    ############ NEIGHBOR CONFIGURATION ###########
    d["neighbors"] = [dict()]
    d["neighbors"][0]["config"] = {
        "neighbor-address": "3.0.0.3",
        "peer-as": 40,
    }
    d["neighbors"][0]["transport"] = {
        "config" : 
            {
                "local-address": "3.0.0.2"
            }
    }
    with open("gobgp2/gobgp.yml", "w") as f:
        yaml.dump(d, f)

    ######### PREFIX-LIST CONFIGURATION #######

    prefix_list_toml = []
    for p in prefix_list:
        d = dict()
        d["ip-prefix"] = p["prefix"] + "/" + str(p["mask"])
        le = str(p["le"]) if p["le"] is not None else "32"
        ge = str(p["ge"]) if p["ge"] is not None else str(p["mask"])
        d["masklength-range"] = ge + ".." + le
        prefix_list_toml.append(d)

    d = dict()
    d["defined-sets"] = dict()

    if pl_flag:
        d["defined-sets"]["prefix-sets"] = {
                    "prefix-set-name" : "ps1",
                    "prefix-list": prefix_list_toml
                }


    ######## COMMUNITY LIST CONFIGURARTION ###########

    community_list_toml = [c["RegularExpression"] for c in community_list]

    if as_flag or com_flag:
        d["defined-sets"]["bgp-defined-sets"] = dict()

    if com_flag:
        d["defined-sets"]["bgp-defined-sets"]["community-sets"]= {
                            "community-set-name": "c1",
                            "community-list": community_list_toml
                        }

    ####### AS PATH LIST CONFIGURATION ################
    aspath_list_toml = [a["RegularExpression"] for a in aspath_list]

    if as_flag:
        d["defined-sets"]["bgp-defined-sets"]["as-path-sets"] = {
                            "as-path-set-name": "a1",
                            "as-path-list": aspath_list_toml
                        }

    ####### ROUTE MAP CONFIGURATION ###################
    d["policy-definitions"] = [dict()]
    d["policy-definitions"][0]["name"] = "example-policy"

    d["policy-definitions"][0]["statements"]= [dict() for i in range(len(route_map))]

    for i in range(len(route_map)):
        d["policy-definitions"][0]["statements"][i]["name"] = "statement" + str(i+1)
        d["policy-definitions"][0]["statements"][i]["conditions"] = dict()
        for m in route_map[i]["match"].keys():
            if m == "As Path List":
                if "bgp-conditions" not in d["policy-definitions"][0]["statements"][i]["conditions"]:
                    d["policy-definitions"][0]["statements"][i]["conditions"]["bgp-conditions"] = {"match-as-path-set" : {"as-path-set" : route_map[i]["match"][m], "match-set-options": ("any" if aspath_list[0]["permit"] is True else "invert")}}
                else:
                    d["policy-definitions"][0]["statements"][i]["conditions"]["bgp-conditions"]["match-as-path-set"] = {"as-path-set" : route_map[i]["match"][m], "match-set-options": ("any" if aspath_list[0]["permit"] is True else "invert")}
            elif m == "Community List":
                if "bgp-conditions" in d["policy-definitions"][0]["statements"][i]["conditions"]:
                    d["policy-definitions"][0]["statements"][i]["conditions"]["bgp-conditions"]["match-community-set"] = {"community-set" : route_map[i]["match"][m], "match-set-options": ("any" if community_list[0]["permit"] is True else "invert")}
                else:
                    d["policy-definitions"][0]["statements"][i]["conditions"]["bgp-conditions"] = {"match-community-set" : {"community-set": route_map[i]["match"][m], "match-set-options": ("any" if community_list[0]["permit"] is True else "invert")}}
            elif m == "Prefix List":
                d["policy-definitions"][0]["statements"][i]["conditions"]["match-prefix-set"] = {"prefix-set": route_map[i]["match"][m]}

        print(route_map[i]["permit"])
        d["policy-definitions"][0]["statements"][i]["actions"] = {"route-disposition": "accept-route" if route_map[i]["permit"] else "reject-route"}

    print(d)
    print(d["policy-definitions"][0]["statements"][0]["actions"])

    with open("gobgp2/gobgp.yml", "a") as f:
        yaml.dump(d, f)


def parse_rib(ribfile):
    with open(ribfile,"r") as f:
        lines = f.readlines()
    if (len(lines) == 1) and lines[0].startswith("Network not in table"):
        return False
    elif len(lines) == 1 and lines[0].startswith("Error: gobgp.yml file not generated") or len(lines) == 0:
        return False
    else:
        return True


def convert_prefix_to_uint(prefix):
    prefix = prefix.split(".")
    p1 = int(prefix[0])
    p2 = int(prefix[1])
    p3 = int(prefix[2])
    p4 = int(prefix[3])

    return  p1 * (1 << 24) + p2 * (1 << 16) + p3 * (1 << 8) + p4


def convert_uint_to_prefix(num):
    p1 = num // (1 << 24)
    num %= (1 << 24)
    p2 = num // (1 << 16)
    num %= (1 << 16)
    p3 = num // (1 << 8)
    num %= (1 << 8)
    p4 = num

    return str(p1) + "." + str(p2) + "." + str(p3) + "." + str(p4)

def get_mask(mask):
    num = 0
    k = 31
    for i in range(mask):
        num |= (1 << k)
        k -= 1

    return num

def inv(i):
    if i == "1":
        return "0"
    else:
        return "1"
    
def dec_to_binary(num, digits):
    s = ""
    for _ in range(digits):
        s = s + str(num & 1)
        num >>= 1
    return s[::-1]
    

def convert_prefix_to_binary(prefix_list):
    binary_set = []
    for p in prefix_list:
        prefix = convert_prefix_to_uint(p["prefix"])
        mask = get_mask(p["mask"])
        prefix = prefix & mask
        binary_set.append(
            (('' if p['mask'] == 0 else dec_to_binary(prefix >> (32 - p["mask"]), p["mask"]),
            p["ge"],
            p["le"]),
            p["permit"])
        )

    # print(binary_set)

    return binary_set


def convert_binary_to_prefix(binary_set):
    prefix_set = []
    # print(binary_set)
    for b in binary_set:
        mask = len(b[0])
        ge = b[1]
        le = b[2]
        prefix = convert_uint_to_prefix(0 if b[0] is '' else (int(b[0], 2) << (32 -mask)))
        prefix_set.append(
            {
                "prefix": prefix,
                "mask": mask,
                "le": max(le,mask),
                "ge": max(ge,mask)
            }
        )

    return prefix_set

def LeGeOverlapHandler(pre, ge1, le1, ge2, le2):
    _s = []
    
    if ge2 <= ge1 and le2 >= le1:
        pass
    elif ge2 > ge1 and le2 < le1:
        _s.append((pre, ge1, ge2-1))
        _s.append((pre, le2+1, le1))
    elif ge2 <= ge1 and le2 < le1:
        _s.append((pre, le2+1, le1))
    elif ge2 > ge1 and le2 >= le1:
        _s.append((pre, ge1, ge2-1))
    return _s

def subs(a,b):
    r = []
    if len(a) < len(b):
        if b.startswith(a):
            x = b[len(a):]
            for i in range(len(x)):
                _x = x
                _x = _x[:i] + inv(_x[i]) + _x[i+1:]
                r.append(a + _x[:i+1])
        else:
            r.append(a)
    else:
        if not a.startswith(b):
            r.append(a)
    return r

def subs_prefix(p,s):
    r = []
    for q in p:
        a = q[0]
        b = s[0]
        ge1 = q[1]
        le1 = q[2]
        ge2 = s[1]
        le2 = s[2]

        if ge2 <= ge1 and le2 >= le1:
            if subs(a,b) != []:
                r += [(i, ge1, le1) for i in subs(a,b)]
        elif ge2 > ge1 and le2 < le1:
            r += [(a, ge1, ge2-1), (a, le2+1, le1)]
            r += [(i, ge2, le2) for i in subs(a,b)]
        elif ge2 <= ge1 and le2 < le1 and le2 >= ge1:
            r += [(a, le2+1, le1)]
            r += [(i, ge1, le2) for i in subs(a,b)]
        elif ge2 > ge1 and le2 >= le1 and ge2 <= le1:
            r += [(a, ge1, ge2-1)]
            r += [(i, ge2, le1) for i in subs(a,b)]
        else:
            r += [(a, ge1, le1)]
    return r
        
    
            
    
    
def subs_rectangle(recs, new_rec):
    _recs = []    
    ge2 = new_rec[1]
    le2 = new_rec[2]
        
    for q in recs:
        ge1 = q[1]
        le1 = q[2]
        
        if len(q[0]) < len(new_rec[0]):
            if new_rec[0].startswith(q[0]):
                if ge1 <= le2 and ge2 <= le1:
                    x = new_rec[0][len(q[0]):]
                    for i in range(len(x)):
                        _x = x
                        _x = _x[:i] + inv(_x[i]) + _x[i+1:]
                        _recs.append((q[0] + _x[:i+1], ge1, le1))
                    
                    _recs.extend(LeGeOverlapHandler(new_rec[0], ge1, le1, ge2, le2))
                        
                else:
                    _recs.append(q)
            else:
                _recs.append(q)
                
        else:
            if q[0].startswith(new_rec[0]):
                if ge1 <= le2 and ge2 <= le1:
                    _recs.extend(LeGeOverlapHandler(new_rec[0], ge1, le1, ge2, le2))
                else:
                    _recs.append(q)
            else:
                _recs.append(q)
    return _recs


def convert_prefix_list_to_prefix_set(prefix_list):
    pref_set = []
    pd = [] ## allow/deny
    prefix_list = convert_prefix_to_binary(prefix_list)
    # print("@@@prefix-list: ",prefix_list)
    for i in prefix_list:
        p = [i[0]]
        for s in pref_set:
            # p = subs_rectangle(p,s)
            p = subs_prefix(p,s)
        pref_set = pref_set + p
        # print("@@@pref_set: ",pref_set)
        if p!=[]:
            for _ in range(len(p)):
                pd.append(i[1])

    final_pref_set = []
    for i in range(len(pd)):
        x = pd[i]
        if x:
            final_pref_set.append(pref_set[i])

    # print("@@@final: ",final_pref_set)

    return convert_binary_to_prefix(final_pref_set)
