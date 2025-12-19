## add "eywa" to the path
import sys
sys.path.append("..")
import json

import eywa
import eywa.ast as ast
import eywa.regex as re
import eywa.oracles as oracles
from termcolor import colored
import json
import os
from eywa.composer import DependencyGraph

def test_confed():
    
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
    # router_validity_oracle = run_wrapper_model(router_validity_model)
    # valid_input_oracle = run_wrapper_model(valid_input_model, [router_validity_model])
    # valid_input_oracle.replace_function_prototype(router_validity_oracle.implementation, valid_input_oracle.function_declares[0])
    
    # confederation_oracle = run_wrapper_model(confederation_model, filter_functions=[valid_input_model], partial=False)
    # confederation_oracle.insert_function_code(valid_input_oracle.implementation)
    
    composer = DependencyGraph()
    composer.Edge(router_validity_model, valid_input_model)
    composer.Node(confederation_model)
    final_oracle = composer.synthesize(filter_functions=[valid_input_model])
    
    with open("confederation.c", "w") as f:
        f.write(final_oracle.implementation)
    
    inputs = final_oracle.get_inputs(timeout_sec=300)
    
    count = 0
    input_list = []
    for input in inputs:
        count += 1
        print(input)
        input_list.append(input)
        
    with open('test_cases2.json', 'w') as f:
        json.dump(input_list, f, indent=4)
        
    print("Total number of test cases:", count)
    
    return final_oracle.count_lines()
    
     
# test_confed()
def unique_test_cases(all_tests):
    unique_tests = []
    for test in all_tests:
        if test not in unique_tests:
            unique_tests.append(test)
    return unique_tests

all_tests = []
num_lines = []
for i in range(10):
    print("@@@ Test Generation Iteration:", i+1)
    lines = test_confed()
    num_lines.append(lines)
    with open('test_cases2.json') as f:
        data = json.load(f)
        all_tests += data
    
## save all tests
with open('all_test_cases.json', 'w') as f:
    json.dump(all_tests, f, indent=4)

            
print("Number of lines of code:", num_lines)
print("Number of test cases:", len(unique_test_cases(all_tests)))  
    






