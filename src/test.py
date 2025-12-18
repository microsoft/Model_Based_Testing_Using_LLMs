import eywa
import eywa.ast as ast
import eywa.regex as re
import eywa.oracles as oracles
from eywa.composition import run_wrapper_model
from termcolor import colored
import json


def run_model(model):
    """
    Run a model and print the results.
    """
    oracle = oracles.KleeOracle(model)
    oracle.build_model(temperature=0.6)
    print(oracle.implementation)
    return oracle
    
def get_partial_model(model, function_prototypes=None, constants=None):
    oracle = oracles.KleeOracle(model, function_prototypes, constants)
    oracle.build_compositional_model(temperature=0.6)
    sys_text = colored("System prompt:", "red", attrs=["bold"])
    print(sys_text, oracle.system_prompt())
    usr_text = colored("User prompt:", "blue", attrs=["bold"])
    print(usr_text, oracle.user_prompt()) 
    gpt_text = colored("GPT:", "green", attrs=["bold"])
    print(gpt_text, oracle.implementation)
    return oracle

def get_filter_and_test_model(model, function_prototypes):
    oracle = oracles.KleeOracle(model)
    sys_text = colored("System prompt:", "red", attrs=["bold"])
    print(sys_text, oracle.system_prompt())
    usr_text = colored("User prompt:", "blue", attrs=["bold"])
    print(usr_text, oracle.user_prompt()) 
    gpt_text = colored("GPT:", "green", attrs=["bold"])
    oracle.build_filter_and_test_model(function_prototypes)
    print(oracle.implementation)
    return oracle

def test_precondition_0():
    """
    Test that strings work with the char* type and regex constraints.
    """
    p1 = ast.Parameter("input", ast.String(maxsize=3), "An input string")
    p2 = ast.Parameter("is_palendrone", ast.Bool(),
                       "Whether the string is a palendrone.")
    model = ast.Function(
        "is_palendrone",
        "A function that checks if a string is a palendrone.",
        [p1, p2],
        precondition=p1.matches(re.star(re.chars('a', 'z'))),
    )
    run_model(model)


def test_precondition_1():
    """
    Test that preconditions work for arrays and structs.
    """
    header = ast.Struct("TCPHeader", dstip=ast.Int(32), srcip=ast.Int(32))
    headers = ast.Array(header, 3)
    p1 = ast.Parameter("headers", headers, "An array of TCP header.")
    p2 = ast.Parameter("is_valid", ast.Bool(),
                       "Whether each header in the array is valid.")
    model = ast.Function(
        "check_tcp_header_valid",
        "A function that checks if a TCP header is valid or not.",
        [p1, p2],
        precondition=p1.forall(lambda h: (h.get_field("dstip") > 10) & (
            h.get_field("srcip") > h.get_field("dstip"))),
    )
    run_model(model)


def test_precondition_2():
    """
    Test that preconditions work with equality and type aliases.
    """
    str = ast.Alias("String", ast.String(maxsize=3))
    p1 = ast.Parameter("input1", str, "An input string.")
    p2 = ast.Parameter("input2", str, "An input string.")
    p3 = ast.Parameter("is_all_bs", ast.Bool(),
                       "if the first string is all 'b's.")
    model = ast.Function(
        "check_if_all_bs",
        "A function that checks if the first input is all 'b' characters.",
        [p1, p2, p3],
        precondition=(p1 == p2),
    )
    run_model(model)


def test_precondition_3():
    """
    Test that preconditions work with basic operations like inequality and equality.
    """
    p1 = ast.Parameter("x", ast.Int(32), "The first input.")
    p2 = ast.Parameter("y", ast.Int(32), "The second input.")
    p3 = ast.Parameter("result", ast.Bool(
    ), "If the inputs x and y have the same parity (odd or even).")
    model = ast.Function(
        "have_same_parity",
        "A function that checks if the two inputs have the same parity.",
        [p1, p2, p3],
        precondition=(p1 >= 10) & (p2 > p1),
    )
    run_model(model)


def test_precondition_4():
    """
    Test that preconditions work with nested arrays.
    """
    a = ast.Alias("Element", ast.Array(ast.Int(32), 3))
    p1 = ast.Parameter("array", a, "An array input.")
    p2 = ast.Parameter("result", ast.Bool(),
                       "If the array is strictly in ascending order.")
    model = ast.Function(
        "identity",
        "A function that determines if an array is strictly in ascending order.",
        [p1, p2],
        precondition=p1.forall(lambda x: (x >= 100) & (x <= 200)),
    )
    run_model(model)


def test_return_type1():
    """
    Test that returns work for complex types.
    """
    t = ast.Struct("Point", x=ast.String(), y=ast.String())
    p1 = ast.Parameter("x", ast.Int(32), "An integer value.")
    p2 = ast.Parameter(
        "result", t, "The point (1, 2) if the input x is equal to 10, otherwise the point (4, 5).")
    model = ast.Function(
        "int2string",
        "A function that returns the point (1, 2) if the input x is equal to 10, otherwise the point (4, 5).",
        [p1, p2],
    )
    run_model(model)
    # tests = eywa.run(model, k=1, debug=r"tests")
    # print(tests)


