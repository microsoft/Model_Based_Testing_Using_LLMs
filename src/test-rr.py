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

def test_rr():
    
    """
    
    R1 ----------------- R2 ----------------- R3
    
    """
    
    outputRIB = ast.Struct(
        "outputRIB",
        isReceivedR2 = ast.Bool(),
        isReceivedR3 = ast.Bool()
    )

    p1r = ast.Parameter("router1RR", ast.Bool(), "True if router 1 is a route reflector to router 2")
    p1c = ast.Parameter("router1Client", ast.Bool(), "True if router 1 is a client to router 2")
    p1a = ast.Parameter("router1AS", ast.Int(32), "AS number of router 1")

    p21r = ast.Parameter("router2RR1", ast.Bool(), "True if router 2 is a route reflector to router 1")
    p21c = ast.Parameter("router2Client1", ast.Bool(), "True if router 2 is a client to router 1")
    p23r = ast.Parameter("router2RR3", ast.Bool(), "True if router 2 is a route reflector to router 3")
    p23c = ast.Parameter("router2Client3", ast.Bool(), "True if router 2 is a client to router 3")
    p2a = ast.Parameter("router2AS", ast.Int(32), "AS number of router 2")

    p3r = ast.Parameter("router3RR", ast.Bool(), "True if router 3 is a route reflector to router 2")
    p3c = ast.Parameter("router3Client", ast.Bool(), "True if router 3 is a client to router 2")    
    p3a = ast.Parameter("router3AS", ast.Int(32), "AS number of router 3")

    p_valid = ast.Parameter("isValidConfiguration", ast.Bool(), "True if the all three router configurations (router 1, 2 and 3) are valid, false otherwise")
    
    p_rib = ast.Parameter("finalRIB", outputRIB, "a struct containing two boolean values indicating whether the route is received at router 2 and router 3.")
    p_void = ast.Parameter("void_res", ast.Void(), "")
    
    router_validity_model = ast.Function(
        "checkValidRouterConfiguration",
        """A function that takes as input the flags and AS numbers for three routers, and returns True if all of them are valid, false otherwise.
Conditions for validitity:
1. AS number of all routers should be in the range [50, 65535] both inclusive.
2. Check for the following cases for flags:
    a. if p1r is true, then p1c should be false, and p21r should be false, p21c should be true.
    b. if p21r is true, then p21c should be false, and p1r should be false, p1c should be true.
    c. if p23r is true, then p23c should be false, and p3r should be false, p3c should be true.
    d. if p3r is true, then p3c should be false, and p23r should be false, p23c should be true.

3. Check for the following cases for AS numbers: 
    a. Router 1, 2, 3 has all different AS numbers.
    b. Any two of them (r1,r2 or r2,r3 or r3,r1) have same AS number.
    c. All of them have same AS number.""",
        [p1a, p2a, p3a, p1r, p1c, p21r, p21c, p23r, p23c, p3r, p3c, p_valid]
    )
    
    rr_model = ast.Function(
        "predictRouteReflectorRibs",
        """A function that takes as input the flags and AS numbers of router 1, router 2 and router 3 and updates a struct with two booleans isReceivedR2 (true if route received by router 2) and isReceivedR3 (true if route received by router 3).
Router 1, Router 2 and Router 3 are connected in series and the route is advertised to router 2 first from router 1, which then forwards it to router 3 if permitted by BGP route reflection rules. You have to take into consideration all BGP route reflector rules, eBGP, iBGP rules. i.e.
1. A route learned from a non-RR client is advertised to RR clients but not to non-RR clients.
2. A route learned from an RR client is advertised to both RR clients and non-RR clients. Even the RR client that advertised the route will receive a copy and discard it because it sees itself as the originator.
3. A route learned from an EBGP neighbor is advertised to both RR clients and non-RR clients.

AS numbers of router 1, router 2 and router 3 can be anything.

The topology is as follows: 

                        R1 ----------------- R2 ----------------- R3
                        
Consider the following cases in your code:
1. Router 1, 2, 3 has all different AS numbers.
2. Any two of them (r1,r2 or r2,r3 or r3,r1) have same AS number.
3. All of them have same AS number.
4. For each of the above cases consider all possible combinations (True/False) of all the router flags. i.e. what happens if router 1 is a route reflector to router 2, router 2 is a route reflector to router 3; router 2 is a client to router 1, router 2 is a client to router 3 etc. Add separate branches for each of these cases.""",
        [p1a, p2a, p3a, p1r, p1c, p21r, p21c, p23r, p23c, p3r, p3c, p_rib, p_void]
    )
    # router_validity_oracle = run_wrapper_model(router_validity_model)
    
    # rr_oracle = run_wrapper_model(rr_model, filter_functions=[router_validity_oracle], partial=False)
    # rr_oracle.insert_function_code(router_validity_oracle.implementation)
    
    composer = DependencyGraph()
    composer.Node(router_validity_model)
    composer.Node(rr_model)
    rr_oracle = composer.synthesize(filter_functions=[router_validity_model])
        
    with open("rr.c", "w") as f:
        f.write(rr_oracle.implementation)
    
    inputs = rr_oracle.get_inputs(timeout_sec=300)
    
    count = 0
    input_list = []
    for input in inputs:
        count += 1
        print(input)
        input_list.append(input)
        
    with open('rr_test_cases.json', 'w') as f:
        json.dump(input_list, f, indent=4)
        
    print("Total number of test cases:", count)
    
    return rr_oracle.count_lines()
    
     
## generate test cases

def unique_test_cases(all_tests):
    unique_tests = []
    for test in all_tests:
        if test not in unique_tests:
            unique_tests.append(test)
    return unique_tests

n_iter = 10

all_tests = []
num_lines = []
for i in range(n_iter):
    print("@@@ Test Generation Iteration:", i+1)

    while True:
        try:
            lines = test_rr()
            num_lines.append(lines)
            break
        except Exception as e:
            print("Exception:", e)
            continue

    with open('rr_test_cases.json') as f:
        data = json.load(f)
        all_tests += data
    
## save all tests
with open('rr_all_test_cases.json', 'w') as f:
    json.dump(all_tests, f, indent=4)
    
print("Number of lines of code:", num_lines)
print("Number of test cases:", len(unique_test_cases(all_tests)))

            
        






