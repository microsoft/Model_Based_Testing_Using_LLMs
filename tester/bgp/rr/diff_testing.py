import os
import subprocess
import argparse
import json
import time

############# Paths #############
test_dir = "../../../tests/bgp/NSDI/RR"
test_file_path = f"{test_dir}/tests.json"
results_json_path = f"{test_dir}/results.json"
diff_results_path = f"{test_dir}/diff_results.json"

############# Helpers #############

def isPassed(result_list):
    isRIB2_ref = result_list[0]["result"]["isRIB2"]
    isRIB3_ref = result_list[0]["result"]["isRIB3"]

    for result in result_list:
        if result["result"]["isRIB2"] != isRIB2_ref:
            return False
        if result["result"]["isRIB3"] != isRIB3_ref:
            return False
    return True

def diff_test(test_file, results_file, diff_results_file, start=None, end=None):
    print(f"Running tests from {test_file} ...")
    with open(test_file, 'r') as f: 
        tests = json.load(f)
    
    # Filter tests by range if specified and create filtered test file
    filtered_test_file = test_file
    if start is not None and end is not None:
        filtered_tests = tests[start:end+1]
        test_dir = os.path.dirname(test_file)
        filtered_test_file = os.path.join(test_dir, "tests_in_range.json")
        with open(filtered_test_file, 'w') as f:
            json.dump(filtered_tests, f, indent=2)
        tests = filtered_tests
    else:
        tests = tests

    # Build command suffix for start_id if specified
    start_id_arg = f" --start_id {start}" if start is not None else ""

    # Start all three tests
    frr_proc = subprocess.run(f"cd frr && python main.py --test_file_path=../{filtered_test_file}{start_id_arg}", shell=True)
    gobgp_proc = subprocess.run(f"cd gobgp && python main.py --test_file_path=../{filtered_test_file}{start_id_arg}", shell=True)
    batfish_proc = subprocess.run(f"cd batfish && python main.py --test_file_path=../{filtered_test_file}{start_id_arg}", shell=True)

    # Wait for all to complete
    # frr_proc.wait()
    # print(f"Tests on FRR from {test_file} completed.")
    # gobgp_proc.wait()
    # print(f"Tests on GoBGP from {test_file} completed.")
    # batfish_proc.wait()
    # print(f"Tests on Batfish from {test_file} completed.")

    with open("frr/results.json", "r") as f:
        frr_results = json.load(f)
    with open("gobgp/results.json", "r") as f:
        gobgp_results = json.load(f)
    with open(f"batfish/results.json", "r") as f:
        batfish_results = json.load(f)

    # Convert results lists to dictionaries keyed by test_id
    frr_dict = {r["test_id"]: r for r in frr_results}
    gobgp_dict = {r["test_id"]: r for r in gobgp_results}
    batfish_dict = {r["test_id"]: r for r in batfish_results}

    # Get test_ids that have results from ALL implementations
    common_test_ids = set(frr_dict.keys()) & set(gobgp_dict.keys()) & set(batfish_dict.keys())

    # Build test_case lookup from original tests
    test_lookup = {}
    start_idx = start if start is not None else 0
    for i, t in enumerate(tests):
        test_lookup[start_idx + i] = t

    results = []
    diff_results = []
    for test_id in sorted(common_test_ids):
        frr_res = frr_dict[test_id]
        gobgp_res = gobgp_dict[test_id]
        batfish_res = batfish_dict[test_id]
        
        d = {
            "test_id": test_id,
            "test_case": test_lookup.get(test_id, frr_res.get("test_case", {})),
            "results":{
                "FRR": frr_res["result"],
                "GoBGP": gobgp_res["result"],
                "Batfish": batfish_res["result"]
            },
            "verdict": "PASS" if isPassed([frr_res, gobgp_res, batfish_res]) else "FAIL"
        }
        results.append(d)
        if d["verdict"] == "FAIL":
            diff_results.append(d)

    with open(results_file, 'w') as f: json.dump(results, f, indent=2)
    print(f"Results from {test_file} saved to {results_file}.")

    with open(diff_results_file, 'w') as f: json.dump(diff_results, f, indent=2)
    print(f"Diff results from {test_file} saved to {diff_results_file}.")
    
    
############### Main ###############

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run differential testing on BGP implementations.')
    parser.add_argument('-r', nargs=2, type=int, metavar=('START', 'END'),
                        help='Range of test cases to run (START END, inclusive). If not provided, all tests are run.')
    args = parser.parse_args()
    
    start = None
    end = None
    if args.r:
        start, end = args.r[0], args.r[1]

    # 🔀 Run diff test
    diff_test(test_file_path, results_json_path, diff_results_path, start=start, end=end)
    print(f" ✨ Diff Testing results updated. ✨")