def test_return_type2():
    """
    Test that returns work for complex types.
    """
    t1 = ast.Struct("Point", x=ast.String(), y=ast.String())
    t2 = ast.Array(t1, 2)
    p1 = ast.Parameter("x", ast.Int(32), "An integer value.")
    p2 = ast.Parameter(
        "result", t2, "The array of points [(1, 2), (3, 4)] if the input x is equal to 10, otherwise the array of points point [(5, 6), (7, 8)].")
    model = ast.Function(
        "int2array",
        "A function that returns the array of points [(1, 2), (3, 4)] if the input x is equal to 10, otherwise the array of points point [(5, 6), (7, 8)].",
        [p1, p2],
    )
    run_model(model)
    # tests = eywa.run(model, k=1, debug=r"tests")
    # print(tests)
    
def test_prompt():
    # Define the data types.
    domain_name = eywa.String(maxsize=3)
    record_type = eywa.Enum("RecordType", ["A", "AAAA", "NS", "TXT", "CNAME", "DNAME", "SOA"])
    record = eywa.Struct("RR", rtyp=record_type, domain_name=domain_name, rdat=eywa.String(3))
    # Define the module arguments.
    query = ast.Parameter("query", domain_name, "A DNS query domain name.")
    record = ast.Parameter("record", record, "A DNS record.")
    result = ast.Parameter("result", eywa.Bool(), "If the DNS record matches the query.")
    # Define 3 modules to validate the query and implement the record matching logic.

    da = ast.Function("dname_applies", "If a DNAME record matches a query.", [record, query, result])

    run_model(da)
    
def test_regex_parser():
    g = eywa.DependencyGraph()
    label = re.star(re.choice(re.chars('a', 'z'), re.text('*')))
    valid_dn_re = re.seq(label, re.star(re.seq(re.text('.'), label)))
    domain_name = eywa.String(maxsize=3)
    query = ast.Parameter("query", domain_name, "A DNS query domain name.")
    regex_str = "[a-z\\*]*(\\.[a-z\\*]*)*"
    valid_query = eywa.RegexModule(
        "isValidQuery",
        regex_str,
        query
    )
    
    oracle = run_wrapper_model(valid_query)
    print(oracle.implementation)
    
    
def test_dname():
    # Define the data types.
    domain_name = eywa.String(maxsize=5)
    record_type = eywa.Enum("RecordType", ["A", "AAAA", "NS", "TXT", "CNAME", "DNAME", "SOA"])
    record = eywa.Struct("RR", rtyp=record_type, domain_name=domain_name, rdat=eywa.String(3))
    # Define the module arguments.
    query = eywa.Parameter("query", domain_name, "A DNS query domain name.")
    record = eywa.Parameter("record", record, "A DNS record.")
    result = eywa.Parameter("result", eywa.Bool(), "If the DNS record matches the query.")
    # Define 3 modules to validate the query and implement the record matching logic.
    valid_query = eywa.RegexModule(
        "isValidQuery",
        "[a-z\\*](\\.[a-z*])*", query)
    ra = eywa.Function("record_applies", "If a DNS record matches a query.", [query, record, result])
    da = eywa.Function("dname_applies", "If a DNAME record matches a query.", [query, record, result])
    # Create the dependency graph to connect the modules.
    g = eywa.DependencyGraph()
    
    g.Pipe(ra, valid_query)
    
    g.CallEdge(ra, [da])
    # Synthesize the end-to-end model and generate test inputs.
    
    model = g.synthesize()
    inputs = model.get_inputs(timeout_sec=5)
    for input in inputs:
        print(input)
    
    
    
def test_ipv4_match():
    valid_domain_regex = "[a-z\\*](\\.[a-z*])*"
    print("Valid domain regex:", valid_domain_regex)
    domain_name = eywa.String(maxsize=5)
    
    domain_name_param = eywa.Parameter("domain_name", domain_name, "The domain name to validate.")
    valid_domain_name = eywa.RegexModule(
        "isValidDomainName",
        valid_domain_regex,
        domain_name_param
    )
    
    query_dn = eywa.Parameter("domain_name", domain_name, "The domain name to check.")
    ip_dn = eywa.Parameter("ipv4_domain_name", domain_name, "The A record domain name.")
    dname_result = eywa.Parameter("result", eywa.Bool(), "If the A record matches the query domain name.")
    is_valid = eywa.Parameter("is_valid", eywa.Bool(), "If the input domain names are valid.")
    
    is_matching_ipv4_record = eywa.Function(
        "is_matching_a_record",
        "a function that checks if an A DNS record matches a DNS domain name query. Include corner cases like wildcard matching and others. DO NOT USE C strtok function.",
        [query_dn, ip_dn, dname_result]
    )
    
    valid_inputs = eywa.Function(
        "isValidInputs",
        "a function that checks if the input domain names are valid according to DNS standards.",
        [query_dn, ip_dn, is_valid]
    )
    
    g = eywa.DependencyGraph()
    g.CallEdge(valid_inputs, [valid_domain_name])
    g.Pipe(is_matching_ipv4_record, valid_inputs)
    model = g.Synthesize()
    print(model.implementation)
    with open('ipv4_match_code.c', 'w') as f:
        f.write(model.implementation)
    inputs = model.get_inputs(timeout_sec=5)
    generated_inputs = []
    for input in inputs:
        generated_inputs.append(input)
        print(input)
    with open('ipv4_match_tests.json', 'w') as f:
        json.dump(generated_inputs, f, indent=4)
    
if __name__ == "__main__":
    # test_precondition_0()
    # test_precondition_1()
    # test_precondition_2()
    # test_precondition_3()
    # test_precondition_4()
    # test_return_type1()
    # test_return_type2()
    # test_void_function()
    # test_function_return()
    # test_prompt()
    # test_point()
    # test_regex_parser()
    # test_dname()
    test_ipv4_match()
    pass