import json
from utils import *
import os
import argparse
import sys

## Take the test file as argument
## Usage: python3 main.py <test_file>
## Example: python3 main.py tests/tests_general.json

parser = argparse.ArgumentParser()
parser.add_argument("--test_file_path", type=str, required=True,
                    help="Path to the test file")
args = parser.parse_args()

results_file = "results.json"

## Reading Test Cases
print_colored(f"\nReading test cases from {args.test_file_path}...\n", "cyan")
with open(args.test_file_path, "r") as f:
    test_cases = json.load(f)

## Create empty results file
with open(results_file, "w") as f:
    json.dump([], f)

test_id = 0
for test_case in test_cases:

    test_id = test_id + 1
    print_colored(f"\n\n@@@Running [Test Case {test_id} on FRR] from {args.test_file_path}...\n\n", "green")
    
    ## Parse Test Case
    route = test_case["route"]
    rmap = test_case["rmap"]
    route_prefix = route["prefix"]

    ## Update Configs
    update_exabgp_config(route)
    update_frr_config(rmap)

    os.system(f"bash run.sh {route_prefix}")

    ### Parse RIBs ###
    isRIB2 = parse_rib("router2_RIB.txt")

    ### Save Results ###
    with open(results_file, "r") as f:
        results = json.load(f)
    
    result_entry = {
        "test_id": test_id,
        "test_case": test_case,
        "result": {
            "isRIB2": isRIB2,
        }
    }

    results.append(result_entry)
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    


