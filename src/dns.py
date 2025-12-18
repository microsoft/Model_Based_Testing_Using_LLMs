import json
import pathlib
from typing import Generator, List, Tuple
import eywa
import eywa.ast as ast
import eywa.oracles as oracles
import eywa.regex as re
import eywa.run as run

SIGCOMM = False

def build_regex_module(maxsize=5):
    valid_dn_re = "[a-z\\*](\\.[a-z*])*"
    domain_name = eywa.String(maxsize=maxsize)
    domain_name_param = eywa.Parameter("domain_name", domain_name,"The domain name to validate")
    is_valid_domain_name = eywa.RegexModule(
        "is_valid_domain_name",
        valid_dn_re,
        domain_name_param
    )
    
    return is_valid_domain_name

def build_is_valid_module(domain_name_param, maxsize=5):
    domain_name = eywa.String(maxsize=maxsize)
    query_dn = eywa.Parameter("domain_name", domain_name,description="The domain name to check")
    is_valid = ast.Parameter("is_valid", ast.Bool(), description="whether the DNS domain name is valid according to DNS standards.")
    valid_inputs = eywa.Function(
        "isValidInputs",
        "a function that checks if the input domain names are valid according to DNS standards.",
        [query_dn, domain_name_param, is_valid]
    )
    return valid_inputs
     
    
def generate_zone_query_pair_inputs(inputs: List[Tuple[List[dict], str]], output_directory: str = "Tests") -> None:
    """
    Generate inputs for a test function that takes a zone and query as input.
    :param inputs: list of tuples of zone file and query
    :param output_directory: the directory to output the generated inputs
    """
    test_dir = pathlib.Path(output_directory)
    test_dir.mkdir(exist_ok=True)
    (test_dir / "ZoneFiles").mkdir(exist_ok=True)
    (test_dir / "Queries").mkdir(exist_ok=True)
    for i, input in enumerate(inputs):
        with open(test_dir / "Queries" / f"{i}.json", "w") as f:
            f.write(json.dumps(input[0]))
        with open(test_dir / "ZoneFiles" / f"{i}.txt", "w") as f:
            f.write(input[1])


def generate_zone_query_inputs_from_zone(zone_input: List[Tuple[List[dict], str]], output_directory: str = "Tests") -> None:
    """
    Generate inputs for a test function that takes a zone as input. The query is created from the zone origin.
    :param inputs: list of tuples of zone file and zone origin
    :param program: the program input to Klee to generate inputs
    :param output_directory: the directory to output the generated inputs
    """
    test_dir = pathlib.Path(output_directory)
    test_dir.mkdir(exist_ok=True)
    (test_dir / "ZoneFiles").mkdir(exist_ok=True)
    (test_dir / "Queries").mkdir(exist_ok=True)
    for i, input in enumerate(zone_input):
        queries = []
        queries.append({"Name": input[1], "Type": "A"})
        with open(test_dir / "Queries" / f"{i}.json", "w") as f:
            f.write(json.dumps(queries))
        with open(test_dir / "ZoneFiles" / f"{i}.txt", "w") as f:
            f.write(input[0])


def cname_match_check():
    domain_name = ast.String(5)
    
    query_dn = ast.Parameter("domain_name", domain_name,description="The domain name to check")
    cname_dn = ast.Parameter("cname_domain_name", domain_name,description="The CNAME record domain name")
    cname_result = ast.Parameter("result", ast.Bool(), description="whether the DNS domain name query matches the CNAME record.")

    def create_cname_zone(input: Tuple) -> Tuple[List[dict], str]:
        query_name, zone_record_name = input[0], input[1]
        zone_file = 'test.\t500\tIN\tSOA\tns1.outside.edu. root.campus.edu. 8 6048 4000 2419200 6048\n'
        zone_file += 'test.\t500\tIN\tNS\tns1.outside.edu.\n'
        zone_file += f'{zone_record_name}.test.\t500\tIN\tCNAME\tsome.domain.\n'
        queries = []
        queries.append({"Name": query_name + ".test.", "Type": "CNAME"})
        queries.append({"Name": query_name + ".test.", "Type": "TXT"})
        return (queries, zone_file)

    is_matching_cname_record = ast.Function(
        "is_matching_cname_record",
        "a function that checks if a CNAME DNS record matches a DNS domain name query.\n"
        "Includes cases like wildcards with '*' labels. DO NOT USE C strtok function.",
        [query_dn, cname_dn, cname_result]
    )
    
    is_valid_domain_name = build_regex_module(maxsize=5)
    is_valid_inputs = build_is_valid_module(cname_dn, maxsize=5)
    
    g = eywa.DependencyGraph()
    g.CallEdge(is_valid_inputs, [is_valid_domain_name])
    g.Pipe(is_matching_cname_record, is_valid_inputs)
    
    if SIGCOMM:
        output_dir = pathlib.Path("SIGCOMM//CNAME")
        inputs = run(g, k=10,
                     debug=output_dir, timeout_sec=300)
        query_zone_tuples = []
        for input in inputs:
            query_zone_tuples.append(create_cname_zone(input))
        generate_zone_query_pair_inputs(query_zone_tuples, (output_dir))
    else:
        output_dir = pathlib.Path("CNAME")
        for i in range(0, 10):
            for temperature in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
                (output_dir / f"{temperature}" /
                 f"{i}").mkdir(exist_ok=True, parents=True)
                inputs = run(g, k=12,
                             debug=output_dir / f"{temperature}" / f"{i}", temperature_value=temperature, timeout_sec=300)
                query_zone_tuples = []
                for input in inputs:
                    query_zone_tuples.append(create_cname_zone(input))
                generate_zone_query_pair_inputs(
                    query_zone_tuples, (output_dir / f"{temperature}" / f"{i}"))


