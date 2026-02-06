import json
import pathlib
from typing import Generator, List, Tuple
import eywa
import eywa.ast as ast
import eywa.oracles as oracles
import regex as re
import eywa.run as run
from argparse import ArgumentParser
from termcolor import colored
import ipaddress

NSDI = False
output_dir_common = pathlib.Path("..//tests//bgp//NSDI")

def int_to_prefix(value: int, prefix_len: int) -> str:
    """
    Convert an integer IPv4 address and prefix length to CIDR notation.

    Example:
        int_to_prefix(1671446532, 24) -> '99.151.128.0/24'
    """
    ip = ipaddress.IPv4Address(value)
    network = ipaddress.IPv4Network(f"{ip}/{prefix_len}", strict=False)
    return str(network)

def confed_check(runs, timeout):
    
    """
    
    (Exabgp) ----------------- R2 ----------------- R3
    
    """

    router = ast.Struct(
        "Router",
        asNumber = ast.Int(32),
        subAS = ast.Int(32)
    )
    
    outputRIB = ast.Struct(
        "outputRIB",
        asNumbers2 = ast.Array(ast.Int(32), 3),
        isSubAS2 = ast.Array(ast.Bool(), 3),
        asNumbers3 = ast.Array(ast.Int(32), 3),
        isSubAS3 = ast.Array(ast.Bool(), 3),
        localPref3 = ast.Int(32)
    )

    p0 = ast.Parameter("router2", router, "Second router")
    p1 = ast.Parameter("router3", router, "Third router")
    p2 = ast.Parameter("isValidConfiguration", ast.Bool(), "True if the both the router configurations (router 2 and 3) are valid, false otherwise")
    
    p3 = ast.Parameter("originAS", ast.Int(32), "AS of the Originating router")
    p4 = ast.Parameter("isValidInput", ast.Bool(), "True if the router configurations of routers 2 and 3 and the AS number & local preference of the originating router are valid.")
    
    p7 = ast.Parameter("removePrivateAS", ast.Bool(), "A flag for router 2. Similar to cisco remove-private-as command. If this is true, then the router 2 should remove all private AS numbers from its AS path before forwarding it to router 3.")
    p8 = ast.Parameter("isExternalPeer", ast.Bool(), "A flag for router 3. If this is True then in BGP config of router 3. the neighbor is configured as neighbor peer-as external. i.e. if this is enabled then connection will be denied if the AS number router 2 is same as mine.")
    p9 = ast.Parameter("replaceAS", ast.Bool(), "A flag for router 2. If this is true, then the router should replace all private AS numbers with the confederation number before forwarding the route to router 3.")
    p10 = ast.Parameter("LocalPref", ast.Int(32), "The local preference value set at router 2.")

    
    p5 = ast.Parameter("finalRIB", outputRIB, "a struct containing the final AS path and local preference value for the installled route in RIBs of router 2 and router 3.")
    p6 = ast.Parameter("void_res", ast.Void(), "")
    
    router_validity_model = ast.Function(
        "checkValidRouterConfiguration",
        """A function that takes as input two router configurations and returns True if both of them are valid, false otherwise.
Conditions for validitity:
   1. Neither router should have asNumber equal to 0.
   2. If a router belongs to a confederation, then subAS must be greater than 0.
   3. If both routers have the same asNumber, then either both of them must have subAS equal to 0 or both should be non-zero.
   4. For both routers, the asNumber should be in the range [400, 65535] both inclusive.
   5. If router 2 is within a confederation, then router 2 subAS can be equal to router 3 asNumber or less than 300.
   6. If router 3 is within a confederation, then router 3 subAS can be equal to router 2 asNumber or less than 300.""",
        [p0, p1, p2]
    )
    
    valid_input_model = ast.Function(
        "checkValidInputs",
        """A function that takes as input the originating AS and local preference for a route and the configurations for two routers and checks whether they are valid.
Conditions for validity:
    1. Both the input router configurations should be valid.
    2. If router2.asNumber == router3.asNumber and router2.subAS == router3.subAS, then removePrivateAS should be set to false
    3. originAS should not be equal to 0.
    4. originAS should not be equal to router 2 asNumber or router 3 asNumber.
    5. The inputLocalPref should be in the range [50, 150] both inclusive.
    6. If router 2 is within a confederation, then router 2 subAS can be equal to originAS or less than than 300.
    7. originAS should be greater than or equal to 400 and less than or equal to 65535.
    8. If "removePrivateAS" is false, then "replaceAS" should be false.""",
        [p3, p0, p1, p7, p9, p10, p4]
    )
    
    confederation_model = ast.Function(
        "computeASPaths",
        """A function that takes as input the originating AS, configs of router 2 and router 3 and updates a struct with the final AS paths and local preferences when the
route is installed in the RIBs of router 2 and router 3. Originating router, Router 2 and Router 3 are connected in series and the route is advertised to router 2 first from the originating router, which then
sets the given local preference value and forwards it to router 3. You have to take into consideration all BGP confederation rules for handling private AS numbers, iBGP and Confederation eBGP
and forwarding updates. The topology is as follows: 

                        Originating Router ----------------- R2 ----------------- R3

A few points to keep in mind:
1. If for any router configuration (router 2 or router 3), subAS is equal to 0, then that router is not within a confederation.
2. If (the bool flag isExternalPeer is True for router 3) and ((router 2 asNumber != router 3 asNumber) or (router2 and router 3 are in same confederation but subASes are different)): then the connection will be established between router 2 and router 3.
3. And if the flag removePrivateAS is True for router 2 then strip off the private AS numbers from AS path before forwarding it to router 3.
4. asNumbers2 and asNumbers3 are the aspath of the route received at router2 and router 3 respectively. The elements of the AS path arrays should be 0-padded on the right-side and the isSubAS array indicates whether the corresponding element in the AS path array is a sub AS (0 if not, 1 if it is).
5. Remember that while advertising a route to a BGP peer that is outside the confederation, the router should remove all sub AS numbers within its confederation and replace it with the confederation number. You should left-shift the other AS numbers in the path accordingly.
6. localPref3 is the local preference value of the installed route in the RIB of router 3. Consider appropriate eBGP, iBGP and confederation rules for setting the local preference value, e.g. Usually, the LOCAL_PREFERENCE attribute is not shared between ASs, as it influences path preference only within a specific AS. However, this restriction is lifted within a confederation, allowing ASs in the confederation to share LOCAL_PREFERENCE values.""",
        [p3, p0, p1, p7, p9, p10, p8, p5, p6]
    )

    g = eywa.DependencyGraph()
    g.CallEdge(valid_input_model, [router_validity_model])
    g.Pipe(confederation_model, valid_input_model)
    
    output_dir = output_dir_common / "CONFED"
    inputs = run(g, k=runs, debug=output_dir, timeout_sec=timeout)

    ## Save test cases

    test_dir = output_dir
    test_dir.mkdir(exist_ok=True)
    test_cases = []
    for input in inputs:
        try:
            originAS = input[0]
            router2 = input[1]
            router3 = input[2]
            removePrivateAS = input[3]
            replaceAS = input[4]
            localPref = input[5]
            isExternalPeer = input[6]
            test_case = {
                "originAS": originAS,
                "router2": {
                    "asNumber": router2["asNumber"],
                    "subAS": router2["subAS"]
                },
                "router3": {
                    "asNumber": router3["asNumber"],
                    "subAS": router3["subAS"]
                },
                "removePrivateAS": removePrivateAS,
                "replaceAS": replaceAS,
                "localPref": localPref,
                "isExternalPeer": isExternalPeer
            }
            test_cases.append(test_case)
        except Exception as e:
            continue

    with open(test_dir / "tests.json", "w") as f:
        json.dump(test_cases, f, indent=4)
    print(f"[DONE] Generated {len(test_cases)} test cases for BGP confederation check.")
    
