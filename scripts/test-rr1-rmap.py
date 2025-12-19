## add "eywa" to the path
import sys
sys.path.append("..")
import json

import eywa
import eywa.ast as ast
import eywa.regex as re
import eywa.oracles as oracles
from eywa.composer import DependencyGraph
from termcolor import colored
import json
import os


def test_rr_rmap():
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

    5. outRmap: outbound Route map to be applied on the advertised route before advertising to neighbor

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
        nextHop = ast.Int(32),
        localPref = ast.Int(32),
        community = ast.Array(ast.Int(32), 1),
        med = ast.Int(32)
    )
    
    prefix_list = ast.Array(prefix_list_entry, 2)
    
    rmap_stanza = ast.Struct(
        "RouteMapStanza",
        matchPrefixList = prefix_list,
        matchLocalPref = ast.Int(32),
        matchMed = ast.Int(32),
        setLocalPref = ast.Int(32),
        setMed = ast.Int(32),
        setNextHop = ast.Int(32),
        setCommunity = ast.Int(32),
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
    
    p_prefix_list = ast.Parameter("prefixList", prefix_list, "Prefix list")
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
    5. The MED value should be in the range [20, 50].
    6. The next hop value should be in the range 1671377732 - 1679687938.
    7. The community value should be 0.""",
        [p_route, p_valid_route]
    )
    
    prefix_list_validity_model = ast.Function(
        "isValidPrefixList",
        """A function that checks whether an input prefix list is valid.
Conditions for validity:
    1. Both entries in the prefix list should be unique.
    2. Within a prefix list entry, if the any flag is set, then the following conditions must be satisified:
        i) the IPv4 address must be equal to 0
        ii) the subnet mask length must be equal to 0
        iii) GE must be equal to 0
        iv) LE must be equal to 32
        
    If, however, the any flag is not set, then all the following conditions must be satisfied:
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
    1. The prefix list should be valid.
    2. matchLocalPref should be in the range [100, 200].
    3. matchMed should be in the range [20, 50].
    4. setLocalPref should be in the range [300, 400].
    5. setMed should be in the range [70, 90].
    6. setNextHop should be in the range 1671377732 - 1679687938.
    7. setCommunity should be in the range 10 - 20.
    8. The route advertisement should be valid.""",
    [p_route, p_rmap, p_valid_route_rmap]
    )


    
    rmap_match_model = ast.Function(
        "isMatchRouteMap",
        """A function that takes as input a BGP route advertisement and a route map. It checks whether the route advertisement matches any of the stanzas in the route map.