def dname_match_check():
    domain_name = ast.String(5)

    query_dn = ast.Parameter("domain_name", domain_name, description="The domain name to check")
    dname_dn = ast.Parameter("dname_domain_name", domain_name, description="The DNAME record domain name")
    dname_result = ast.Parameter("result", ast.Bool(
    ), description="whether the DNS domain name query matches the DNAME record.")

    def create_dname_zone(input: Tuple) -> Tuple[List[dict], str]:
        query_name, zone_record_name = input[0], input[1]
        zone_file = 'test.\t500\tIN\tSOA\tns1.outside.edu. root.campus.edu. 8 6048 4000 2419200 6048\n'
        zone_file += 'test.\t500\tIN\tNS\tns1.outside.edu.\n'
        zone_file += f'{zone_record_name}.test.\t500\tIN\tDNAME\tsome.domain.\n'
        queries = []
        queries.append({"Name": query_name + ".test.", "Type": "DNAME"})
        queries.append({"Name": query_name + ".test.", "Type": "CNAME"})
        return (queries, zone_file)

    is_matching_dname_record = ast.Function(
        "is_matching_dname_record",
        "a function that checks if a DNAME (provides redirection from a part of the DNS name tree to another part of the DNS name tree) DNS record matches a DNS domain name query. DO NOT USE C strrev function.",
        [query_dn, dname_dn, dname_result],
    )
    
    is_valid_domain_name = build_regex_module(maxsize=5)
    is_valid_inputs = build_is_valid_module(dname_dn, maxsize=5)
    
    g = eywa.DependencyGraph()
    g.CallEdge(is_valid_inputs, [is_valid_domain_name])
    g.Pipe(is_matching_dname_record, is_valid_inputs)
    
    if SIGCOMM:
        output_dir = pathlib.Path("SIGCOMM//DNAME")
        inputs = run(g, k=10,
                     debug=output_dir, timeout_sec=300)
        query_zone_tuples = []
        for input in inputs:
            query_zone_tuples.append(create_dname_zone(input))
        generate_zone_query_pair_inputs(query_zone_tuples, (output_dir))
    else:
        output_dir = pathlib.Path("DNAME")
        for i in range(0, 10):
            for temperature in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
                (output_dir / f"{temperature}" /
                 f"{i}").mkdir(exist_ok=True, parents=True)
                inputs = run(g, k=12,
                             debug=output_dir / f"{temperature}" / f"{i}", temperature_value=temperature, timeout_sec=300)
                query_zone_tuples = []
                for input in inputs:
                    query_zone_tuples.append(create_dname_zone(input))
                generate_zone_query_pair_inputs(
                    query_zone_tuples, (output_dir / f"{temperature}" / f"{i}"))


def ipv4_match_check():
    domain_name = ast.String(5)

    query_dn = ast.Parameter("domain_name", domain_name, description="The domain name to check")
    ip_dn = ast.Parameter("ipv4_domain_name", domain_name, description="The A record domain name")
    dname_result = ast.Parameter("result", ast.Bool(
    ), description="whether the DNS domain name query matches the A record.")

    def create_ipv4_zone(input: Tuple) -> Tuple[List[dict], str]:
        query_name, zone_record_name = input[0], input[1]
        zone_file = 'test.\t500\tIN\tSOA\tns1.outside.edu. root.campus.edu. 8 6048 4000 2419200 6048\n'
        zone_file += 'test.\t500\tIN\tNS\tns1.outside.edu.\n'
        zone_file += f'{zone_record_name}.test.\t500\tIN\tA\t1.1.1.1\n'
        queries = []
        queries.append({"Name": query_name + ".test.", "Type": "A"})
        queries.append({"Name": query_name + ".test.", "Type": "CNAME"})
        return (queries, zone_file)

    is_matching_ipv4_record = ast.Function(
        "is_matching_a_record",
        "a function that checks if an A DNS record matches a DNS domain name query. Include corner cases like wildcard matching and others. DO NOT USE C strtok function.",
        [query_dn, ip_dn, dname_result]
    )
    
    is_valid_domain_name = build_regex_module(maxsize=5)
    is_valid_inputs = build_is_valid_module(ip_dn, maxsize=5)
    
    g = eywa.DependencyGraph()
    g.CallEdge(is_valid_inputs, [is_valid_domain_name])
    g.Pipe(is_matching_ipv4_record, is_valid_inputs)
    
    if SIGCOMM:
        output_dir = pathlib.Path("SIGCOMM//IPv4")
        inputs = run(g, k=10,
                     debug=output_dir,  timeout_sec=300)
        query_zone_tuples = []
        for input in inputs:
            query_zone_tuples.append(create_ipv4_zone(input))
        generate_zone_query_pair_inputs(query_zone_tuples, (output_dir))
    else:
        output_dir = pathlib.Path("IPv4")
        for i in range(0, 10):
            for temperature in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
                (output_dir / f"{temperature}" /
                 f"{i}").mkdir(exist_ok=True, parents=True)
                inputs = run(g, k=12,
                             debug=output_dir / f"{temperature}" / f"{i}", temperature_value=temperature, timeout_sec=300)
                query_zone_tuples = []
                for input in inputs:
                    query_zone_tuples.append(create_ipv4_zone(input))
                generate_zone_query_pair_inputs(
                    query_zone_tuples, (output_dir / f"{temperature}" / f"{i}"))


