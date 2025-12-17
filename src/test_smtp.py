import json
import eywa
import eywa.ast as ast
from eywa.llm import GPT4
import eywa.regex as re
import eywa.oracles as oracles
from eywa.composer import DependencyGraph
    

def test_smtp(test_gen=True):
    
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
    
    composer = DependencyGraph()
    composer.Node(smtp_server_model)
    smtp_oracle = composer.synthesize()
    
    smtp_code = smtp_oracle.implementation
    
    
    with open('smtp_code.c', 'w') as f:
        f.write(smtp_code)
    
    if test_gen:
        inputs = smtp_oracle.get_inputs(timeout_sec=300)
        count = 0
        for input in inputs:
            count += 1
            print(input)
            
        print("Total number of test cases:", count)

        with open('smtp_test_cases.json', 'w') as f:
            json.dump(inputs, f, indent=4)

    return (p_state, p_input, p_output, smtp_server_model, smtp_code, smtp_oracle.count_lines())


def generate_transition_dict():

    with open('smtp_code.c', 'r') as f:
        code = f.read()

    ## extract the code between line containing "smtp_server_response" and "int main()"
    start = code.find("smtp_server_response")
    end = code.find("int main()")
    code = code[start:end]

    gpt4 = GPT4()
    user_prompt = f"""
    Create a python dictionary that maps the state transitions: (state,input) --> state for the following C code snippet:

    {code}

    Output format:

    1. A python dictionary like {{ (state1, input1): state2, (state3, input2): state4, ...}}

    2. Output within a json block.
    """ 

    gpt4_response = gpt4.query_openai_endpoint(user_prompt)

    # print("\n\n***** GPT-4 response *****\n\n")
    # print(gpt4_response)

    ## parse the json response
    parsed_response = gpt4_response.split("```json")[1].split("```")[0]

    # print("\n\n***** Parsed response *****\n\n")
    # print(parsed_response)

    with open('smtp_transition_dict.json', 'w') as f:
        json.dump(json.loads(parsed_response), f, indent=4)
 
def unique_test_cases(all_tests):
    unique_tests = []
    for test in all_tests:
        if test not in unique_tests:
            unique_tests.append(test)
    return unique_tests
    
if __name__ == "__main__":
    result = test_smtp()
    num_lines = []
    all_tests = []
    for i in range(10):
        print("@@@ Test Generation Iteration:", i+1)
        result = test_smtp()
        num_lines.append(result[-1])
        
        with open('smtp_test_cases.json') as f:
            data = json.load(f)
            all_tests += data
        
        print("Number of lines of code:", num_lines)
        print("Number of test cases:", len(unique_test_cases(all_tests)))