def rr_check(runs, timeout):
    """
    --------->------- R2 --------->-------

    input parameters:
    1. inRRflag : 
        0 : R2 is a client to R1 (RR)
        1 : R2 is a route reflector to R1
        2 : R2 is a non-client to R1 (RR)

    2. outRRflag :
        0 : R2 is a client to R3 (RR)
        1 : R2 is a route reflector to R3
        2 : R2 is a non-client to R3 (RR)

    3. inAS : 
        True : if AS of R2 is same as AS of R1
        False : if AS of R2 is different from AS of R1
    
    4. outAS :
        True : if AS of R2 is same as AS of R3
        False : if AS of R2 is different from AS of R3

    output:
    1. isReceivedR2 : True if route is received at R2
    2. isReceivedR3 : True if route is received at R3

    RR rules:
    1. A route learned from a non-RR client is advertised to RR clients but not to non-RR clients.
    2. A route learned from an RR client is advertised to both RR clients and non-RR clients. Even the RR client that advertised the route will receive a copy and discard it because it sees itself as the originator.
    3. A route learned from an EBGP neighbor is advertised to both RR clients and non-RR clients.
    """
    
    outputRIB = ast.Struct(
        "outputRIB",
        isReceived = ast.Bool(),
        isAdvertised = ast.Bool()
    )

    p_inRRflag = ast.Parameter("inRRflag", ast.Int(32), "0 : R2 is a client to R1 (RR), 1 : R2 is a route reflector to R1, 2 : R2 is a non-client to R1 (RR)")
    p_outRRflag = ast.Parameter("outRRflag", ast.Int(32), "0 : R2 is a client to R3 (RR), 1 : R2 is a route reflector to R3, 2 : R2 is a non-client to R3 (RR)")
    p_inAS = ast.Parameter("inAS", ast.Bool(), "True : if AS of R2 is same as AS of R1, False : if AS of R2 is different from AS of R1")
    p_outAS = ast.Parameter("outAS", ast.Bool(), "True : if AS of R2 is same as AS of R3, False : if AS of R2 is different from AS of R3")

    p_valid = ast.Parameter("isValidConfiguration", ast.Bool(), "True if the router configuration (R2) is valid, false otherwise")
    
    p_rib = ast.Parameter("finalRIBs", outputRIB, "a struct containing two boolean values indicating whether the route is received at router 2 at one interface and if the route is advertised to another router through another interface respectively.")
    p_void = ast.Parameter("void_res", ast.Void(), "")
    
    router_validity_model = ast.Function(
        "checkValidRouterConfiguration",
        """A function that takes as input:inRRflag, outRRflag, as_num, inAS, outAS and returns True if the router configuration is valid, false otherwise. 
Conditions for validitity:
1. The flags inRRflag and outRRflag should be in the range [0, 2] both inclusive.
2. if inAS is False, then inRRflag should be 2.
3. if outAS is False, then outRRflag should be 2.""",
        [p_inRRflag, p_outRRflag, p_inAS, p_outAS, p_valid]
    )
    
    rr_model = ast.Function(
        "predictRouteReflectorRibs",
        """A function that takes as input some flags related to router 2 and its relationship with neighbors and updates a struct with two booleans isReceived (true if route received by R2) and isAdvertised (true if route advertised to neighbor).
You have to take into consideration all BGP route reflector rules, eBGP, iBGP rules.""",
        [p_inRRflag, p_outRRflag, p_inAS, p_outAS, p_rib, p_void]
    )
    
    g = eywa.DependencyGraph()
    g.Pipe(rr_model, router_validity_model)

    output_dir = output_dir_common / "RR"
    inputs = run(g, k=runs, debug=output_dir, timeout_sec=timeout)

    ## Save test cases
    test_dir = output_dir
    test_dir.mkdir(exist_ok=True)
    test_cases = []
    for input in inputs:
        try:
            inRRflag = input[0]
            outRRflag = input[1]
            inAS = input[2]
            outAS = input[3]
            test_case = {
                "inRRflag": inRRflag,
                "outRRflag": outRRflag,
                "inAS": inAS,
                "outAS": outAS
            }
            test_cases.append(test_case)
        except Exception as e:
            continue

    with open(test_dir / 'tests.json', 'w') as f:
        json.dump(test_cases, f, indent=4)
    print(f"[DONE] Generated {len(test_cases)} test cases for BGP route reflector check.")

