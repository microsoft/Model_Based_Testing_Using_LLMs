import smtplib
import json
from tqdm import tqdm

def run_smtp_tests(server_address, port, tests_file, output_file):
    # Load test cases from the JSON file
    with open(tests_file, "r") as f:
        test_cases = json.load(f)
    
    results = []

    count = 0
    # Loop through each test case
    for test in tqdm(test_cases):
        count += 1
        input_seq, state, test_input, expected_response = test
        print(f"Running test {count} for state: {state}, input: {test_input}")
        print(f"test case: {test}\n")
        total_input_seq = input_seq + [test_input]

        try:
            # Connect to the SMTP server
            server = smtplib.SMTP(server_address, port)
            
            # Execute input sequence to reach the desired state
            for input in total_input_seq:
                print(f"Input: {input}")
                if input == "EHLO":
                    response = server.ehlo()
                elif input == "HELO":
                    response = server.helo()
                elif input == "MAIL FROM:":
                    response = server.mail("rathin.singha2012@gmail.com")
                elif input == "RCPT TO:":
                    response = server.rcpt("rsingha@cs.ucla.edu")
                elif input == "DATA":
                    response = server.docmd("DATA")
                    server.send("Hi\r\n.\r\n")
                elif input == ".":
                    server.send("\r\n.\r\n")
                    response = server.getreply()
                elif input == "QUIT":
                    response = server.quit()
                else:
                    server.send(f"{input}\r\n")
                    response = server.getreply()

                print(f"Response: {response}")
            
            results.append((state, test_input, response))
        except Exception as e:
            results.append((state, test_input, str(e)))
        finally:
            # Quit the server connection
            try:
                server.quit()
            except:
                pass

    # Save results to the output file
    with open(output_file, "w") as f:
        for result in results:
            f.write(f"{result}\n")

# Example Usage
run_smtp_tests(
    server_address="127.0.0.1",
    port=8025,
    tests_file="tests.json",
    output_file="results.txt"
)
