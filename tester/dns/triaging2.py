"""
Fingerprint and group the tests that resulted in differences based on the model case (for valid zone
files) as well as the unique implementations in each group from the responses.
For invalid zone files, they are already separated into different directories based on the condition
violated. Therefore, only the unique implementations in each group is used.

usage: triaging.py [-h] [-path DIRECTORY_PATH]

optional arguments:
  -h, --help            show this help message and exit
  -path DIRECTORY_PATH  The path to the directory containing Differences directory.
                        Searches recursively (default: Results/)
"""

import json
import pathlib
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser, SUPPRESS
from collections import defaultdict
from typing import Union

import dns

from test_implementations import DIFFERENCES


def response_equality_check(response_a: Union[str, dns.message.Message],
                            response_b: Union[str, dns.message.Message]):
    """
    Checks whether the two input responses are same or not.

    :param response_a: The first response (expected response)
    :param response_b: The second response

    Either of the responses can be a string if there was an error during querying.
    """
    if type(response_a) != type(response_b):
        return ("MISMATCH",)
    if isinstance(response_a, str):
        return ("STRING", response_a == response_b)
    if response_a.rcode() != response_b.rcode():
        return ("RCODE", dns.rcode.to_text(response_a.rcode()), dns.rcode.to_text(response_b.rcode()))
    a_flags = dns.flags.to_text(response_a.flags).split()
    if 'RA' in a_flags:
        a_flags.remove('RA')
    b_flags = dns.flags.to_text(response_b.flags).split()
    if 'RA' in b_flags:
        b_flags.remove('RA')
    if a_flags != b_flags:
        return ("FLAGS", a_flags, b_flags)

    def check_section(section_a, section_b):
        for record in section_a:
            if record not in section_b:
                return False
        for record in section_b:
            if record not in section_a:
                return False
        return True

    if not check_section(response_a.question, response_b.question):
        return ("QUESTION",)
    if not check_section(response_a.answer, response_b.answer):
        return ("ANSWER",)
    if not check_section(response_a.additional, response_b.additional):
        return ("ADDITIONAL",)
    # Check authority section only when both the answer sections are non-empty
    # as implementations can add SOA/NS records to the authority section
    if not (len(response_a.answer) and len(response_b.answer)):
        if not check_section(response_a.authority, response_b.authority):
            return ("AUTHORITY",)
    # raise error that it should not reach here
    raise Exception("Should not reach here")


def fingerprint_group_tests(dir_path: pathlib.Path) -> None:
    """
    Fingerprints each test with the model case if available and the unique
    implementations in each group from the responses.
    Then groups the tests with the same fingerprint and outputs the groups as
    a JSON file.

    :param dir_path: The path to the directory containing the Differences directory
    """

    difference_zones = list((dir_path / DIFFERENCES).iterdir())
    vectors_count = defaultdict(lambda: defaultdict(int))
    vectors_full = defaultdict(lambda: defaultdict(list))
    old_new_differences = defaultdict(list)
    for diff in difference_zones:
        with open(diff, 'r') as diff_fp:
            diff_json = json.load(diff_fp)
        zone_lines = []
        zone_wildcard = False
        with open(dir_path / "ZoneFiles" / (diff.stem + ".txt"), 'r') as zone_fp:
            for line in zone_fp:
                zone_lines.append(line.strip())
                record_name = line.split("\t")[0]
                zone_wildcard = zone_wildcard or "*" in record_name
        for difference in diff_json:
            groupservers_response = []
            query_wildcard = "*" in difference["Query Name"]
            for group in difference["Groups"]:
                servers = set(group["Server/s"].strip().split())
                if servers:
                    groupservers_response.append(
                        (frozenset(servers), group["Response"]))
            groupservers_response.sort(key=lambda x: len(x[0]), reverse=True)
            if "No response" == groupservers_response[0][1]:
                expected_responses = "No response"
            else:
                expected_responses = dns.message.from_text(
                    '\n'.join(groupservers_response[0][1]))
            # Find reasons for differences for minority groups
            for group in groupservers_response[1:]:
                servers, response = group
                if "No response" == response:
                    group_response = "No response"
                else:
                    group_response = dns.message.from_text('\n'.join(response))
                fingerprint = response_equality_check(
                    expected_responses, group_response)
                final_fingerprint = fingerprint + \
                    (dir_path.stem, )
                for server in servers:
                    vectors_count[server][str(final_fingerprint)] += 1
                    full_details = {
                        "Zone Id": diff.stem,
                        "Zone": zone_lines,
                        "Response": difference
                    }
                    vectors_full[server][str(final_fingerprint)].append(
                        full_details)
            # Find reasons for differences for same implementation but different versions
            for group in groupservers_response:
                servers, response = group
                for server in servers:
                    name, version = server.split("_")
                    other = name + "_" + \
                        ("oct" if version == "latest" else "latest")
                    if other in servers:
                        continue
                    for othergroup in groupservers_response:
                        if other in othergroup[0]:
                            full_details = {
                                "Category": dir_path.stem,
                                "Zone Id": diff.stem,
                                "Zone": zone_lines,
                                "Response": difference
                            }
                            if full_details not in old_new_differences[name]:
                                old_new_differences[name].append(
                                    full_details)

    output = {}
    output["A-Summary"] = vectors_count
    output["B-OldNewDifferences"] = old_new_differences
    output["C-Details"] = vectors_full
    with open(dir_path / f"Fingerprints_New_1.json", 'w') as cj_fp:
        json.dump(output, cj_fp, indent=2, sort_keys=True)
    return output


