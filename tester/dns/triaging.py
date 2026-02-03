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
import sys
from argparse import SUPPRESS, ArgumentDefaultsHelpFormatter, ArgumentParser
from collections import defaultdict
from typing import Any, Dict

from test_implementations import (DIFFERENCES, QUERIES,
                                  QUERY_RESPONSES)


def fingerprint_group_tests(dir_path: pathlib.Path,
                            model_cases: Dict[str, Dict[str, str]]) -> None:
    """
    Fingerprints each test with the model case if available and the unique
    implementations in each group from the responses.
    Then groups the tests with the same fingerprint and outputs the groups as
    a JSON file.

    :param dir_path: The path to the directory containing the Differences directory
    """
    # Either all the zone files that resulted in some difference have the model cases
    # or none of them have it.
    # If all of them are not True and there is a True in the list then print error
    # and return: All of them are not true - there is at least one False and there
    # is a True => some zones have model cases and some don't.
    # The only acceptable scenarios are the list being all true and all false
    difference_zones = list((dir_path / DIFFERENCES).iterdir())
    has_model_cases = [zone.stem in model_cases for zone in difference_zones]
    if not all(model_cases) and any(has_model_cases):
        sys.exit(
            f'Some of the tests have model cases and other don\'t in {dir_path}')
    preprocessors_summary = dir_path / f"Preprocessor_Fingerprints.json"
    ignore_zones = set()
    if preprocessors_summary.exists():
        with open(preprocessors_summary, 'r') as ps_fp:
            preprocessors_summary_json = json.load(ps_fp)
        for k, v in preprocessors_summary_json['Summary'].items():
            if "1" in k:
                ignore_zones.update(v)
    vectors = defaultdict(set)
    old_new_differences = defaultdict(list)
    for diff in difference_zones:
        with open(diff, 'r') as diff_fp:
            diff_json = json.load(diff_fp)
        for difference in diff_json:
            query_str = difference["Query Name"] + \
                ":" + difference["Query Type"]
            zoneid = diff.stem
            if zoneid in ignore_zones:
                continue
            groups = difference["Groups"]
            frozen_groups = []
            for group in groups:
                servers = set(group["Server/s"].strip().split())
                if servers:
                    frozen_groups.append(frozenset(servers))
            if len(frozen_groups) > 1:
                if zoneid in model_cases:
                    test_model_case = model_cases[zoneid][query_str]
                    vectors[(test_model_case, frozenset(frozen_groups))].add(
                        (zoneid, query_str))
                else:
                    vectors[("-", frozenset(frozen_groups))
                            ].add((zoneid, query_str))
            for group in frozen_groups:
                for impl in group:
                    name, version = impl.split("_")
                    other = name + "_" + \
                        ("oct" if version == "latest" else "latest")
                    if other in group:
                        continue
                    for othergroup in frozen_groups:
                        if other in othergroup:
                            if zoneid.ljust(6) + query_str not in old_new_differences[name]:
                                old_new_differences[name].append(
                                    zoneid.ljust(6) + query_str)
    summary = []
    keys = sorted(vectors.keys())
    output_json = defaultdict(list)
    model_cases_present = set(k[0] for k in keys)
    for model_case in model_cases_present:
        for k in keys:
            if k[0] != model_case:
                continue
            sorted_groups = sorted(k[1], key=len, reverse=True)
            json_groups = []
            groups_summary = ''
            for grp in sorted_groups:
                groups_summary += f' {{{",".join(grp)}}} '
                json_groups.append(list(grp))
            if model_case != '-':
                summary.append(
                    f'{model_case} {len(vectors[k])} {groups_summary}')
                output_json[model_case].append({
                    'Groups': json_groups,
                    'Count': len(vectors[k]),
                    'Tests': list(vectors[k])
                })
            else:
                summary.append(
                    f'{len(vectors[k])} {groups_summary}')
                output_json["Fingerprints"].append({
                    'Groups': json_groups,
                    'Count': len(vectors[k]),
                    'Tests': list(vectors[k])
                })
    output = {}  # type: Dict[str, Any]
    output["Summary"] = summary
    print("Length of summary: ", len(summary))
    output["OldNewDifferences"] = old_new_differences
    output["Details"] = output_json
    with open(dir_path / f"Fingerprints.json", 'w') as cj_fp:
        json.dump(output, cj_fp, indent=2)