def ipv4_match_check_no_precondition():
    domain_name = ast.String(5)

    query_dn = ast.Parameter("domain_name", domain_name,
                             description="The domain name to check")
    ip_dn = ast.Parameter("ipv4_domain_name", domain_name,
                          description="The A record domain name")
    dname_result = ast.Parameter("result", ast.Bool(
    ), description="whether the DNS domain name query matches the A record.")

    def create_ipv4_zone(input: Tuple) -> Tuple[List[dict], str]:
        query_name, zone_record_name = input[0], input[1]
        zone_file = 'test.\t500\tIN\tSOA\tns1.outside.edu. root.campus.edu. 8 6048 4000 2419200 6048\n'
        zone_file += 'test.\t500\tIN\tNS\tns1.outside.edu.\n'
        zone_file += f'{zone_record_name}.test.\t500\tIN\tA\t1.1.1.1\n'
        queries = []
        queries.append({"Name": query_name + ".test.", "Type": "A"})
        queries.append({"Name": query_name + ".test.", "Type": "CNAME"})
        return (queries, zone_file)

    is_matching_ipv4_record = ast.Function(
        "is_matching_a_record",
        "a function that checks if an A DNS record matches a DNS domain name query. \
         Include corner cases like wildcard matching and others. DO NOT USE C strtok function. \
         First write a function that checks if a DNS domain name is valid and only if they are valid then check if they match.",
        [query_dn, ip_dn, dname_result]
    )
    
    g = eywa.DependencyGraph()
    g.Node(is_matching_ipv4_record)

    output_dir = "IPv4_full"
    inputs = run(g, k=3, debug=output_dir)
    query_zone_tuples = []
    for input in inputs:
        query_zone_tuples.append(create_ipv4_zone(input))
    generate_zone_query_pair_inputs(query_zone_tuples, output_dir)


def validate_domain_name():
    domain_name = ast.String(3)
    dn = ast.Parameter("domain_name", domain_name,
                       description="The DNS domain name to validate")
    result = ast.Parameter("result", ast.Bool(
    ), description="whether the DNS domain name is valid.")
    validate_domain_name = ast.Function(
        "validate_domain_name",
        "a function that checks if a DNS domain name is valid according to RFC standards. "
        "Include as many checks as possible including checks for wildcard domain names.",
        [dn, result]
    )
    
    g = eywa.DependencyGraph()
    g.Node(validate_domain_name)

    output_dir = "ValidateDomainName"
    inputs = run(g, k=10, debug=output_dir)

    test_dir = pathlib.Path(output_dir)
    test_dir.mkdir(exist_ok=True)
    (test_dir / "ZoneFiles").mkdir(exist_ok=True)
    (test_dir / "Queries").mkdir(exist_ok=True)

    for i, input in enumerate(inputs):
        domain_name = input[0]
        if not len(domain_name):
            continue
        if domain_name[-1] != ".":
            domain_name += "."
        zone_file = f'{domain_name}\t500\tIN\tSOA\tns1.outside.edu. root.campus.edu. 8 6048 4000 2419200 6048\n'
        zone_file += f'{domain_name}\t500\tIN\tNS\tns1.outside.edu.\n'
        with open(test_dir / "ZoneFiles" / f"{i}.txt", "w") as f:
            f.write(zone_file)
        queries = []
        queries.append({"Name": domain_name, "Type": "A"})
        with open(test_dir / "Queries" / f"{i}.json", "w") as f:
            f.write(json.dumps(queries))