If a match is found, the function should update a struct with the output route advertisement and a boolean value indicating whether the route is permitted by the route map. In case
of a successful match, the function should modify the output route according to the set statements in the stanza. If no 
match is found, the function should set the isPermitted flag in Result struct to false and the attributes of the route should be set to zero.""",
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

    # prefix_length_to_subnet_mask_oracle = run_wrapper_model(prefix_length_to_subnet_mask_model)
    # route_validity_oracle = run_wrapper_model(route_validity_model, [prefix_length_to_subnet_mask_model])
    # prefix_list_validity_oracle = run_wrapper_model(prefix_list_validity_model, [prefix_length_to_subnet_mask_model])
    # route_rmap_validity_oracle = run_wrapper_model(route_rmap_validity_model, function_prototypes=[prefix_list_validity_model, route_validity_model])
    # rr_validity_oracle = run_wrapper_model(rr_validity_model)
    # input_validity_oracle = run_wrapper_model(input_validity_model, [route_rmap_validity_model, rr_validity_model], partial=False)
    
    # prefix_list_validity_oracle.implementation = replace_wrapper_code(prefix_list_validity_oracle.implementation, prefix_length_to_subnet_mask_oracle.implementation, prefix_list_validity_oracle.function_declares[0])
    # route_validity_oracle.implementation = remove_function_declaration(route_validity_oracle.implementation, route_validity_oracle.function_declares[0])
    # route_rmap_validity_oracle.implementation = replace_wrapper_code(route_rmap_validity_oracle.implementation, prefix_list_validity_oracle.implementation, route_rmap_validity_oracle.function_declares[0])
    # route_rmap_validity_oracle.implementation = replace_wrapper_code(route_rmap_validity_oracle.implementation, route_validity_oracle.implementation, route_rmap_validity_oracle.function_declares[1])
    # input_validity_oracle.implementation = replace_wrapper_code(input_validity_oracle.implementation, route_rmap_validity_oracle.implementation, input_validity_oracle.function_declares[0])
    # input_validity_oracle.implementation = replace_wrapper_code(input_validity_oracle.implementation, rr_validity_oracle.implementation, input_validity_oracle.function_declares[1])
    
    # prefix_list_entry_match_oracle = run_wrapper_model(prefix_list_entry_match_model, [prefix_length_to_subnet_mask_model])
    # prefix_list_entry_match_code = remove_function_declaration(prefix_list_entry_match_oracle.implementation, prefix_list_entry_match_oracle.function_declares[0])
    
    # rmap_match_oracle = run_wrapper_model(rmap_match_model, [prefix_list_entry_match_model])
    # rmap_match_code = replace_wrapper_code(rmap_match_oracle.implementation, prefix_list_entry_match_code, rmap_match_oracle.function_declares[0])

    # rr_oracle = run_wrapper_model(rr_model, [rmap_match_model], [input_validity_model], partial=False)
    # rr_code = replace_wrapper_code(rr_oracle.implementation, rmap_match_code, rr_oracle.function_declares[0])
    # rr_code = insert_into_wrapper_code(rr_code, input_validity_code)
    # rr_oracle.implementation = rr_code
    
    g = DependencyGraph()
    g.Edge(prefix_length_to_subnet_mask_model, prefix_list_validity_model)
    g.Edge(prefix_length_to_subnet_mask_model, route_validity_model)
    g.Edge(prefix_list_validity_model, route_rmap_validity_model)
    g.Edge(route_validity_model, route_rmap_validity_model)
    g.Edge(route_rmap_validity_model, input_validity_model)
    g.Edge(rr_validity_model, input_validity_model)
    g.Edge(prefix_list_entry_match_model, rmap_match_model)
    g.Edge(rmap_match_model, rr_model)
    g.Edge(prefix_length_to_subnet_mask_model, prefix_list_entry_match_model)
    
    final_oracle = g.synthesize(filter_functions=[input_validity_model])

    with open("rr1_rmap.c", "w") as f:
        f.write(final_oracle.implementation)

    inputs = final_oracle.get_inputs(timeout_sec=300)
    
    count = 0
    input_list = []
    for input in inputs:
        count += 1
        input_list.append(input)
    print(input_list)
    
    with open('rr1_rmap_test_cases.json', 'w') as f:
        json.dump(input_list, f, indent=4)
        
    # count = len(set(input_list))
    print("Total number of test cases:", count)
    
    return final_oracle.count_lines()
    
     
# MAIN: generate test cases

def unique_test_cases(test_cases):
    unique_test_cases = []
    for test_case in test_cases:
        if test_case not in unique_test_cases:
            unique_test_cases.append(test_case)
    return unique_test_cases

n_iter = 10

all_tests = []
num_lines = []

for i in range(n_iter):
    print("@@@ Test Generation Iteration:", i+1)

    while True:
        try:
            lines = test_rr_rmap()
            num_lines.append(lines)
            break
        except Exception as e:
            print("Exception:", e)
            continue

    with open('rr1_rmap_test_cases.json', 'r') as f:
        data = json.load(f)
        all_tests += data
    
## save all tests
with open('rr1_rmap_all_test_cases.json', 'w') as f:
    json.dump(all_tests, f, indent=4)

            
print("Number of lines of code:", num_lines)
print("Number of test cases:", len(unique_test_cases(all_tests)))  







    