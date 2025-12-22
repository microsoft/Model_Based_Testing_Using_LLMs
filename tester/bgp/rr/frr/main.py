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
    parsed_params = parse_test_case(test_case)
    inRRflag, outRRflag, inAS, outAS = parsed_params
    as2 = 200; 
    as1 = as2 if inAS else 100
    as3 = as2 if outAS else 300

    ## Update Configs
    update_router1_config(as1, as2, inRRflag)
    update_router2_config(as2, as1, as3, inRRflag, outRRflag)
    update_router3_config(as3, as2, outRRflag)

    os.system("bash run.sh")

    ### Parse RIBs ###
    isRIB2 = parse_rib("router2_RIB.txt")
    isRIB3 = parse_rib("router3_RIB.txt")


    ### Save Results ###
    with open(results_file, "r") as f:
        results = json.load(f)
    
    result_entry = {
        "test_id": test_id,
        "test_case": test_case,
        "result": {
            "isRIB2": isRIB2,
            "isRIB3": isRIB3
        }
    }

    results.append(result_entry)
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    