def get_model_cases(dir_path: pathlib.Path) -> Dict[str, Dict[str, str]]:
    """
    Returns the Zen model case for each test if it exists.

    :param dir_path: The path to the directory containing the DIFFERENCES directory.
    """
    model_cases = defaultdict(dict)  # type: Dict[str, Dict[str, str]]
    queries_dir = dir_path / QUERIES
    expected_res_dir = dir_path / QUERY_RESPONSES
    tag_dir = None
    if queries_dir.exists() and queries_dir.is_dir():
        tag_dir = queries_dir
    elif expected_res_dir.exists() and expected_res_dir.is_dir():
        tag_dir = expected_res_dir
    if isinstance(tag_dir, pathlib.Path):
        for queries_file in tag_dir.iterdir():
            with open(queries_file, 'r') as qf_fp:
                queries_info = json.load(qf_fp)
                for qinfo in queries_info:
                    if "ZenResponseTag" in qinfo:
                        query_str = qinfo["Query"]["Name"] + ":" +\
                            qinfo["Query"]["Type"]
                        model_cases[queries_file.stem][query_str] = qinfo["ZenResponseTag"]
    return model_cases


def fingerprint_group_tests_helper(input_dir: pathlib.Path) -> None:
    """
    :param input_dir: The input directory
    """
    # Exit if the inputted path does not exist or is not a directory.
    if not (input_dir.exists() or input_dir.is_dir()):
        return
    differences_dir = input_dir / DIFFERENCES
    if differences_dir.exists() and differences_dir.is_dir():
        model_cases = get_model_cases(input_dir)
        fingerprint_group_tests(input_dir, model_cases)
    else:
        if input_dir.is_dir():
            for subdir in input_dir.iterdir():
                fingerprint_group_tests_helper(subdir)


def preprocessors_summary(input_dir: pathlib.Path) -> None:
    preprocess_dir = input_dir / f"PreprocessorOutputs"
    summary = defaultdict(list)
    if not (preprocess_dir.exists() or preprocess_dir.is_dir()):
        return
    fingerprints_file = input_dir / f"Preprocessor_Fingerprints.json"
    all_keys = list()
    old_new_differences = defaultdict(list)
    for zone in preprocess_dir.iterdir():
        with open(zone, 'r') as zone_fp:
            data = json.load(zone_fp)
            file_keys = list(data.keys())
            if all_keys and all_keys != file_keys:
                print("Keys not matching: ", zone)
            all_keys = file_keys
            codes = []
            for k in file_keys:
                codes.append(data[k]['Code'])
                name, version = k.split("_")
                other = name + "_" + \
                    ("oct" if version == "latest" else "latest")
                if other in file_keys and data[k]['Code'] != data[other]['Code']:
                    if zone.stem not in old_new_differences[name]:
                        old_new_differences[name].append(zone.stem)
            summary[str(codes)].append(zone.stem)
    output = {}
    counts = {}
    for k, v in summary.items():
        counts[k] = len(v)
    output["Counts"] = counts
    output["OldNewDifferences"] = old_new_differences
    output["Summary"] = summary
    with open(fingerprints_file, 'w') as cj_fp:
        json.dump(output, cj_fp, indent=2)


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
    parser.add_argument('-preprocess', action='store_true', default=False,
                        help='Group them based on the preprocessor outputs.')
    args = parser.parse_args()
    if "path" in args:
        directory_path = pathlib.Path(args.path)
    else:
        directory_path = pathlib.Path("Results/")
    if args.preprocess:
        preprocessors_summary(directory_path)
    else:
        fingerprint_group_tests_helper(directory_path)
