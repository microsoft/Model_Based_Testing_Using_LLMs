This version contains support for two kinds of modularity:
    1. filter and test
    2. composition

Place the OpenAI key in a file named key.txt

The files containing code for the new experiments are **test.py** and **test-confed.py**.

If you run test-confed.py, it will produce errors, which I believe are in the main function.

I have made changes to **KleeOracle** class.
These are the methods I added mainly (they call other methods which I have defined or used from previous code accordigly):
    * build_partial_model (only writes the function code)
    * build_filter_and_test_model (writes the function code as well as the main function, which adds additional calls to the provided validity functions - it is currently not very flexible and might need more work)

Also made changes to build_model in KleeOracle, which can take in function declarations (meant for developing function compositions).



May 28 push:
Made changes to oracles.py
New class VoidReturnBuilder that initializes the final parameter in the set of inputs for void functions
Changes made in build_klee_main and build_klee_filter_main
Currently only final parameter is considered, updates happen within function
Capture updates with symbolic variables defined after the function call is made
**test.py** contains function test_function_return that checks a simple case of void return type
