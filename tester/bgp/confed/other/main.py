import json
import argparse
from bgp_confed import simulate_bgp_confederation

parser = argparse.ArgumentParser()
parser.add_argument("--test_file_path", type=str, required=True,
                    help="Path to the test file")
parser.add_argument("--start_id", type=int, default=0,
                    help="Starting test ID (default: 0)")
args = parser.parse_args()

results_file = "results.json"

## Reading Test Cases
print(f"\nReading test cases from {args.test_file_path}...\n")
with open(args.test_file_path, "r") as f:
    test_cases = json.load(f)

## Create empty results file
with open(results_file, "w") as f:
    json.dump([], f)

for i, test_case in enumerate(test_cases):
    test_id = args.start_id + i
    print(f"\n\n@@@Running [Test Case {test_id} on Manual Implementation]...\n\n")
    
    try:
        ## Run simulation
        result = simulate_bgp_confederation(test_case)

        ### Save Results ###
        with open(results_file, "r") as f:
            results = json.load(f)
        
        result_entry = {
            "test_id": test_id,
            "test_case": test_case,
            "result": {
                "isRIB2": result["isRIB2"],
                "aspath2": result["aspath2"],
                "isRIB3": result["isRIB3"],
                "aspath3": result["aspath3"]
            }
        }

        results.append(result_entry)
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
    except Exception as e:
        print(f"Error processing test case {test_id}: {e}")
        continue

print(f"\nProcessed {len(test_cases)} test cases. Results saved to {results_file}")
