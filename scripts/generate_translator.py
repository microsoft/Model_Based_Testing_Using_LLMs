from eywa.llm import GPT4
import argparse

##=============================== COMMAND LINE ARGS =================================##

parser = argparse.ArgumentParser(description='Generate translator code for different use cases')
parser.add_argument('--rr', action='store_true', help='Generate translator for Route Reflectors')
parser.add_argument('--confed', action='store_true', help='Generate translator for Confederations')
parser.add_argument('--router_type', type=str, help='Router type (e.g. "FRR", "GoBGP")', required=True)
args = parser.parse_args()

##========================= QUERY LLM FOR TRANSLATOR CODE ===========================##

def query_llm(system_prompt, user_prompt):
    gpt4 = GPT4()
    gpt4_response = gpt4.query_openai_endpoint(
        user_prompt, temperature=0, system_prompt=system_prompt)

    print("System prompt:", system_prompt, "\n\n")
    print("User prompt:", user_prompt, "\n\n")
    print("GPT:", gpt4_response, "\n\n")

    return gpt4_response

def extract_python_code_and_write(gpt_response, file_path):
    python_code = gpt_response.split("```python")[1].split("```")[0]
    with open(file_path, "w") as f:
        f.write(python_code)

##======================================== GLOBALS ================================================##


topology_description = """
Topology:

R1 (3.0.0.3) ----- (3.0.0.2) R2 (4.0.0.2) ----- (4.0.0.3) R3

"""

##========================= GENERATE TRANSLATORS FOR DIFFERENT USE CASES ===========================##

def generate_rr_translator(router_type):

    feature = "Route Reflectors"

    router_description = f"""

    In the given topology R1 is a ExaBGP route injector.
    R2 and R3 are {router_type} routers.

    """

    test_case_description = """

    Example of a test case:
    [
        256,
        256,
        256,
        true,
        false,
        false,
        true,
        true,
        false,
        false,
        true,
        {
            "isReceivedR2": true,
            "isReceivedR3": false
        }
    ]

    test[0] = AS of R1 (Exabgp)
    test[1] = AS of R2
    test[2] = AS of R3
    test[3] = whether R1 is a route reflector to R2
    test[4] = whether R1 is a client to R2
    test[5] = whether R2 is a route reflector to R1
    test[6] = whether R2 is a client to R1
    test[7] = whether R2 is a route reflector to R3
    test[8] = whether R2 is a client to R3
    test[9] = whether R3 is a route reflector to R2
    test[10] = whether R3 is a client to R2
    test[11] = the output, i.e. 'isReceivedR2' and 'isReceivedR3' says whether router2 and router3 received the route from router1 respectively.
    
    """

    output_format = """

    The output format is as follows:
    (isRIB2, isRIB3)

    isRIB2: True if router2 received the route from router1, False otherwise.
    isRIB3: True if router3 received the route from router1, False otherwise.

    These informations are to be extracted from the RIBs of router2 and router3 respectively.

    """

    with open("translator_template.py", "r") as f:
        template = f.read()
    
    system_prompt = "You need to write a translator code in python, which reads the given test case and generates appropriate configurations for the routers.\n" + \
    f"The test cases are for {feature}, so while populating the translator code, consider including configs of {feature} for router2 and router3. \n\n" + \
    topology_description + router_description 
    

    user_prompt = test_case_description + output_format + \
    "\nA template for the translator code is given below. You can modify it as needed.\n\n" + template + \
    "\n\nNow write a translator code in python by filling the missing parts in the template.\n" + \
    f"For Router 2 and Router 3 configuration should be written in {router_type} format\n" + \
    f"Make sure to include the configurations for {feature} in the translator code for updating configs of router2 and router 3. Use the semantics of the test case to do that.\n"

    response = query_llm(system_prompt, user_prompt)
    extract_python_code_and_write(response, "generated_rr_translator.py")


def generate_confed_translator(router_type):

    feature = "Confederations"

    router_description = f"""

    In the given topology R1 is a ExaBGP route injector.
    R2 and R3 are {router_type} routers.

    """

    test_case_description = """

    Example of a test case:
    [
        64512,
        {
            "asNumber": 400,
            "subAS": 256
        },
        {
            "asNumber": 512,
            "subAS": 400
        },
        true,
        false,
        50,
        false
    ]

    test[0] = AS of R1 (Exabgp)
    test[1] = Configuration of R2
    test[2] = Configuration of R3
    test[3] = remove-private-as flag of R2
    test[4] = replace-as flag of R2
    test[5] = Local Preference set at R2 using a outbound route-map
    test[6] = isExternalPeer flag at R3 (if true, R2 is marked as external peer and in config of R3, remote-as is set to 'external')

    """

    output_format = """

    The output format is as follows:
    (isRIB2, isRIB3, aspath2, aspath3, lp2, lp3)

    isRIB2: True if router2 received the route from router1, False otherwise.
    isRIB3: True if router3 received the route from router1, False otherwise.
    aspath2: AS path of the route received by router2.
    aspath3: AS path of the route received by router3.
    lp2: Local Preference set at router2.
    lp3: Local Preference received at router3.

    These informations are to be extracted from the RIBs of router2 and router3 respectively.

    """

    with open("translator_template.py", "r") as f:
        template = f.read()
    
    system_prompt = "You need to write a translator code in python, which reads the given test case and generates appropriate configurations for the routers.\n" + \
    f"The test cases are for {feature}, so while populating the translator code, consider including configs of {feature} for router2 and router3. \n\n" + \
    topology_description + router_description 
    

    user_prompt = test_case_description + output_format + \
    "\nA template for the translator code is given below. You can modify it as needed.\n\n" + template + \
    "\n\nNow write a translator code in python by filling the missing parts in the template.\n" + \
    f"For Router 2 and Router 3 configuration should be written in {router_type} format\n" + \
    f"Make sure to include the configurations for {feature} in the translator code for updating configs of router2 and router 3. Use the semantics of the test case to do that.\n"

    response = query_llm(system_prompt, user_prompt)
    extract_python_code_and_write(response, "generated_confed_translator.py")


##======================================== MAIN ================================================##

if args.rr:
    generate_rr_translator(args.router_type)
elif args.confed:
    generate_confed_translator(args.router_type)