def rmap_pl_check(runs, timeout):
    # Define a prefixListEntry struct with fields prefix, prefixLength, le, ge, any, permit
    pr_list_entry = ast.Struct(
        "PrefixListEntry",
        prefix = ast.Int(32),
        prefixLength = ast.Int(8),
        le = ast.Int(32),
        ge = ast.Int(32),
        any = ast.Bool(),
        permit = ast.Bool()
    )

    # Define a struct named Route with fields prefix, prefixLength, nextHop, localPref, asPath, community, origin, med
    route = ast.Struct(
        "Route",
        prefix = ast.Int(32),
        prefixLength = ast.Int(8),
        localPref = ast.Int(32),
        med = ast.Int(32)
    )
    
    # Prefix list is a single entry (not an array)
    pr_list = pr_list_entry
    
    # Removed all set* fields from route map stanza; matchPrefixList is a single entry now
    rmap_stanza = ast.Struct(
        "RouteMapStanza",
        matchPrefixList = pr_list,
        matchLocalPref = ast.Int(32),
        matchMed = ast.Int(32),
        rmapAction = ast.Bool()
    )
    
    rmap = ast.Struct(
        "RouteMap",
        stanza = ast.Array(rmap_stanza, 1)
    )
    
    result = ast.Struct(
        "Result",
        route = route,
        isPermitted = ast.Bool()
    )
    
    p0 = ast.Parameter("route", route, "Route to be matched")
    p1 = ast.Parameter("routeMap", rmap, "Route map to be applied")
    p2 = ast.Parameter("result", result, "Result of applying route map on route")
    p3 = ast.Parameter("void_res", ast.Void(), "")
    
    p4 = ast.Parameter("maskLength", ast.Int(32), "The length of the prefix")
    p5 = ast.Parameter("subnetMask", ast.Int(32), "The unsinged integer representation of the prefix length")
    p6 = ast.Parameter("pfe", pr_list_entry, "Prefix list entry")
    p7 = ast.Parameter("pr_match", ast.Bool(), "True if the route matches the prefix list entry")
    
    p8 = ast.Parameter("prefixList", pr_list, "Single prefix list entry")
    p9 = ast.Parameter("valid", ast.Bool(), "True if the prefix list is valid")
    p10 = ast.Parameter("validRoute", ast.Bool(), "True if the route is valid")
    p11 = ast.Parameter("validInputs", ast.Bool(), "True if the route map and route are valid")
    
    prefix_length_to_subnet_mask_model = ast.Function(
        "prefixLenToSubnetMask",
        "a function that takes as input the prefix length and converts it to the corresponding unsigned integer representation",
        [p4, p5]
    )
    
    prefix_list_entry_match_model = ast.Function(
        "isMatchPrefixListEntry",
        """A function that takes as input a prefix list entry and a BGP route advertisement. If the route advertisement matches the prefix, then the function should return the value of the permit flag. In case there is no match, the function should vacuously return false.""",
        [p0, p6, p7]
    )
    
    route_validity_model =  ast.Function(
        "isValidRoute",
        """A function that checks whether the BGP route advertisement has a valid BGP attributes.
Conditions for valiidity:
    1. The IPv4 address should be in the range 1671377732 - 1679687938.
    2. The subnet mask length must be in the range 0-32.
    3. The prefix value should be greater than 0 i.e (ipaddr & subnet_mask) > 0.
    4. The local preference value should be in the range [100, 200].
    5. The MED value should be in the range [20, 50].""",
        [p0, p10]
    )
    
    prefix_list_validity_model = ast.Function(
        "isValidPrefixList",
        """A function that checks whether an input prefix list (single entry) is valid.
Conditions for validity for the single prefix-list entry:
    1. If the 'any' flag is set, then:
        i) the IPv4 address must be equal to 0
        ii) the subnet mask length must be equal to 0
        iii) GE must be equal to 0
        iv) LE must be equal to 32
    2. If the 'any' flag is not set, then:
        i) The IPv4 address should be in the range 1671377732 - 1679687938.
        ii) The subnet mask length, LE and GE values must all be in the range 0-32.
        iii) subnet mask length <= GE <= LE
        iv) The prefix value should be greater than 0 i.e (ipaddr & subnet_mask) > 0""",
        [p8, p9]
    )
    
    valid_input_model = ast.Function(
        "checkValidInputs",
        """A function that takes as input a BGP route advertisement and a route map. It checks whether the input route advertisement and route map are valid. The function should return true if both the route advertisement and route map are valid, false otherwise.
Conditions for validity:
    1. The single prefix-list entry should be valid.
    2. matchLocalPref should be in the range [100, 200].
    3. matchMed should be in the range [20, 50].
    4. The route advertisement should be valid.""",
    [p0, p1, p11]
    )
    
    rmap_match_model = ast.Function(
        "isMatchRouteMap",
        """A function that takes as input a BGP route advertisement and a route map. It checks whether the route advertisement matches the stanza in the route map.
If a match is found, the function should update the Result struct's isPermitted flag according to the matching stanza's permit value and set the output route accordingly. If no match is found, the function should set the isPermitted flag in Result struct to false and the attributes of the route should be set to zero.""",
        [p0, p1, p2, p3]
    )

    ## New API
    g = eywa.DependencyGraph()
    g.CallEdge(prefix_list_validity_model, [prefix_length_to_subnet_mask_model])
    g.CallEdge(route_validity_model, [prefix_length_to_subnet_mask_model])
    g.CallEdge(valid_input_model, [prefix_list_validity_model, route_validity_model])
    g.CallEdge(prefix_list_entry_match_model, [prefix_length_to_subnet_mask_model])
    g.CallEdge(rmap_match_model, [prefix_list_entry_match_model])
    g.Pipe(rmap_match_model, valid_input_model)

    output_dir = output_dir_common / "RMAP_PL"
    inputs = run(g, k=runs, debug=output_dir, timeout_sec=timeout)
    
    ## Save test cases
    test_dir = output_dir
    test_dir.mkdir(exist_ok=True)
    test_cases = []
    for input in inputs:
        try: 
            route = input[0]
            routeMap = input[1]
            # matchPrefixList is a single entry now (not an array)
            mpl = routeMap["stanza"][0]["matchPrefixList"]
            if mpl["any"]:
                pl_match_str = "any"
            else:
                pl_match_str = int_to_prefix(mpl["prefix"], mpl["prefixLength"]) + f" le {mpl['le']} ge {mpl['ge']}"
            test_case = {
                "route": {
                    "prefix": int_to_prefix(route["prefix"], route["prefixLength"]),
                    "local_pref": route["localPref"],
                    "med": route["med"]
                },
                "rmap": {
                    "local_pref": routeMap["stanza"][0]["matchLocalPref"],
                    "med": routeMap["stanza"][0]["matchMed"],
                    "prefix_list": [
                        {
                            "match": pl_match_str,
                            "action": "permit" if mpl["permit"] else "deny"
                        }
                    ],
                    "rmap_action": "permit" if routeMap["stanza"][0]["rmapAction"] else "deny"
                }
            }
            test_cases.append(test_case)
        except Exception as e:
            continue
    with open(test_dir / 'tests.json', 'w') as f:
        json.dump(test_cases, f, indent=4)
    print(f"[DONE] Generated {len(test_cases)} test cases for BGP route map with single-entry prefix list.")