def wildcard_match_check():
    domain_name = ast.String(5)
    
    query_dn = ast.Parameter("domain_name", domain_name, description="The domain name to check")
    wildcard_dn = ast.Parameter("wildcard_domain_name", domain_name, description="The wildcard record domain name")
    wildcard_result = ast.Parameter("result", ast.Bool(
    ), description="whether the DNS domain name query matches the wildcard record.")

    def create_wildcard_zone(input: Tuple) -> Tuple[List[dict], str]:
        query_name, zone_record_name = input[0], input[1]
        zone_file = 'test.\t500\tIN\tSOA\tns1.outside.edu. root.campus.edu. 8 6048 4000 2419200 6048\n'
        zone_file += 'test.\t500\tIN\tNS\tns1.outside.edu.\n'
        zone_file += f'{zone_record_name}.test.\t500\tIN\tA\t1.1.1.1\n'
        queries = []
        queries.append({"Name": query_name + ".test.", "Type": "A"})
        queries.append({"Name": query_name + ".test.", "Type": "CNAME"})
        return (queries, zone_file)

    is_matching_wildcard_record = ast.Function(
        "is_matching_wildcard_record",
        "a function that checks if a DNS wildcard record matches a DNS domain name query. DO NOT USE C strrev function.",
        [query_dn, wildcard_dn, wildcard_result]
    )
    
    is_valid_domain_name = build_regex_module(maxsize=5)
    is_valid_inputs = build_is_valid_module(wildcard_dn, maxsize=5)
    g = eywa.DependencyGraph()
    g.CallEdge(is_valid_inputs, [is_valid_domain_name])
    g.Pipe(is_matching_wildcard_record, is_valid_inputs)
    
    if SIGCOMM:
        output_dir = pathlib.Path("SIGCOMM//Wildcard")
        inputs = run(g, k=10,
                     debug=output_dir, timeout_sec=300)
        query_zone_tuples = []
        for input in inputs:
            query_zone_tuples.append(create_wildcard_zone(input))
        generate_zone_query_pair_inputs(query_zone_tuples, (output_dir))
    else:
        output_dir = pathlib.Path("Wildcard")
        for i in range(0, 10):
            for temperature in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
                (output_dir / f"{temperature}" /
                 f"{i}").mkdir(exist_ok=True, parents=True)
                inputs = run(g, k=12,
                             debug=output_dir / f"{temperature}" / f"{i}", temperature_value=temperature, timeout_sec=300)
                query_zone_tuples = []
                for input in inputs:
                    query_zone_tuples.append(create_wildcard_zone(input))
                generate_zone_query_pair_inputs(
                    query_zone_tuples, (output_dir / f"{temperature}" / f"{i}"))


def create_zone(input: List) -> Tuple[List[dict], str]:
    """
    Creates a well-formatted zone file from a Klee generated zone file.
    Adds an SOA record if one is not present in the zone file.

    :param input: A list of arguments to the function with zone file as the first argument
    :return: a tuple of the formatted zone file and zone origin
    """
    def ipv4_gen() -> Generator[str, None, None]:
        """
        Returns RDATA for A (IPv4) records.
        Klee generated zone files have random RDATA for IPv4 records, which are
        filled during translation.
        """
        sample_ips = ['1.1.1.1', '2.2.2.2', '3.3.3.3', '4.4.4.4', '5.5.5.5']
        while True:
            for i in sample_ips:
                yield i

    def ipv6_gen() -> Generator[str, None, None]:
        """
        Returns RDATA for AAAA (IPv6) records.
        Klee generated zone files have random RDATA for IPv6 records, which are
        filled during translation.
        """
        sample_ips = ['2400:cb00:2049:1::a29f:1804', '2001:0db8:85a3:0000:0000:8a2e:0370:7334',
                      '0:0:0:0:0:ffff:192.1.56.10', 'FE80:CD00:0000:0CDE:1257:0000:211E:729C',
                      '2001:0db8:0000:0000:0000:8a2e:0370:7334']
        while True:
            for i in sample_ips:
                yield i

    formatted_records = set()
    ipv4 = ipv4_gen()
    ipv6 = ipv6_gen()
    found_soa = False
    zone_origin = ""
    for record in input[0]:
        record_name = record["domain_name"]
        rtype = record["record_type"]
        rdata = record["rdata"]
        if rtype == "A":
            rdata = next(ipv4)
        elif rtype == "AAAA":
            rdata = next(ipv6)
        elif rtype == "CNAME" or rtype == "DNAME" or rtype == "NS":
            rdata = rdata
            if not rdata:
                rdata = "somedomain"
        elif rtype == "SOA":
            rdata = "ns1.outside.edu. root.campus.edu. 8 6048 4000 2419200 6048"
            found_soa = True
        elif rtype == "TXT":
            rdata = "some text"
        formatted_records.add((record_name[0], rtype, rdata))
    if not found_soa:
        # All the records and query will be guaranteed to be in the same zone
        zone_file = 'test.\t500\tIN\tSOA\tns1.outside.edu. root.campus.edu. 8 6048 4000 2419200 6048\n'
        zone_file += 'test.\t500\tIN\tNS\tns1.outside.edu.\n'
        for record in formatted_records:
            rdata = record[2]
            if record[1] in ["CNAME", "DNAME", "NS"]:
                rdata = record[2] + ".test."
            zone_file += f'{record[0]}.test.\t500\tIN\t{record[1]}\t{rdata}\n'
        zone_origin = "test."
    else:
        zone_file = ""
        # Some records might be out-of-zone which most implementations ignore
        for record in formatted_records:
            if record[1] == "SOA":
                zone_origin = record[0]
                zone_file = f'{record[0]}\t500\tIN\t{record[1]}\t{record[2]}\n' + \
                            f'{record[0]}\t500\tIN\tNS\tns1.outside.edu.\n' + zone_file
            else:
                zone_file += f'{record[0]}\t500\tIN\t{record[1]}\t{record[2]}\n'
    return (zone_file, zone_origin)


