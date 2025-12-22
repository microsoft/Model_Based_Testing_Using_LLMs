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

NSDI = False
output_dir_common = pathlib.Path("..//tests//bgp//NSDI")
n_models = 1

def confed_check():
    
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
    g.CallEdge(router_validity_model, valid_input_model)
    g.Pipe(confederation_model, valid_input_model)
    
    output_dir = output_dir_common / "CONFED"
    inputs = run(g, k=n_models, debug=output_dir, timeout_sec=300)

    ## Save test cases

    test_dir = output_dir
    test_dir.mkdir(exist_ok=True)
    test_cases = []
    for input in inputs:
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

    with open(test_dir / "tests.json", "w") as f:
        json.dump(test_cases, f, indent=4)
    print(f"[DONE] Generated {len(test_cases)} test cases for BGP confederation check.")
    

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-m", "--module", type=str, required=True,
                        choices=["confed", "rr", "rmap_pl", "rr_rmap"],
                        help="The BGP module to generate inputs for.", default="confed")
    parser.add_argument("-n", "--nsdi", action="store_true",
                        help="Generate NSDI inputs.", default=False)
    parser.add_argument("-r", "--runs", type=int, required=False,
                        help="Number of runs to generate inputs for.", default=10)
    args = parser.parse_args()
    NSDI = args.nsdi
    if args.module == "cname":
        cname_match_check(args.runs)
    elif args.module == "dname":
        dname_match_check(args.runs)
    elif args.module == "wildcard":
        wildcard_match_check(args.runs)
    elif args.module == "ipv4":
        ipv4_match_check(args.runs)
    elif args.module == "full_lookup":
        full_query_lookup()
    elif args.module == "loop_count":
        loop_count()
    elif args.module == "rcode":
        return_code_lookup()
    elif args.module == "authoritative":
        authoritative_lookup()
    else:
        print("Invalid module selected.")


   
    






