import os
import argparse
import json
import subprocess
import sys
from pathlib import Path

## ========= Helpers ========= ##
def print_colored(text, color):
    colors = {
        "black": "\033[30m",
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "reset": "\033[0m"
    }
    color_code = colors.get(color.lower(), colors["reset"])
    print(f"{color_code}{text}{colors['reset']}")

def append_result(results_file, result_entry):
    with open(results_file, "r") as f:
        results = json.load(f)
    results.append(result_entry)
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

## Current directory
current_file = Path(__file__).resolve()
current_dir = current_file.parent

## Taking Test file path as Command line argument 
parser = argparse.ArgumentParser()
parser.add_argument("--test_file_path", type=str, required=True,
                    help="Path to the test file")
args = parser.parse_args()

results_file = "results.json"

## Remove any existing Batfish container
print("Killing Existing Batfish Container...")
# subprocess.run("kill -9 $(ps aux | grep batfish | grep -v grep | awk '{print $2}')", shell=True)
subprocess.run("docker stop batfish", shell=True)
subprocess.run("docker rm batfish", shell=True)
print("Batfish Container stopped and removed.")

## Start the Container, 
subprocess.run(
    f"docker run -d --name batfish -v batfish-data:/data -v {current_dir}/testing:/notebooks/testing/ -p 8888:8888 -p 9997:9997 -p 9996:9996 batfish/allinone",
    shell=True)

print("New Batfish Container Started...")

## Read the tests from given path
print_colored(f"\nReading test cases from {args.test_file_path}...\n", "cyan")
with open(args.test_file_path, "r") as f:
    test_cases = json.load(f)

print("Test cases loaded from:", args.test_file_path)

## Create empty results file
with open(results_file, "w") as f:
    json.dump([], f)

print("Results file created: results.json")

## Iterate through each test case
print("Iterating over tests...")
test_id = 0
for test_id, test_case in enumerate(test_cases, start=1):
    # populate testing/test.json
    print("****************************************\n")
    print_colored(f"\n\n@@@Running [Test Case {test_id} on Batfish] from {args.test_file_path}...\n\n", "yellow")
    print("importing test case with id:", test_id)
    with open("testing/test.json", "w") as f:
        json.dump(test_case, f, indent=2)
    print("Test case imported.")

    # Run the Batfish Test
    print("Running Batfish test...")
    # os.system('docker exec -t batfish bash -c "cd notebooks/testing && python3 test.py"')

    try:
        subprocess.run(
            'docker exec -t batfish bash -c "cd notebooks/testing && python3 test.py"',
            shell=True,
            check=True,
            timeout=30
        )
    except subprocess.TimeoutExpired:
        print("❌ Batfish test timed out after 30 seconds.")
        append_result(results_file, {"isRIB2": False, "isRIB3": False})
        continue  # go to next test
    except subprocess.CalledProcessError as e:
        print(f"❌ Batfish test failed: {e}")
        append_result(results_file, {"isRIB2": False, "isRIB3": False})
        continue
    print("Batfish test completed.")

    # Save successful test result 
    print("Saving test result...")
    with open("testing/result.json", "r") as f:
        result = json.load(f)
    append_result(results_file, {"result": result})
    print("Test result saved.")


# Stop the Batfish Container
print("Stopping Batfish Container...")
# subprocess.run("kill -9 $(ps aux | grep batfish | grep -v grep  | awk '{print $2}')", shell=True)
subprocess.run("docker stop batfish", shell=True)
subprocess.run("docker rm batfish", shell=True)
print("Batfish Container stopped and removed.")



