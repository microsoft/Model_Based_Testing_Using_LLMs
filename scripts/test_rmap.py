import eywa
import eywa.ast as ast
import eywa.composer
import eywa.regex as re
import eywa.oracles as oracles
from eywa.composer import DependencyGraph

def test_rmap(test_gen=True):
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
        nextHop = ast.Int(32),
        localPref = ast.Int(32),
        community = ast.Array(ast.Int(32), 1),
        med = ast.Int(32)
    )
    
    pr_list = ast.Array(pr_list_entry, 2)
    
    rmap_stanza = ast.Struct(
        "RouteMapStanza",
        matchPrefixList = pr_list,
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
    
    p0 = ast.Parameter("route", route, "Route to be matched")
    p1 = ast.Parameter("routeMap", rmap, "Route map to be applied")
    p2 = ast.Parameter("result", result, "Result of applying route map on route")
    p3 = ast.Parameter("void_res", ast.Void(), "")
    
    
    p4 = ast.Parameter("maskLength", ast.Int(32), "The length of the prefix")
    p5 = ast.Parameter("subnetMask", ast.Int(32), "The unsinged integer representation of the prefix length")
    p6 = ast.Parameter("pfe", pr_list_entry, "Prefix list entry")
    p7 = ast.Parameter("pr_match", ast.Bool(), "True if the route matches the prefix list entry")
    
    p8 = ast.Parameter("prefixList", pr_list, "Prefix list")
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
    5. The MED value should be in the range [20, 50].
    6. The next hop value should be in the range 1671377732 - 1679687938.
    7. The community value should be 0.""",
        [p0, p10]
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
        [p8, p9]
    )
    
    valid_input_model = ast.Function(
        "checkValidInputs",
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
    [p0, p1, p11]
    )
    
    rmap_match_model = ast.Function(
        "isMatchRouteMap",
        """A function that takes as input a BGP route advertisement and a route map. It checks whether the route advertisement matches any of the stanzas in the route map.
If a match is found, the function should update a struct with the output route advertisement and a boolean value indicating whether the route is permitted by the route map. In case
of a successful match, the function should modify the output route according to the set statements in the stanza. If no 
match is found, the function should set the isPermitted flag in Result struct to false and the attributes of the route should be set to zero.""",
        [p0, p1, p2, p3]
    )
    
    # valid_input_oracle = run_wrapper_model(valid_input_model, [prefix_list_validity_model, route_validity_model])
    # prefix_list_validity_oracle = run_wrapper_model(prefix_list_validity_model,[prefix_length_to_subnet_mask_model])
    # route_validity_oracle = run_wrapper_model(route_validity_model, [prefix_length_to_subnet_mask_model])
    
    # prefix_length_to_subnet_mask_oracle = run_wrapper_model(prefix_length_to_subnet_mask_model)
    
    # prefix_list_validity_code = replace_wrapper_code(prefix_list_validity_oracle.implementation, prefix_length_to_subnet_mask_oracle.implementation, prefix_list_validity_oracle.function_declares[0])
    # route_validity_code = remove_function_declaration(route_validity_oracle.implementation, route_validity_oracle.function_declares[0])
    
    # valid_input_code = replace_wrapper_code(valid_input_oracle.implementation, prefix_list_validity_code, valid_input_oracle.function_declares[0])
    # valid_input_code = replace_wrapper_code(valid_input_code, route_validity_code, valid_input_oracle.function_declares[1])
    
    # prefix_list_entry_match_oracle = run_wrapper_model(prefix_list_entry_match_model, [prefix_length_to_subnet_mask_model])
    # prefix_list_entry_match_code = remove_function_declaration(prefix_list_entry_match_oracle.implementation, prefix_list_entry_match_oracle.function_declares[0])
    
    # rmap_match_oracle = run_wrapper_model(rmap_match_model, [prefix_list_entry_match_model], [valid_input_model], partial=False)
    # rmap_match_code = replace_wrapper_code(rmap_match_oracle.implementation, prefix_list_entry_match_code, rmap_match_oracle.function_declares[0])
    
    # rmap_match_code = insert_into_wrapper_code(rmap_match_code, valid_input_code)
    
    # rmap_match_oracle.implementation = rmap_match_code
    
    composer = DependencyGraph()
    composer.Edge(prefix_length_to_subnet_mask_model, prefix_list_validity_model)
    composer.Edge(prefix_length_to_subnet_mask_model, route_validity_model)
    composer.Edge(prefix_list_validity_model, valid_input_model)
    composer.Edge(route_validity_model, valid_input_model)
    composer.Edge(prefix_length_to_subnet_mask_model, prefix_list_entry_match_model)
    composer.Edge(prefix_list_entry_match_model, rmap_match_model)
    
    final_oracle = composer.synthesize(filter_functions=[valid_input_model])
    
    with open('rmap_match_code_full.c', 'w') as f:
        f.write(final_oracle.implementation)
        
    if test_gen:
        inputs = final_oracle.get_inputs(timeout_sec=300)
        count = 0
        for input in inputs:
            count += 1
            print(input)
            
        print("Total number of test cases:", count)

    return (p0, p1, rmap_match_model, valid_input_model, final_oracle.implementation)

     
if __name__ == "__main__":
    result = test_rmap()