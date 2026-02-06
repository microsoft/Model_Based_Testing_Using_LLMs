import json
from ast import literal_eval
import pathlib
from typing import Generator, List, Tuple
import eywa
import eywa.ast as ast
from eywa.llm import GPT4
import eywa.oracles as oracles
import regex as re
import eywa.run as run
from argparse import ArgumentParser
from termcolor import colored
import ipaddress
import re
from pathlib import Path

## GLOBALS
NSDI = False
output_dir_common = pathlib.Path("..//tests//smtp//NSDI")


## HELPERS
def pick_first_implementation(folder: Path) -> Path:
    pat = re.compile(r"implementation_(\d+)_.*\.c")
    candidates = []
    for f in folder.glob("implementation_*.c"):
        m = pat.match(f.name)
        if m:
            candidates.append((int(m.group(1)), f))
    if not candidates:
        raise FileNotFoundError("No implementation_*.c files found")
    return min(candidates, key=lambda x: (x[0], x[1].name))[1]

from collections import deque

def BFS(transition_dict, target_state):
    """
    transition_dict: { (state, input) : next_state }
    target_state: state we want to reach

    Returns: list of inputs (commands), or None if unreachable
    """
    queue = deque()
    queue.append(("INITIAL", []))   # (current_state, input_sequence)
    visited = set(["INITIAL"])

    while queue:
        state, seq = queue.popleft()

        if state == target_state:
            return seq

        for (s, inp), next_state in transition_dict.items():
            if s == state and next_state not in visited:
                visited.add(next_state)
                queue.append((next_state, seq + [inp]))

    return None


def server_check(runs, timeout):
    
    state = ast.Enum("State", ["INITIAL", "HELO_SENT", "EHLO_SENT", "MAIL_FROM_RECEIVED", "RCPT_TO_RECEIVED", "DATA_RECEIVED", "QUITTED"])

    p_input = ast.Parameter("input", ast.String(10), "Input string")

    p_state = ast.Parameter("state", state, "Current state of the SMTP server")

    p_output = ast.Parameter("output", ast.String(50), "Output string")

    smtp_server_model = ast.Function(
        "smtp_server_response",
        """A function that takes the current state of the SMTP server, the input string, updates the state and returns the output string as server response. 
        ** Use if-else instead of switch-case for state transitions.""",
        [p_state, p_input, p_output]
    )

    # smtp_oracle = run_wrapper_model(smtp_server_model, partial=False)
    
    g = eywa.DependencyGraph()
    g.Node(smtp_server_model)

    output_dir = output_dir_common / "SMTP"
    inputs = run(g, k=runs, debug=output_dir, timeout_sec=timeout)

    ## Save the test cases
    test_dir = output_dir
    test_dir.mkdir(exist_ok=True)
    test_cases = []
    for input in inputs:
        state = input[0]
        message = input[1]
        exp_response = input[2]

        test_case = {
            "state": state,
            "message": message,
            "expected_response": exp_response
        }
        test_cases.append(test_case)

    with open(test_dir / 'tests.json', 'w') as f:
        json.dump(test_cases, f, indent=4)

    ## Pick an implementation for state graph generation
    impl = pick_first_implementation(test_dir)
    print(f"\n [+] Picked implementation: {impl} for state transition extraction \n")
    with open(impl, 'r') as f:
        code = f.read()

    ## extract the code between line containing "smtp_server_response" and "int main()"
    start = code.find("smtp_server_response")
    end = code.find("int main()")
    code = code[start:end]

    ## Query GPT4 for state transition dictionary
    print("\n [*] Generating state transition dictionary using GPT4 \n")
    gpt4 = GPT4()
    user_prompt = f"""
    ### Task:
    Create a python dictionary that maps the state transitions: [state,input] --> state for the following C code snippet:

    {code}

    ### Output format:

    1. A python dictionary like {{ (state1, input1): state2, (state3, input2): state4, ...}}

    2. Output within a json block (```json ... ```)

    3. Note: The keys of the dictionary should be tuple of strings, and the values should be strings.

    4. Make sure all states are reachable from the INITIAL state.
    """ 

    gpt4_response = gpt4.query_openai_endpoint(user_prompt)
    with open(test_dir / 'gpt4_response.txt', 'w') as f:
        f.write(gpt4_response)

    ## parse the json response and save the transition dict
    parsed_response = gpt4_response.split("```json")[1].split("```")[0]
    transition_dict = eval(parsed_response)
    with open(test_dir / 'transition_dict.py', 'w') as f:
        f.write(parsed_response)
    print(f"\n[DONE] Saved transition dictionary at {test_dir / 'transition_dict.py'} \n")

    print("\n [*] Generating full test cases using the transition dictionary \n")

    ## iterate through test cases and generate full input sequences for each using the transition dict
    
    full_test_cases = []
    for test in test_cases:
        state = test["state"]
        message = test["message"]
        expected_response = test["expected_response"]

        # Use BFS to find the input sequence to reach the desired state from INITIAL state
        input_sequence = BFS(transition_dict, state)
        if input_sequence is None:
            print(colored(f" [!] State {state} is unreachable from INITIAL state using the transition dictionary. Skipping test case.", "red"))
            continue
        
        # Append the final input to reach the desired state
        input_sequence.append(message)
        full_test_cases.append({
            "input_sequence": input_sequence,
            "expected_response": expected_response
        })

    ## Save the full test cases
    with open(test_dir / 'full_test_cases.json', 'w') as f:
        json.dump(full_test_cases, f, indent=4)
    print(f"\n[DONE] Saved full test cases at {test_dir / 'full_test_cases.json'} \n")
 

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-m", "--module", type=str, required=True,
                        choices=["server"],
                        help="The SMTP module to generate inputs for.", default="server")
    # parser.add_argument("-n", "--nsdi", action="store_true",
    #                     help="Generate NSDI inputs.", default=False)
    parser.add_argument("-r", "--runs", type=int, required=False,
                        help="Number of runs to generate inputs for.", default=10)
    parser.add_argument("--timeout", type=int, required=False,
                        help="Timeout in seconds for each run.", default=300)
    args = parser.parse_args()
    # NSDI = args.nsdi
    if args.module == "server":
        server_check(args.runs, args.timeout)
    else:
        print("Invalid module selected.")