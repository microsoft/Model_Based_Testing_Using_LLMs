import json
import os
import time
import traceback
from collections import defaultdict
from typing import Union
from eywa.composer import DependencyGraph
import eywa.ast as ast
import eywa.oracles as oracles

def generate_temperature_values(k):
    if k == 1:
        return [0]
    else:
        step = 1 / (k - 1)
        return [round(i * step, 3) for i in range(k)]


def make_hashable(obj):
    if isinstance(obj, (tuple, list)):
        return tuple((make_hashable(elem) for elem in obj))
    elif isinstance(obj, dict):
        return tuple(sorted((key, make_hashable(val)) for key, val in obj.items()))
    else:
        return obj


def recreate_structure(hashable):
    if isinstance(hashable, tuple) and all(isinstance(item, tuple) and len(item) == 2 for item in hashable):
        return {key: recreate_structure(val) for key, val in hashable}
    elif isinstance(hashable, tuple):
        return tuple(recreate_structure(item) for item in hashable)
    else:
        return hashable


def run(graph: DependencyGraph, k: int = 1, ratelimit_sec=10, debug: Union[None, str] = None, timeout_sec: int = 300, temperature_value=0.6):
    """
    Run a model to produce test results.
    """
    if debug is not None:
        if not os.path.exists(debug):
            os.makedirs(debug)
    unique_testcases = set()
    temperature_values = [temperature_value for _ in range(k)]
    stats = defaultdict(lambda: defaultdict(float))
    for i in range(k):
        if i > 0:
            time.sleep(ratelimit_sec)
        start_time = time.time()
        # oracle = oracles.KleeOracle(model)
        try:
            # oracle.build_model(temperature=temperature_values[i])
            model = graph.Synthesize(temperature=temperature_values[i])
        except Exception as e:
            print(
                f"Error building model with temperature {temperature_values[i]}: {e}")
            time.sleep(120)
            start_time = time.time()
            # oracle.build_model(temperature=temperature_values[i])
            model = graph.Synthesize(temperature=temperature_values[i])
        stats[i]["GPT_Time"] = time.time() - start_time
        system_prompt = model.system_prompt()
        user_prompt = model.user_prompt()
        implementation = model.implementation
        if debug is not None:
            if i == 0:
                with open(os.path.join(debug, f"system_prompt.txt"), "w") as f:
                    f.write(system_prompt)
                with open(os.path.join(debug, f"user_prompt.txt"), "w") as f:
                    f.write(user_prompt)
            with open(os.path.join(debug, f"implementation_{i}_{temperature_value}.c"), "w") as f:
                f.write(implementation)
        try:
            start_time = time.time()
            tests = model.get_inputs(timeout_sec)
            stats[i]["Klee_Time"] = time.time() - start_time
            strings = []
            unique_testcases_i = set()
            for test in tests:
                unique_testcases_i.add(make_hashable(test))
                strings.append(str(test))
            stats[i]["Num_Tests"] = len(strings)
            stats[i]["Num_Unique_Tests"] = len(unique_testcases_i)
            stats[i]["Implementation_Lines"] = len(implementation.split("\n"))
            unique_testcases_before = len(unique_testcases)
            for testcase in unique_testcases_i:
                unique_testcases.add(testcase)
            stats[i]["Unique_Tests_Added"] = len(
                unique_testcases) - unique_testcases_before
            stats[i]["Total_Unique_Tests"] = len(unique_testcases)
            if debug is not None:
                with open(os.path.join(debug, f"tests_{i}_{temperature_value}.txt"), "w") as f:
                    f.write("\n".join(strings))
                print(
                    f"Generated {len(strings)} test cases in run {i} with temp {temperature_value}.", flush=True)
        except Exception as e:
            if debug is not None:
                with open(os.path.join(debug, f"errors_{i}_{temperature_value}.txt"), "w") as f:
                    f.write(str(e) + "\n")
                    traceback.print_exc(file=f)
    unique_tuples_list = [recreate_structure(t) for t in unique_testcases]
    print(
        f"Generated {len(unique_tuples_list)} test cases across {k} runs with temp {temperature_value}.", flush=True)
    with open(os.path.join(debug, f"stats_{temperature_value}.json"), "w") as f:
        json.dump(stats, f, indent=2)
    return unique_tuples_list
