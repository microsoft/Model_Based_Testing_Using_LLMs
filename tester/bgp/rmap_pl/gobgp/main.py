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
parser.add_argument("--start_id", type=int, default=0,
                    help="Starting test ID (default: 0)")
args = parser.parse_args()

results_file = "results.json"

## Reading Test Cases
print_colored(f"\nReading test cases from {args.test_file_path}...\n", "cyan")
with open(args.test_file_path, "r") as f:
    test_cases = json.load(f)

## Create empty results file
with open(results_file, "w") as f:
    json.dump([], f)

for i, t in enumerate(test_cases):
    test_id = args.start_id + i
    print_colored(f"\n\n@@@Running [Test Case {test_id} on GoBGP] from {args.test_file_path}...\n\n", "blue")

    try:
        ## Parse Test Case
        route = t["route"]
        rmap = t["rmap"]

        ## Update Configs
        update_exabgp_config(route)
        update_gobgp_config(rmap)

        os.system(f"bash run.sh")

        ### Parse RIBs ###
        isRIB2 = parse_rib("router2_RIB.txt")
        
        ### Save Results ###
        with open(results_file, "r") as f:
            results = json.load(f)
        
        result_entry = {
            "test_id": test_id,
            "test_case": t,
            "result": {
                "isRIB2": isRIB2
            }
        }
        
        results.append(result_entry)
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
    except:
        continue
