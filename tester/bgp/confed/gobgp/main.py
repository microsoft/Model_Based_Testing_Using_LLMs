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

        # write_config(t[0], t[1], t[2], t[3], t[4], t[5])
        write_config(t["originAS"], t["router2"], t["router3"], t["removePrivateAS"], t["replaceAS"], t["localPref"])
        os.system('bash run.sh')
        isRIB2, aspath2 = get_as_path("router2_RIB.txt")
        isRIB3, aspath3 = get_as_path("router3_RIB.txt")
        
        ### Save Results ###
        with open(results_file, "r") as f:
            results = json.load(f)
        
        result_entry = {
            "test_id": test_id,
            "test_case": t,
            "result": {
                "isRIB2": isRIB2,
                "aspath2": aspath2,
                "isRIB3": isRIB3,
                "aspath3": aspath3
            }
        }
        
        results.append(result_entry)
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
    except:
        continue