def rr_rmap_check(runs, timeout):
    """
    input parameters:
    1. inRRflag : 
        0 : R2 is a client to R1 (RR)
        1 : R2 is a route reflector to R1
        2 : R2 is a non-client to R1 (RR)

    2. outRRflag :
        0 : R2 is a client to R3 (RR)
        1 : R2 is a route reflector to R3
        2 : R2 is a non-client to R3 (RR)

    3. inAS : 
        True : if AS of R2 is same as AS of R1
        False : if AS of R2 is different from AS of R1
    
    4. outAS :
        True : if AS of R2 is same as AS of R3
        False : if AS of R2 is different from AS of R3

    5. outRmap: outbound Route map to be applied on the advertised route from R2 before advertising to R3

    6. inRoute: Route to be matched

    output:
    1. isReceived : True if route is received at R2
    2. isAdvertised : True if route is received at R3
    3. route_at_R2 : Route at R2
    4. route_at_R3 : Route at R3
    
    """

    # Define a prefixListEntry struct with fields prefix, prefixLength, le, ge, any, permit
    prefix_list_entry = ast.Struct(
        "PrefixListEntry",
        prefix = ast.Int(32),
        prefixLength = ast.Int(8),
        le = ast.Int(32),
        ge = ast.Int(32),
        any = ast.Bool(),
        permit = ast.Bool()
    )

    # Define a struct named Route with fields prefix, prefixLength, nextHop, localPref, asPath, community, origin, med
    route = ast.Struct(
        "Route",
        prefix = ast.Int(32),
        prefixLength = ast.Int(8),
        localPref = ast.Int(32),
        med = ast.Int(32)
    )
    
    # Single prefix list entry (not an array)
    prefix_list = prefix_list_entry
    
    # Removed all set* fields from route map stanza; matchPrefixList is a single entry now
    rmap_stanza = ast.Struct(
        "RouteMapStanza",
        matchPrefixList = prefix_list,
        matchLocalPref = ast.Int(32),
        matchMed = ast.Int(32),
        rmapAction = ast.Bool()
    )
    
    rmap = ast.Struct(
        "RouteMap",
        stanza = ast.Array(rmap_stanza, 1)
    )
    
    result = ast.Struct(
        "Result",
        route = route,
        isPermitted = ast.Bool()
    )
    
    final_output = ast.Struct(
        "outputRIB",
        isReceivedR2 = ast.Bool(),
        isReceivedR3 = ast.Bool(),
        route_at_R2 = route,
        route_at_R3 = route
    )

    p_route = ast.Parameter("route", route, "Route to be matched")
    p_rmap = ast.Parameter("routeMap", rmap, "Route map to be applied")
    p_result = ast.Parameter("result", result, "Result of applying route map on route")
    
    p_mask_len = ast.Parameter("maskLength", ast.Int(32), "The length of the prefix")
    p_subnet_mask = ast.Parameter("subnetMask", ast.Int(32), "The unsinged integer representation of the prefix length")
    p_prefix_list_entry = ast.Parameter("prefixListEntry", prefix_list_entry, "Prefix list entry")
    p_prefix_match = ast.Parameter("prefix_match", ast.Bool(), "True if the route matches the prefix list entry")
    
    # prefixList param is now a single entry
    p_prefix_list = ast.Parameter("prefixList", prefix_list, "Single prefix list entry")
    p_valid_prefix_list = ast.Parameter("prefixListValid", ast.Bool(), "True if the prefix list is valid")
    p_valid_route = ast.Parameter("validRoute", ast.Bool(), "True if the route is valid")
    p_valid_route_rmap = ast.Parameter("validRouteRmap", ast.Bool(), "True if the route map and route are valid")

    p_inRRflag = ast.Parameter("inRRflag", ast.Int(32), "0 : R2 is a client to R1 (RR), 1 : R2 is a route reflector to R1, 2 : R2 is a non-client to R1 (RR)")
    p_outRRflag = ast.Parameter("outRRflag", ast.Int(32), "0 : R2 is a client to R3 (RR), 1 : R2 is a route reflector to R3, 2 : R2 is a non-client to R3 (RR)")
    p_inAS = ast.Parameter("inAS", ast.Bool(), "True : if AS of R2 is same as AS of R1, False : if AS of R2 is different from AS of R1")
    p_outAS = ast.Parameter("outAS", ast.Bool(), "True : if AS of R2 is same as AS of R3, False : if AS of R2 is different from AS of R3")

    p_rr_valid = ast.Parameter("isValidConfiguration", ast.Bool(), "True if the router configuration (R2) is valid, false otherwise")

    p_input_valid = ast.Parameter("isValidInput", ast.Bool(), "True if the input parameters are valid, false otherwise")
    
    p_rib = ast.Parameter("finalOutput", final_output, "a struct containing two boolean values indicating whether the route is received at router 2 at one interface and if the route is advertised to another router through another interface respectively.")
    p_void = ast.Parameter("void_res", ast.Void(), "")

    prefix_length_to_subnet_mask_model = ast.Function(
        "prefixLenToSubnetMask",
        "a function that takes as input the prefix length and converts it to the corresponding unsigned integer representation",
        [p_mask_len, p_subnet_mask]
    )
    
    prefix_list_entry_match_model = ast.Function(
        "isMatchPrefixListEntry",
        """A function that takes as input a prefix list entry and a BGP route advertisement. If the route advertisement matches the prefix, then the function should return the value of the permit flag. In case there is no match, the function should vacuously return false.""",
        [p_route, p_prefix_list_entry, p_prefix_match]
    )
    
    route_validity_model =  ast.Function(
        "isValidRoute",
        """A function that checks whether the BGP route advertisement has a valid BGP attributes.
Conditions for valiidity:
    1. The IPv4 address should be in the range 1671377732 - 1679687938.
    2. The subnet mask length must be in the range 0-32.
    3. The prefix value should be greater than 0 i.e (ipaddr & subnet_mask) > 0.
    4. The local preference value should be in the range [100, 200].
    5. The MED value should be in the range [20, 50].""",
        [p_route, p_valid_route]
    )
    
    prefix_list_validity_model = ast.Function(
        "isValidPrefixList",
        """A function that checks whether an input prefix list (single entry) is valid.
Conditions for validity for the single prefix-list entry:
    1. If the 'any' flag is set, then:
        i) the IPv4 address must be equal to 0
        ii) the subnet mask length must be equal to 0
        iii) GE must be equal to 0
        iv) LE must be equal to 32
    2. If the 'any' flag is not set, then:
        i) The IPv4 address should be in the range 1671377732 - 1679687938.
        ii) The subnet mask length, LE and GE values must all be in the range 0-32.
        iii) subnet mask length <= GE <= LE
        iv) The prefix value should be greater than 0 i.e (ipaddr & subnet_mask) > 0""",
        [p_prefix_list, p_valid_prefix_list]
    )
    
    route_rmap_validity_model = ast.Function(
        "isValidRouteRmap",
        """A function that takes as input a BGP route advertisement and a route map. It checks whether the input route advertisement and route map are valid. The function should return true if both the route advertisement and route map are valid, false otherwise.
Conditions for validity:
    1. The prefix list (single entry) should be valid.
    2. matchLocalPref should be in the range [100, 200].
    3. matchMed should be in the range [20, 50].
    4. The route advertisement should be valid.""",
    [p_route, p_rmap, p_valid_route_rmap]
    )

    
    rmap_match_model = ast.Function(
        "isMatchRouteMap",
        """A function that takes as input a BGP route advertisement and a route map. It checks whether the route advertisement matches the stanza in the route map.
If a match is found, the function should update a struct with the output route advertisement and a boolean value indicating whether the route is permitted by the route map. If no match is found, the function should set the isPermitted flag in Result struct to false and the attributes of the route should be set to zero.""",
        [p_route, p_rmap, p_result, p_void]
    )
    
    
    rr_validity_model = ast.Function(
        "isValidRouteReflectorFlags",
        """A function that takes as input:inRRflag, outRRflag, as_num, inAS, outAS and returns True if the router configuration is valid, false otherwise. 
Conditions for validitity:
1. The flags inRRflag and outRRflag should be in the range [0, 2] both inclusive.
2. if inAS is False, then inRRflag should be 2.
3. if outAS is False, then outRRflag should be 2.""",
        [p_inRRflag, p_outRRflag, p_inAS, p_outAS, p_rr_valid]
    )
    

    input_validity_model = ast.Function(
        "isValidInput",
        """A function that takes as input the router configuration parameters, route advertisement and route map. It checks whether the input parameters are valid. The function should return true if all the input parameters are valid, false otherwise.""",
        [p_route, p_rmap, p_inRRflag, p_outRRflag, p_inAS, p_outAS, p_input_valid]
    )

    rr_model = ast.Function(
        "predictRouteReflectorRibs",
        """A function that takes as input an incoming route, an outbound route map, and some flags related to router 2 and its relationship with neighbors and updates a struct with two booleans isReceived (true if route received by R2) and isAdvertised (true if route advertised to neighbor) anf two routes: route_at_R2 and route_at_R3.
If R2 receives the route, then before advertising it to other interfaces, it applies the outbound route map on it. You have to take into consideration all BGP route reflector rules, eBGP, iBGP rules and route map rules.""",
        [p_route, p_rmap, p_inRRflag, p_outRRflag, p_inAS, p_outAS, p_rib, p_void]
    )
    
    ## New API
    g = eywa.DependencyGraph()
    g.CallEdge(prefix_list_validity_model, [prefix_length_to_subnet_mask_model])
    g.CallEdge(route_validity_model, [prefix_length_to_subnet_mask_model])
    g.CallEdge(route_rmap_validity_model, [prefix_list_validity_model, route_validity_model])
    g.CallEdge(input_validity_model, [route_rmap_validity_model, rr_validity_model])
    g.CallEdge(rmap_match_model, [prefix_list_entry_match_model])
    g.CallEdge(rr_model, [rmap_match_model])
    g.Pipe(rr_model, input_validity_model)

    output_dir = output_dir_common / "RR_RMAP"
    inputs = run(g, k=runs, debug=output_dir, timeout_sec=timeout)

    ## Save test cases
    test_dir = output_dir
    test_dir.mkdir(exist_ok=True)
    test_cases = []
    for input in inputs:
        try: 
            route = input[0]
            routeMap = input[1]
            inRRflag = input[2]
            outRRflag = input[3]
            inAS = input[4]
            outAS = input[5]
            mpl = routeMap["stanza"][0]["matchPrefixList"]
            if mpl["any"]:
                pl_match_str = "any"
            else:
                pl_match_str = int_to_prefix(mpl["prefix"], mpl["prefixLength"]) + f" le {mpl['le']} ge {mpl['ge']}"

            # matchPrefixList is now a single entry (not an array)
            mpl = routeMap["stanza"][0]["matchPrefixList"]

            test_case = {
                "route": {
                    "prefix": int_to_prefix(route["prefix"], route["prefixLength"]),
                    "local_pref": route["localPref"],
                    "med": route["med"]
                },
                "rmap": {
                    "local_pref": routeMap["stanza"][0]["matchLocalPref"],
                    "med": routeMap["stanza"][0]["matchMed"],
                    "prefix_list": [
                        {
                            "match": pl_match_str,
                            "action": "permit" if mpl["permit"] else "deny"
                        }
                    ],
                    "rmap_action": "permit" if routeMap["stanza"][0]["rmapAction"] else "deny"
                },
                "inRRflag": inRRflag,
                "outRRflag": outRRflag,
                "inAS": inAS,
                "outAS": outAS
            }
            test_cases.append(test_case)
        except Exception as e:
            continue
        
    with open(test_dir / 'tests.json', 'w') as f:
        json.dump(test_cases, f, indent=4)
    print(f"[DONE] Generated {len(test_cases)} test cases for BGP route reflector with route map check.")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-m", "--module", type=str, required=True,
                        choices=["confed", "rr", "rmap_pl", "rr_rmap"],
                        help="The BGP module to generate inputs for.", default="confed")
    # parser.add_argument("-n", "--nsdi", action="store_true",
    #                     help="Generate NSDI inputs.", default=False)
    parser.add_argument("-r", "--runs", type=int, required=False,
                        help="Number of runs to generate inputs for.", default=10)
    parser.add_argument("--timeout", type=int, required=False,
                        help="Timeout in seconds for each run.", default=300)
    args = parser.parse_args()
    # NSDI = args.nsdi
    if args.module == "confed":
        confed_check(args.runs, args.timeout)
    elif args.module == "rr":
        rr_check(args.runs, args.timeout)
    elif args.module == "rmap_pl":
        rmap_pl_check(args.runs, args.timeout)
    elif args.module == "rr_rmap":
        rr_rmap_check(args.runs, args.timeout)
    else:
        print("Invalid module selected.")


   
    