def valid_zone_check():
    domain_name = ast.String(3)

    label = re.choice(re.text('*'), re.chars('a', 'z'))
    valid_dn_re = re.seq(label, re.star(re.seq(re.text('.'), label)))

    record_type = ast.Enum(
        "RecordType", ["A", "AAAA", "NS", "TXT", "CNAME", "DNAME", "SOA"])
    record = ast.Struct("ResourceRecord", domain_name=domain_name,
                        record_type=record_type, rdata=ast.String(3))

    zone = ast.Array(record, 2)
    zone_parameter = ast.Parameter(
        "zone", ast.Alias("Zone", zone), description="The zone to check for validity. The zone file is a collection of resource records which can have a variety of record types.")
    zone_result = ast.Parameter("result", ast.Bool(
    ), description="Whether the DNS zone file is valid or not.")

    is_valid_zone = ast.Function(
        "is_valid_zone",
        "a function that validates a DNS zone file according to the DNS RFC semantics. "
        "Include as many important semantic condition checks as possible that must hold for a zone file to be considered valid and well-formed. "
        "Consider different record types and their semantics. ",
        [zone_parameter, zone_result],
        precondition=zone_parameter.forall(
            lambda r: r.get_field("domain_name").matches(valid_dn_re)),
    )

    output_dir = "ValidZone"
    inputs = run(is_valid_zone, k=10, debug=output_dir, timeout_sec=300)
    query_zone_tuples = []
    for input in inputs:
        query_zone_tuples.append(create_zone(input))
    generate_zone_query_inputs_from_zone(query_zone_tuples, output_dir)


def full_query_lookup():
    domain_name = ast.String(3)

    label = re.choice(re.text('*'), re.chars('a', 'z'))
    valid_dn_re = re.seq(label, re.star(re.seq(re.text('.'), label)))

    record_type = ast.Enum(
        "RecordType", ["A", "AAAA", "NS", "TXT", "CNAME", "DNAME", "SOA"])
    record = ast.Struct("ResourceRecord", domain_name=domain_name,
                        record_type=record_type, rdata=ast.String(3))

    zone = ast.Array(record, 2)
    zone_parameter = ast.Parameter(
        "zone", ast.Alias("Zone", zone), description="The zone file as a list of resource records which can have CNAME, DNAME, NS among other record types or wildcard records.")

    query = ast.Struct("DNSQuery", domain_name=domain_name,
                       record_type=record_type)
    query_parameter = ast.Parameter(
        "query", query, description="The input query for lookup which has the domain name and record type")

    response_parameter = ast.Parameter("response", ast.String(
        3), description="The response to the DNS query.")

    dns_query_lookup = ast.Function(
        "dns_query_lookup",
        "a function that implements a DNS query lookup on a given zone. "
        "Assume there is no cache and there is only the input zone file to answer the query. "
        "Assume the zone file is valid and all the record domain names in the zone are not relative domain names. "
        "The input query has a domain name and record type. The function should handle CNAME, DNAME, NS, A, AAAA, TXT, SOA, and wildcard cases among other types. "
        "It should return the DNS response. ",
        [zone_parameter, query_parameter, response_parameter],
        precondition=zone_parameter.forall(
            lambda r: ((r.get_field("record_type") == 5).implies(r.get_field("rdata").matches(valid_dn_re))) &
            ((r.get_field("record_type") == 4).implies(r.get_field("rdata").matches(valid_dn_re))) &
            (r.get_field("domain_name").matches(valid_dn_re)))
        & query_parameter.get_field("domain_name").matches(valid_dn_re),
    )
    if SIGCOMM:
        output_dir = pathlib.Path("SIGCOMM//FullLookup")
        inputs = run(dns_query_lookup, k=10,
                     debug=output_dir, timeout_sec=300)
        query_zone_tuples = []
        for input in inputs:
            zone_file, zone_origin = create_zone(input)
            queries = []
            query_name = input[1]["domain_name"]
            query_type = input[1]["record_type"]
            if zone_origin == "test.":
                queries.append(
                    {"Name": query_name + ".test.", "Type": query_type})
            else:
                queries.append({"Name": query_name, "Type": query_type})
            query_zone_tuples.append((queries, zone_file))
        generate_zone_query_pair_inputs(query_zone_tuples, output_dir)
    else:
        output_dir = pathlib.Path("FullLookup")
        for i in range(0, 10):
            for temperature in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
                (output_dir / f"{temperature}" /
                 f"{i}").mkdir(exist_ok=True, parents=True)
                inputs = run(dns_query_lookup, k=12,
                             debug=output_dir / f"{temperature}" / f"{i}", temperature_value=temperature, timeout_sec=300)
                query_zone_tuples = []
                for input in inputs:
                    zone_file, zone_origin = create_zone(input)
                    queries = []
                    query_name = input[1]["domain_name"]
                    query_type = input[1]["record_type"]
                    if zone_origin == "test.":
                        queries.append(
                            {"Name": query_name + ".test.", "Type": query_type})
                    else:
                        queries.append(
                            {"Name": query_name, "Type": query_type})
                    query_zone_tuples.append((queries, zone_file))
                generate_zone_query_pair_inputs(
                    query_zone_tuples, (output_dir / f"{temperature}" / f"{i}"))