def fingerprint_group_tests_helper(input_dir: pathlib.Path) -> None:
    """
    :param input_dir: The input directory
    """
    # Exit if the inputted path does not exist or is not a directory.
    if not (input_dir.exists() or input_dir.is_dir()):
        return
    differences_dir = input_dir / DIFFERENCES
    if differences_dir.exists() and differences_dir.is_dir():
        fingerprint_group_tests(input_dir)
    else:
        if input_dir.is_dir():
            for subdir in input_dir.iterdir():
                fingerprint_group_tests_helper(subdir)


def aggregate_results():
    dir_names = ["CNAME", "DNAME", "IPv4", "Wildcard",
                 "Authoritative", "FullLookup", "LoopCount", "RCODE"]
    gcr_path = pathlib.Path("/opt/Eywa/")
    overall_output = {}
    overall_output["A-Summary"] = defaultdict(lambda: defaultdict(int))
    overall_output["B-OldNewDifferences"] = defaultdict(list)
    overall_output["C-Details"] = defaultdict(lambda: defaultdict(list))
    for dir_name in dir_names:
        output = fingerprint_group_tests(gcr_path / dir_name)
        for key, value in output["A-Summary"].items():
            for fingerprint, count in value.items():
                overall_output["A-Summary"][key][fingerprint] += count
        for key, value in output["B-OldNewDifferences"].items():
            overall_output["B-OldNewDifferences"][key].extend(value)
        for key, value in output["C-Details"].items():
            for fingerprint, details in value.items():
                overall_output["C-Details"][key][fingerprint].extend(details)
        print(f"Finished {dir_name}")
    output_path = gcr_path / "Fingerprints_Aggregate"
    output_path.mkdir(exist_ok=True)
    with open(output_path / f"Summary.json", 'w') as cj_fps:
        json.dump(overall_output["A-Summary"],
                  cj_fps, indent=2, sort_keys=True)
    with open(output_path / f"OldNewDifferences.json", 'w') as cj_fps:
        json.dump(overall_output["B-OldNewDifferences"],
                  cj_fps, indent=2, sort_keys=True)
    for key, value in overall_output["C-Details"].items():
        with open(output_path / f"Details_{key}.json", 'w') as cj_fps:
            json.dump(value, cj_fps, indent=2, sort_keys=True)


def max_min_c_code_count():
    dir_names = ["CNAME", "DNAME", "Wildcard", "IPv4",
                 "FullLookup", "RCODE", "Authoritative", "LoopCount", ]
    gcr_path = pathlib.Path("/opt/Eywa/SIGCOMM")
    for dir_name in dir_names:
        # Find all the C files in the directory
        c_files = list((gcr_path / dir_name).glob("*.c"))
        # Find the maximum and minimum number of C files in the directory
        max_c_files = max(c_files, key=lambda x: len(
            x.read_text().split("\n")))
        max_len = len(max_c_files.read_text().split("\n"))
        min_c_files = min(c_files, key=lambda x: len(
            x.read_text().split("\n")))
        min_len = len(min_c_files.read_text().split("\n"))
        # Count the number of files in the Zonefiles directory
        zone_files = list((gcr_path / dir_name / "ZoneFiles").glob("*.txt"))
        print(f"{dir_name:14} {min_len} / {max_len}  {len(zone_files)}")

def diff_count():
    dir_names = ["CNAME", "DNAME", "Wildcard", "IPv4",
                 "FullLookup", "RCODE", "Authoritative", "LoopCount", ]
    gcr_path = pathlib.Path("/opt/Eywa/SIGCOMM")
    sum_total = 0
    sum_diff = 0
    for dir_name in dir_names:
        total_tests = len(list((gcr_path / dir_name / "ZoneFiles").glob("*.txt")))
        total_diff = len(list((gcr_path / dir_name / "Differences").glob("*.json")))
        print(f"{dir_name:14} {total_tests} {total_diff}")
        sum_total += total_tests
        sum_diff += total_diff
    print(f"Total {sum_total} {sum_diff}")

if __name__ == '__main__':
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter,
                            description='Fingerprint and group the tests that resulted in '
                            'differences based on the model case (for valid zone files) as '
                            'well as the unique implementations in each group from '
                            'the responses. For invalid zone files, they are already '
                            'separated into different directories based on the condition violated. '
                            'Therefore, only the unique implementations in each group is used.')
    parser.add_argument('-path', metavar='DIRECTORY_PATH', default=SUPPRESS,
                        help='The path to the directory containing Differences directory.'
                        ' Searches recursively (default: Results/)')
    args = parser.parse_args()
    if "path" in args:
        directory_path = pathlib.Path(args.path)
    else:
        directory_path = pathlib.Path("Results/")
    diff_count()
    # max_min_c_code_count()
    # aggregate_results()
    # fingerprint_group_tests_helper(directory_path)
