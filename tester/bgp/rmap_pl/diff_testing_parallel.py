import os
import subprocess
import argparse
import json
import time

############# Paths #############
test_dir = "../../../tests/bgp/NSDI/RMAP_PL"
test_file_path = f"{test_dir}/debug_test.json"
results_json_path = f"{test_dir}/results.json"
diff_results_path = f"{test_dir}/diff_results.json"

############# Helpers #############

def diff_test(test_file, results_file, diff_results_file):
    print(f"Running tests from {test_file} ...")
    with open(test_file, 'r') as f: 
        tests = json.load(f)

    # Start all three tests in parallel
    frr_proc = subprocess.run(f"cd frr && python main.py --test_file_path=../{test_file}", shell=True)
    gobgp_proc = subprocess.run(f"cd gobgp && python main.py --test_file_path=../{test_file}", shell=True)
    batfish_proc = subprocess.run(f"cd batfish && python main.py --test_file_path=../{test_file}", shell=True)

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

    assert len(frr_results) == len(gobgp_results) == len(batfish_results), "Results from FRR, GoBGP, and Batfish do not match in length."
    results = []
    diff_results = []
    for i in range(len(frr_results)):
        d = {
            "test_id": i+1,
            "test_case": tests[i],
            "results":{
                "FRR": frr_results[i]["result"],
                "GoBGP": gobgp_results[i]["result"],
                "Batfish": batfish_results[i]["result"]
            },
            "verdict": "PASS" if (frr_results[i]["result"]["isRIB2"] == gobgp_results[i]["result"]["isRIB2"] == batfish_results[i]["result"]["isRIB2"]) else "FAIL"
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
    

    # 🔀 Run diff test
    diff_test(test_file_path, results_json_path, diff_results_path)
    print(f" ✨ Diff Testing results updated. ✨")