def return_code_lookup():
    domain_name = ast.String(3)

    label = re.choice(re.text('*'), re.chars('a', 'z'))
    valid_dn_re = re.seq(label, re.star(re.seq(re.text('.'), label)))

    record_type = ast.Enum(
        "RecordType", ["A", "AAAA", "NS", "TXT", "CNAME", "DNAME", "SOA"])
    record = ast.Struct("ResourceRecord", domain_name=domain_name,
                        record_type=record_type, rdata=ast.String(3))

    zone = ast.Array(record, 2)
    zone_parameter = ast.Parameter(
        "zone", ast.Alias("Zone", zone), description="The zone file as a list of resource records which can have CNAME, DNAME, NS among other record types or wildcard records.")

    query = ast.Struct("DNSQuery", domain_name=domain_name,
                       record_type=record_type)
    query_parameter = ast.Parameter(
        "query", query, description="The input query for lookup which has the domain name and record type")

    response_parameter = ast.Parameter("response", ast.String(
        2), description="The return code of the DNS response to the query.")

    dns_query_lookup_rcode = ast.Function(
        "dns_query_lookup_rcode",
        "a function that returns the RCODE of the DNS response to the input query using the input zone file. "
        "Assume there is no cache and there is only the input zone file to answer the query. "
        "Assume the zone file is valid and all the record domain names in the zone are not relative domain names. "
        "The input query has a domain name and record type. The function should handle CNAME, DNAME, NS, A, AAAA, TXT, SOA, and wildcard cases among other types. "
        "It should return the RCODE of the DNS response that a DNS nameserver will respond with to the query using this zone file as a shortened two-letter code. ",
        [zone_parameter, query_parameter, response_parameter],
        precondition=zone_parameter.forall(
            lambda r: ((r.get_field("record_type") == 5).implies(r.get_field("rdata").matches(valid_dn_re))) &
            ((r.get_field("record_type") == 4).implies(r.get_field("rdata").matches(valid_dn_re))) &
            (r.get_field("domain_name").matches(valid_dn_re)))
        & query_parameter.get_field("domain_name").matches(valid_dn_re),
    )
    if SIGCOMM:
        output_dir = pathlib.Path("SIGCOMM//RCODE")
        inputs = run(dns_query_lookup_rcode, k=10,
                     debug=output_dir, timeout_sec=300)
        query_zone_tuples = []
        for input in inputs:
            zone_file, zone_origin = create_zone(input)
            queries = []
            query_name = input[1]["domain_name"]
            query_type = input[1]["record_type"]
            if zone_origin == "test.":
                queries.append(
                    {"Name": query_name + ".test.", "Type": query_type})
            else:
                queries.append({"Name": query_name, "Type": query_type})
            query_zone_tuples.append((queries, zone_file))
        generate_zone_query_pair_inputs(query_zone_tuples, output_dir)
    else:
        output_dir = pathlib.Path("RCODE")
        for i in range(0, 10):
            for temperature in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
                (output_dir / f"{temperature}" /
                 f"{i}").mkdir(exist_ok=True, parents=True)
                inputs = run(dns_query_lookup_rcode, k=12,
                             debug=output_dir / f"{temperature}" / f"{i}", temperature_value=temperature, timeout_sec=300)
                query_zone_tuples = []
                for input in inputs:
                    zone_file, zone_origin = create_zone(input)
                    queries = []
                    query_name = input[1]["domain_name"]
                    query_type = input[1]["record_type"]
                    if zone_origin == "test.":
                        queries.append(
                            {"Name": query_name + ".test.", "Type": query_type})
                    else:
                        queries.append(
                            {"Name": query_name, "Type": query_type})
                    query_zone_tuples.append((queries, zone_file))
                generate_zone_query_pair_inputs(
                    query_zone_tuples, (output_dir / f"{temperature}" / f"{i}"))


