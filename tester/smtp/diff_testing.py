import subprocess
import time
import smtplib
import json
from tqdm import tqdm
import socket
import os

# Configuration
test_dir = "../../tests/smtp/NSDI/SMTP"
test_file_path = f"{test_dir}/full_test_cases_reduced.json"
results_json_path = f"{test_dir}/results.json"
diff_results_path = f"{test_dir}/diff_results.json"
server_ip = "127.0.0.1"
SERVER_TIMEOUT_SECONDS = 60 

## Helpers

def extract_code(resp) -> int:
    """
    Given one server's response from results.json, extract the numeric code.

    Expected normal shape (from normalize_response_to_tuple):
        [code: int, message: str]

    Be defensive in case of older / malformed data.
    """
    # Normal case: list/tuple [code, message]
    if isinstance(resp, (list, tuple)) and len(resp) >= 1:
        try:
            return int(resp[0])
        except (ValueError, TypeError):
            return 0

    # Unexpected shapes → treat as code 0
    return 0


def has_code_disagreement(actual_response) -> bool:
    """
    Return True if the response codes differ among any servers.
    """
    codes = []

    for server_name, resp in actual_response.items():
        code = extract_code(resp)
        codes.append(code)

    # If we have fewer than 2 codes, can't compare meaningfully
    if len(codes) < 2:
        return False

    # Disagreement iff not all codes are equal
    return len(set(codes)) > 1

def normalize_response_to_tuple(resp):
    """
    Convert any SMTP library response into a consistent tuple:
        [code: int, message: str]

    Handles:
    - (code, bytes)
    - (code, str)
    - bytes
    - str
    - None
    - Exceptions (handled outside)
    """

    # Typical case: (code, message)
    if isinstance(resp, tuple) and len(resp) == 2:
        code, msg = resp
        # message may be bytes → decode
        if isinstance(msg, bytes):
            msg = msg.decode(errors="replace")
        else:
            msg = str(msg)
        return [int(code), msg]

    # Raw bytes → message-only
    if isinstance(resp, bytes):
        return [0, resp.decode(errors="replace")]

    # Raw string
    if isinstance(resp, str):
        return [0, resp]

    # None or anything else
    return [0, ""]


def get_smtp_response(server_address, port, total_command_seq):
    """
    Execute a sequence of SMTP commands and return the last response.

    Strategy:
    - For protocol commands: use server.docmd(verb, arg).
    - For DATA payload commands encoded with <CRLF>: send raw data and getreply().
    - Special-case "." as end-of-data terminator if it appears as its own command.
    """
    server = None
    last_response = None

    try:
        server = smtplib.SMTP(server_address, port, timeout=SERVER_TIMEOUT_SECONDS)
        print(f"    - Connected to {server_address}:{port}")

        for raw_cmd in total_command_seq:
            cmd = raw_cmd.strip()
            print(f"        > C: {cmd}")
            # If the command encodes DATA payload with <CRLF>, treat it as raw data.
            if "<CRLF>" in cmd:
                data = cmd.replace("<CRLF>", "\r\n")
                server.send(data)
                last_response = server.getreply()

            # Special-case lone "." as end-of-data terminator
            elif cmd == ".":
                server.send("\r\n.\r\n")
                last_response = server.getreply()

            else:
                # Split into verb + arg for docmd
                parts = cmd.split(maxsplit=1)
                verb = parts[0].upper()
                arg = parts[1] if len(parts) > 1 else None

                # QUIT is just another command; don't break, let exceptions surface if more commands follow
                if arg is None:
                    last_response = server.docmd(verb)
                else:
                    last_response = server.docmd(verb, arg)

    except Exception as e:
        # If the server is too slow / not responding within timeout, mark it explicitly
        if isinstance(e, (socket.timeout, TimeoutError)):
            last_response = "not responding"
        else:
            # Capture other errors as string so they can be JSON-serialized if needed
            last_response = str(e)
    finally:
        if server is not None:
            try:
                server.quit()
            except Exception:
                pass

    return normalize_response_to_tuple(last_response)



def run_smtp_tests(server_address, tests_file):
    # Load test cases from the JSON file
    with open(tests_file, "r") as f:
        test_cases = json.load(f)

    print(f"[+] Loaded {len(test_cases)} test cases from {tests_file}")

    # Create empty results file
    with open(results_json_path, "w") as f:
        json.dump([], f)
    print(f"[+] Created new results file → {results_json_path}")


    # Loop through each test case
    results = []
    diff_results = []
    for idx, test in enumerate(tqdm(test_cases, desc="Running SMTP tests"), start=1):
        total_command_seq = test["input_sequence"]
        expected_response = test["expected_response"]

        print(f"[*] Test {idx}/{len(test_cases)}")

        # Execute on all servers
        print("    - Testing smtpd...")
        smtpd_response = get_smtp_response(server_address, 8025, total_command_seq)
        print("    - Testing opensmtpd...")
        opensmtpd_response = get_smtp_response(server_address, 8030, total_command_seq)
        print("    - Testing aiosmtpd...")
        aiosmtpd_response = get_smtp_response(server_address, 8034, total_command_seq)

        # Final result object
        result = {
            "test_id": idx,
            "input_sequence": total_command_seq,
            "expected_response": expected_response,
            "actual_response": {
                "smtpd": smtpd_response,
                "opensmtpd": opensmtpd_response,
                "aiosmtpd": aiosmtpd_response
            }
        }

        results.append(result)
        if has_code_disagreement(result["actual_response"]):
            diff_results.append(result)
            print("    - [!] Disagreement detected among servers!")

        with open(results_json_path, "w") as f:
            json.dump(results, f, indent=2)
        with open(diff_results_path, "w") as f:
            json.dump(diff_results, f, indent=2)

    print(f"\n[✔] All tests results written to {results_json_path}")


if __name__ == "__main__":

    ## Start the servers
    aiosmtpd_process = subprocess.Popen(["python", "server_aiosmtpd.py"])
    time.sleep(5)  # wait for the server to start

    ## Start smtpd in a different terminal with py 3.8
    # smtpd_process = subprocess.Popen("python server_smtpd.py", shell=True)
    # time.sleep(5)  # wait for the server to start
    
    opensmtpd_process = subprocess.Popen(["python", "server_opensmtpd.py"])
    time.sleep(5)  # wait for the server to start

    ## Run the tests
    run_smtp_tests(server_ip, test_file_path)

    ## Terminate the servers
    aiosmtpd_process.terminate()
    opensmtpd_process.terminate()
    os.system("kill -9 $(lsof -t -i:8025)")  
    os.system("kill -9 $(lsof -t -i:8030)")
    os.system("kill -9 $(lsof -t -i:8034)")



