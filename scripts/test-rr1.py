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
    # router_validity_oracle = run_wrapper_model(router_validity_model)
    # rr_oracle = run_wrapper_model(rr_model, filter_functions=[router_validity_oracle], partial=False)
    # rr_oracle.insert_function_code(router_validity_oracle.implementation)
    
    composer = DependencyGraph()
    composer.Node(router_validity_model)
    composer.Node(rr_model)
    rr_oracle = composer.synthesize(filter_functions=[router_validity_model])
    
    with open("rr1.c", "w") as f:
        f.write(rr_oracle.implementation)
    
    inputs = rr_oracle.get_inputs(timeout_sec=300)
    
    count = 0
    input_list = []
    for input in inputs:
        count += 1
        print(input)
        input_list.append(input)
        
    with open('rr1_test_cases.json', 'w') as f:
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

    with open('rr1_test_cases.json') as f:
        data = json.load(f)
        all_tests += data
    
## save all tests
with open('rr1_all_test_cases.json', 'w') as f:
    json.dump(all_tests, f, indent=4)

            
print("Number of lines of code:", num_lines)
print("Number of test cases:", len(unique_test_cases(all_tests)))






