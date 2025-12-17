import json
import os

def parse_test_case(test):
    ## Implement as follows:

    ## Parse fileds from test case
    # field0 = test[0]
    # field1 = test[1]
    # ...
    # return field0, field1, ...
    pass

    
def parse_rib(ribfile):
    """
    Example of a BGP RIB:

BGP routing table entry for 100.10.0.0/24, version 1
Paths: (1 available, best #1, table default)
  Advertised to non peer-group peers:
  3.0.0.3
  512
    3.0.0.3 from 3.0.0.3 (3.0.0.3)
      Origin IGP, valid, external, best (First path received)
      Last update: Sat Nov  9 19:26:45 2024
    """

    with open(ribfile,"r") as f:
        lines = f.readlines()

    if lines[0].strip() == "% Network not in table":
        isRIB = False ## route not in RIB
    else:
        isRIB = True ## route in RIB

    ## Similarly parse other information from RIB if needed
        

    return isRIB ## return other parsed information as well if needed


def update_exabgp_config(local_as, peer_as):

    new_config = f"""
process announce-routes {{  
    run python exabgp/example.py;
    encoder json;
}}

neighbor 3.0.0.2 {{                 # Remote neighbor to peer with
    router-id 3.0.0.3;              # Our local router-id
    local-address 3.0.0.3;          # Our local update-source
    local-as {local_as};                    # Our local AS
    peer-as {peer_as};                     # Peer's AS

    api {{
        processes [announce-routes];
    }}
}}
    """

    with open("exabgp1/conf.ini", "w") as f:
        f.write(new_config)


def update_router2_config(): ## Add parameters as needed
    """
    This function updates the configuration file of router 2 based on the test case.
    Pick up appropriate parameters from the test case and update the configuration file.
    Choose the parameters that are relevant to the test case.

    """

    ## An example configuration is given below. Change it as per the test case. 
    new_config = f"""
    Write your configuration here
    """

def update_router3_config(): ## Add parameters as needed
    """
    This function updates the configuration file of router 3 based on the test case.
    Pick up appropriate parameters from the test case and update the configuration file.
    Choose the parameters that are relevant to the test case.

    """

    ## An example configuration is given below. Change it as per the test case. 
    new_config = f"""
    Write your configuration here
    """


################ Main ################
with open("../tests.json","r") as f:
    tests = json.load(f)

g = open("results.txt","w")
g.close()
n_tests = len(tests)
for i,test in enumerate(tests):
    print(f"@@@ Running Test {i+1}/{n_tests}...\n")

    ## Parse test cases
    
    parsed_params = parse_test_case(test)
    
    ## ... = parsed_params ## unpack parsed_params

    ## update_exabgp_config(...) ## decide which parameters to pass

    ## update_router2_config(...) ## decide which parameters to pass

    ## update_router3_config(...) ## decide which parameters to pass

    os.system("bash test.sh") ## This will run the test (already implemented in test.sh)

    ### Parse RIBs ###

    isRIB2 = parse_rib("router2_RIB.txt") ## capture other parsed information as well if needed
    isRIB3 = parse_rib("router3_RIB.txt") ## capture other parsed information as well if needed

    with open("results.txt","a") as f:
        f.write(f"{isRIB2},{isRIB3}\n") ## write other parsed information as well if needed






