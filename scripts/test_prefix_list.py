import eywa
import eywa.ast as ast
import eywa.regex as re
import eywa.oracles as oracles
from termcolor import colored
import json
from eywa.composer import DependencyGraph

def test_route_map_composition():
    route = ast.Struct(
        "Route",
        ipaddr = ast.Int(32),
        maskLength = ast.Int(32)
    )
    
    pr_list_entry = ast.Struct(
        "PrefixListEntry",
        ipaddr = ast.Int(32),
        maskLength = ast.Int(32),
        le = ast.Int(32),
        ge = ast.Int(32),
        any = ast.Bool(),
        permit = ast.Bool()
    )
    
    pr_list = ast.Array(pr_list_entry, 2)
    
    rmap_stanza = ast.Struct(
        "RouteMapStanza",
        prefix_list = pr_list,
        permit = ast.Bool()
    )
    
    p0 = ast.Parameter("prefix_list", pr_list, "The prefix list")
    p0a = ast.Parameter("pfe", pr_list_entry, "The prefix list entry")
    p1 = ast.Parameter("rmap_stanza", rmap_stanza, "A route-map stanza containing a prefix list match condition")
    p2 = ast.Parameter("route", route, "The route advertisement")
    p3 = ast.Parameter("result", ast.Bool(), "A boolean value indicating whether the route is permitted or denied")
    
    p4 = ast.Parameter("validRoute", ast.Bool(), "True if the BGP route advertisement is valid, false otherwise")
    p5 = ast.Parameter("validPrefixList", ast.Bool(), "True if the prefix list is valid, false otherwise.")
    p6 = ast.Parameter("isValidInput", ast.Bool(), "True if both the route-map stanza and BGP route advertisement are valid, false otherwise")
    
    p7 = ast.Parameter("maskLength", ast.Int(32), "The length of the prefix")
    p8 = ast.Parameter("subnetMask", ast.Int(32), "The unsinged integer representation of the prefix length")
    p9 = ast.Parameter("isMatch", ast.Bool(), "True if the route-map stanza permits the route, otherwise false")
    
    prefix_length_to_subnet_mask_model = ast.Function(
        "prefixLenToSubnetMask",
        "a function that takes as input the prefix length and converts it to the corresponding unsigned integer representation",
        [p7, p8]
    )
    
    route_validity_model =  ast.Function(
        "isValidRoute",
        """A function that checks whether the BGP route advertisement has a valid prefix list and mask length.
Conditions for valiidity:
    1. The IPv4 address should be in the range 1671377732 - 1679687938.
    2. The subnet mask length must be in the range 0-32.
    3. The prefix value should be greater than 0 i.e (ipaddr & subnet_mask) > 0.""",
        [p2, p4]
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
        [p0, p5]
    )
    
    valid_input_model = ast.Function(
        "checkValidInputs",
        """A function that takes as input a route-map stanza and a BGP route advertisement and checks whether:
    1. The prefix list defined within the route-map stanza is valid.
    2. The BGP route advertisment is valid.""",
        [p1, p2, p6]
    )

    prefix_list_entry_match_model = ast.Function(
        "isMatchPrefixListEntry",
        """A function that takes as input a prefix list entry and a BGP route advertisement. If the route advertisement matches one of the prefixes in the list, then the function should return the value of the permit flag corresponding to that prefix. In case there is no match, the function should vacuously return false.""",
        [p0a, p2, p3]
    )
    
    rmap_match_model = ast.Function(
        "matchAgainstRouteMapStanza",
        """A function that takes as input a route-map stanza and a BGP route-advertisement. The stanza has a match clause
that matches routes against a given prefix-list. If the match condition fails, then it vacuously evaluates to false.""",
        [p1, p2, p9]
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
    
    g = DependencyGraph()
    
    g.CallEdge(prefix_list_validity_model, [prefix_length_to_subnet_mask_model])
    g.CallEdge(route_validity_model, [prefix_length_to_subnet_mask_model])
    g.CallEdge(valid_input_model, [prefix_list_validity_model, route_validity_model])
    g.CallEdge(prefix_list_entry_match_model, [prefix_length_to_subnet_mask_model])
    g.CallEdge(rmap_match_model, [prefix_list_entry_match_model])
    
    g.Pipe(rmap_match_model, valid_input_model)
    
    final_oracle = g.synthesize()
            
    with open('rmap_match_code_full.c', 'w') as f:
        f.write(final_oracle.implementation)
        
    inputs = final_oracle.get_inputs(timeout_sec=300)
    count = 0
    for input in inputs:
        count += 1
        print(input)
        
    with open('rmap_test_cases.json', 'w') as f:
        json.dump(inputs, f, indent=4)
        
    print("Total number of test cases:", count)
    
    return final_oracle.count_lines()

def unique_test_cases(all_tests):
    unique_tests = []
    for test in all_tests:
        if test not in unique_tests:
            unique_tests.append(test)
    return unique_tests
    
if __name__ == '__main__':
    num_lines = []
    all_tests = []
    
    for i in range(1):
        lines = test_route_map_composition()
        num_lines.append(lines)
        with open('rmap_test_cases.json') as f:
            data = json.load(f)
            all_tests += data
            
    print("Number of lines of code:", num_lines)
    print("Number of test cases:", len(unique_test_cases(all_tests)))