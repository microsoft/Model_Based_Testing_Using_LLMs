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
        ### Parse Test Case ###
        route, rmap, p_inRRflag, p_outRRflag, p_inAS, p_outAS = t["route"], t["rmap"], t["inRRflag"], t["outRRflag"], t["inAS"], t["outAS"]

        exabgp_asnum = 512
        router2_asnum = 200
        router1_asnum = router2_asnum if p_inAS else 100
        router3_asnum = router2_asnum if p_outAS else 300

        if p_inRRflag == 0:
            isRR1 = False
            isClient1 = True
            isRR_router1 = True
            isClient_router1 = False
        elif p_inRRflag == 1:
            isRR1 = True
            isClient1 = False
            isRR_router1 = False
            isClient_router1 = True
        else:
            isRR1 = False
            isClient1 = False
            isRR_router1 = False
            isClient_router1 = False
            
        if p_outRRflag == 0:
            isRR3 = False
            isClient3 = True
            isRR_router3 = True
            isClient_router3 = False
        elif p_outRRflag == 1:
            isRR3 = True
            isClient3 = False
            isRR_router3 = False
            isClient_router3 = True
        else:
            isRR3 = False
            isClient3 = False
            isRR_router3 = False
            isClient_router3 = False

        exabgp = {
            'asNumber': exabgp_asnum
        }
            
        router1 = {
            'asNumber': router1_asnum,
            'isRR': isRR_router1,
            'isClient': isClient_router1
        }

        router2 = {
            'asNumber': router2_asnum,
            'isRR1': isRR1,
            'isClient1': isClient1,
            'isRR3': isRR3,
            'isClient3': isClient3
        }

        router3 = {
            'asNumber': router3_asnum,
            'isRR': isRR_router3,
            'isClient': isClient_router3
        }

        write_config(route, rmap, exabgp, router1, router2, router3)
        os.system('bash run.sh')
        
        isReceivedR2 = False
        isReceivedR3 = False
        
        if os.path.exists('router2_RIB.txt'):
            with open('router2_RIB.txt', 'r') as r2:
                lines = r2.readlines()
                if(len(lines) > 1): isReceivedR2 = True
        
        if os.path.exists('router3_RIB.txt'):
            with open('router3_RIB.txt', 'r') as r3:
                lines = r3.readlines()
                if(len(lines) > 1): isReceivedR3 = True
        

        ### Save Results ###
        with open(results_file, "r") as f:
            results = json.load(f)
        
        result_entry = {
            "test_id": test_id,
            "test_case": t,
            "result": {
                "isRIB2": isReceivedR2,
                "isRIB3": isReceivedR3
            }
        }
        
        results.append(result_entry)
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
    except:
        continue
