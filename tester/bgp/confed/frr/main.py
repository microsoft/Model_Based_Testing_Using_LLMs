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

for i, test_case in enumerate(test_cases):
    test_id = args.start_id + i
    print_colored(f"\n\n@@@Running [Test Case {test_id} on FRR] from {args.test_file_path}...\n\n", "green")
    
    try:
        ## Parse Test Case
        parsed_params = parse_test_case(test_case)
        orig_as, r2_lp, r2_config, r3_config, remove_private_as_2, replace_as_2, is_ext_peer_3 = parsed_params

        ## Update Configs
        update_exabgp_config(orig_as, r2_config["asNumber"])
        update_frr2_config(r2_config, orig_as, r3_config, remove_private_as_2, replace_as_2, r2_lp)
        update_frr3_config(r3_config, r2_config, is_ext_peer_3)

        os.system("bash run.sh")

        ### Parse RIBs ###
        isRIB2, aspath2, lp2 = parse_rib("router2_RIB.txt")
        isRIB3, aspath3, lp3 = parse_rib("router3_RIB.txt")


        ### Save Results ###
        with open(results_file, "r") as f:
            results = json.load(f)
        
        result_entry = {
            "test_id": test_id,
            "test_case": test_case,
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
    