def authoritative_lookup():
    domain_name = ast.String(3)

    label = re.choice(re.text('*'), re.chars('a', 'z'))
    valid_dn_re = re.seq(label, re.star(re.seq(re.text('.'), label)))

    record_type = ast.Enum(
        "RecordType", ["A", "AAAA", "NS", "TXT", "CNAME", "DNAME", "SOA"])
    record = ast.Struct("ResourceRecord", domain_name=domain_name,
                        record_type=record_type, rdata=ast.String(3))

    zone = ast.Array(record, 2)
    zone_parameter = ast.Parameter(
        "zone", ast.Alias("Zone", zone), description="The zone file as a list of resource records which can have CNAME, DNAME, NS among other record types or wildcard records.")

    query = ast.Struct("DNSQuery", domain_name=domain_name,
                       record_type=record_type)
    query_parameter = ast.Parameter(
        "query", query, description="The input query for lookup which has the domain name and record type")

    response_parameter = ast.Parameter("response", ast.Bool(
    ), description="Whether the DNS response will have the authoritative flag (AA) bit set or not.")

    dns_query_lookup_authoritative = ast.Function(
        "dns_query_lookup_authoritative",
        "a function that returns whether the DNS response for the input query using the input zone file will be authoritative or not. "
        "Assume there is no cache and there is only the input zone file to answer the query. "
        "Assume the zone file is valid and all the record domain names in the zone are not relative domain names. "
        "The input query has a domain name and record type. The function should handle CNAME, DNAME, NS, A, AAAA, TXT, SOA, and wildcard cases among other types. "
        "It should return whether a nameserver answering the query using the input zone file will set the AA flag in the response. ",
        [zone_parameter, query_parameter, response_parameter],
        precondition=zone_parameter.forall(
            lambda r: ((r.get_field("record_type") == 5).implies(r.get_field("rdata").matches(valid_dn_re))) &
            ((r.get_field("record_type") == 4).implies(r.get_field("rdata").matches(valid_dn_re))) &
            ((r.get_field("record_type") == 2).implies(r.get_field("rdata").matches(valid_dn_re))) &
            (r.get_field("domain_name").matches(valid_dn_re)))
        & query_parameter.get_field("domain_name").matches(valid_dn_re),
    )
    if SIGCOMM:
        output_dir = pathlib.Path("SIGCOMM//Authoritative")
        inputs = run(dns_query_lookup_authoritative, k=10,
                     debug=output_dir, timeout_sec=300)
        query_zone_tuples = []
        for input in inputs:
            zone_file, zone_origin = create_zone(input)
            queries = []
            query_name = input[1]["domain_name"]
            query_type = input[1]["record_type"]
            if zone_origin == "test.":
                queries.append(
                    {"Name": query_name + ".test.", "Type": query_type})
            else:
                queries.append({"Name": query_name, "Type": query_type})
            query_zone_tuples.append((queries, zone_file))
        generate_zone_query_pair_inputs(query_zone_tuples, output_dir)
    else:
        output_dir = pathlib.Path("Authoritative")
        for i in range(0, 10):
            for temperature in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
                (output_dir / f"{temperature}" /
                 f"{i}").mkdir(exist_ok=True, parents=True)
                inputs = run(dns_query_lookup_authoritative, k=12,
                             debug=output_dir / f"{temperature}" / f"{i}", temperature_value=temperature, timeout_sec=300)
                query_zone_tuples = []
                for input in inputs:
                    zone_file, zone_origin = create_zone(input)
                    queries = []
                    query_name = input[1]["domain_name"]
                    query_type = input[1]["record_type"]
                    if zone_origin == "test.":
                        queries.append(
                            {"Name": query_name + ".test.", "Type": query_type})
                    else:
                        queries.append(
                            {"Name": query_name, "Type": query_type})
                    query_zone_tuples.append((queries, zone_file))
                generate_zone_query_pair_inputs(
                    query_zone_tuples, (output_dir / f"{temperature}" / f"{i}"))


def loop_count():
    domain_name = ast.String(3)

    label = re.choice(re.text('*'), re.chars('a', 'z'))
    valid_dn_re = re.seq(label, re.star(re.seq(re.text('.'), label)))

    record_type = ast.Enum(
        "RecordType", ["A", "AAAA", "NS", "TXT", "CNAME", "DNAME", "SOA"])
    record = ast.Struct("ResourceRecord", domain_name=domain_name,
                        record_type=record_type, rdata=ast.String(3))

    zone = ast.Array(record, 2)
    zone_parameter = ast.Parameter(
        "zone", ast.Alias("Zone", zone), description="The zone file as a list of resource records which can have CNAME, DNAME, NS among other record types or wildcard records.")

    query = ast.Struct("DNSQuery", domain_name=domain_name,
                       record_type=record_type)
    query_parameter = ast.Parameter(
        "query", query, description="The input query to lookup which has the domain name and record type")

    response_parameter = ast.Parameter("response", ast.Int(
        32), description="The number of times the query will be rewritten and redirected to the same zone file.")
    loop_count = ast.Function(
        "dns_query_lookup_count",
        "A function that counts the number of times the query will be rewritten and redirected to the same zone file. "
        "If it is more than 10, it is considered a loop and the function should return 15. "
        "The query can be rewritten due to CNAME, DNAME, wildcard records or a combination of them. "
        "For example, consider the zone file:\n"
        "  foo.com. 500 IN SOA ns1.outside.edu. root.campus.edu. 8 6048 86400 2419200 6048\n"
        "  bar.foo.com. 500 IN CNAME other.foo.com.\n"
        "  *.foo.com. 500 IN CNAME test.foo.com.\n"
        "  test.foo.com. 500 IN A 1.2.3.4\n"
        "The query <bar.foo.com., A> will be first rewritten to <other.foo.com., A>, which will  be next rewritten to <test.foo.com., A> using wildcard CNAME record and resolved eventually to IP address 1.2.3.4. "
        "The function should return 2 as the query is rewritten twice.",
        [zone_parameter, query_parameter, response_parameter],
        precondition=zone_parameter.forall(
            lambda r: ((r.get_field("record_type") == 5).implies(r.get_field("rdata").matches(valid_dn_re))) &
            ((r.get_field("record_type") == 4).implies(r.get_field("rdata").matches(valid_dn_re))) &
            (r.get_field("domain_name").matches(valid_dn_re)))
        & query_parameter.get_field("domain_name").matches(valid_dn_re),
    )
    if SIGCOMM:
        output_dir = pathlib.Path("SIGCOMM//LoopCount")
        inputs = run(loop_count, k=10,
                     debug=output_dir, timeout_sec=300)
        query_zone_tuples = []
        for input in inputs:
            zone_file, zone_origin = create_zone(input)
            queries = []
            query_name = input[1]["domain_name"]
            query_type = input[1]["record_type"]
            if zone_origin == "test.":
                queries.append(
                    {"Name": query_name + ".test.", "Type": query_type})
            else:
                queries.append({"Name": query_name, "Type": query_type})
            query_zone_tuples.append((queries, zone_file))
        generate_zone_query_pair_inputs(query_zone_tuples, output_dir)
    else:
        output_dir = pathlib.Path("LoopCount")
        for i in range(0, 10):
            for temperature in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
                (output_dir / f"{temperature}" /
                 f"{i}").mkdir(exist_ok=True, parents=True)
                inputs = run(loop_count, k=12,
                             debug=output_dir / f"{temperature}" / f"{i}", temperature_value=temperature, timeout_sec=300)
                query_zone_tuples = []
                for input in inputs:
                    zone_file, zone_origin = create_zone(input)
                    queries = []
                    query_name = input[1]["domain_name"]
                    query_type = input[1]["record_type"]
                    if zone_origin == "test.":
                        queries.append(
                            {"Name": query_name + ".test.", "Type": query_type})
                    else:
                        queries.append(
                            {"Name": query_name, "Type": query_type})
                    query_zone_tuples.append((queries, zone_file))
                generate_zone_query_pair_inputs(
                    query_zone_tuples, (output_dir / f"{temperature}" / f"{i}"))


def zonecut():
    domain_name = ast.String(3)

    label = re.choice(re.text('*'), re.chars('a', 'z'))
    valid_dn_re = re.seq(label, re.star(re.seq(re.text('.'), label)))
    
    record_type = ast.Enum(
        "RecordType", ["A", "AAAA", "NS", "TXT", "CNAME", "DNAME", "SOA"])
    record = ast.Struct("ResourceRecord", domain_name=domain_name,
                        record_type=record_type, rdata=ast.String(3))

    zone = ast.Array(record, 2)
    zone_parameter = ast.Parameter(
        "zone", ast.Alias("Zone", zone), description="The zone file as a list of resource records which can have CNAME, DNAME, NS among other record types or wildcard records.")

    query = ast.Struct("DNSQuery", domain_name=domain_name,
                       record_type=record_type)
    query_parameter = ast.Parameter(
        "query", query, description="The input query for lookup which has the domain name and record type")

    response_parameter = ast.Parameter("response", ast.Int(
        32), description="Whether the query will be resolved by a zone cut or not and whether the nameserver will respond with glue records")

    dns_query_lookup_zonecut = ast.Function(
        "dns_query_lookup_zonecut",
        "a function that returns whether the DNS response for the input query using the input zone file will be through NS records at the zone cut and whether it will have glue records. "
        "Assume there is no cache and there is only the input zone file to answer the query. "
        "Assume the zone file is valid and all the record domain names in the zone are not relative domain names. "
        "The input query has a domain name and record type."
        "It should return 0 if there is no zone cut NS records relevant to the query."
        "It should return 1 if there are relevant zone cut NS records for the query but there are no glue records"
        "It should return 2 if there are relevant zone cut NS records for the query and also glue records in the zone file.",
        [zone_parameter, query_parameter, response_parameter],
        precondition=zone_parameter.forall(
            lambda r: ((r.get_field("record_type") == 5).implies(r.get_field("rdata").matches(valid_dn_re))) &
            ((r.get_field("record_type") == 4).implies(r.get_field("rdata").matches(valid_dn_re))) &
            ((r.get_field("record_type") == 2).implies(r.get_field("rdata").matches(valid_dn_re))) &
            (r.get_field("domain_name").matches(valid_dn_re)))
        & query_parameter.get_field("domain_name").matches(valid_dn_re),
    )

    output_dir = "Zonecut"
    inputs = run(dns_query_lookup_zonecut, k=5, debug=output_dir)
    query_zone_tuples = []
    for input in inputs:
        zone_file, zone_origin = create_zone(input)
        queries = []
        query_name = input[1]["domain_name"]
        query_type = input[1]["record_type"]
        if zone_origin == "test.":
            queries.append({"Name": query_name + ".test.", "Type": query_type})
        else:
            queries.append({"Name": query_name, "Type": query_type})
        query_zone_tuples.append((queries, zone_file))
    generate_zone_query_pair_inputs(query_zone_tuples, output_dir)


def false_function_to_check_regex():
    domain_name = ast.String(5)

    label = re.choice(re.text('*'), re.chars('a', 'z'))
    valid_dn_re = re.seq(label, re.star(re.seq(re.text('.'), label)))

    query_dn = ast.Parameter("domain_name", domain_name,
                             description="The domain name input")
    result = ast.Parameter("result", ast.Bool(
    ), description="The return value")

    false_function = ast.Function(
        "false_function",
        "a function that returns false for all inputs.",
        [query_dn, result],
        precondition=(query_dn.matches(valid_dn_re)),
    )

    output_dir = "Regex"
    inputs = run(false_function, k=10, debug=output_dir)
    print(f"Total inputs {len(inputs)}")
    
if __name__ == "__main__":
    # false_function_to_check_regex()
    # validate_domain_name()
    # cname_match_check()
    # dname_match_check()
    # ipv4_match_check()
    # ipv4_match_check_no_precondition()
    wildcard_match_check()
    # valid_zone_check()
    # full_query_lookup()
    # loop_count()
    # return_code_lookup()
    # authoritative_lookup()
    # zonecut()
    pass
