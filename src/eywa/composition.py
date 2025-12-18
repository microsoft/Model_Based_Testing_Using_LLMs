import eywa.oracles as oracles
import json
import re

def find_all_function_definitions(c_code):
    # Split the C code into lines for easy line number tracking
    pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)\s*\{')
    
    functions = re.findall(pattern, c_code)
    lines = c_code.split("\n")
    k = 0
    flag = False
    d = dict()
    
    if len(functions) == 0: return d
    
    for i, line in enumerate(lines):
        f_dec = functions[k][0] + ' ' + functions[k][1] + '(' + functions[k][2] + ') {'
        # print(f_dec)
        if line.startswith(f_dec):
            flag = True           
            d[f_dec] = (i,)
        if line.rstrip().startswith('}') and flag:
            d[f_dec] += (i,)
            flag = False
            k += 1
        if k == len(functions):
            break
    
    return d

def remove_function_definition(c_code, rngs):
    new_c_code = ""
    prev = 0
    c_code = c_code.split("\n")
    for rng in rngs:
        # print(c_code[rng[0]])
        new_c_code = new_c_code + '\n'.join(c_code[prev:rng[0]])
        prev = rng[1] + 1
    
    new_c_code = new_c_code + '\n'.join(c_code[prev:])
    return new_c_code

def insert_function_definition(wrapper_code, function_code):
    wrapper_code_functions = find_all_function_definitions(wrapper_code)
    function_code_functions = find_all_function_definitions(function_code)
    
    removals = []
    for func in function_code_functions:
        if func in wrapper_code_functions:
            removals.append(wrapper_code_functions[func])
    removals.sort()
    wrapper_code = remove_function_definition(wrapper_code, removals)
    
    ## Skip the includes and the structs (typedef struct) in function code
    last_typedef_struct_line = None
    lines = function_code.split("\n")
    function_code_typedef_struct_lines = []           
            
    for line in lines:
        if line.startswith("typedef"):
            function_code_typedef_struct_lines.append(line)
            last_typedef_struct_line = line
            
    if last_typedef_struct_line:
        index = function_code.rfind(last_typedef_struct_line) + len(last_typedef_struct_line)
        function_code = function_code[index:]
    else:
        last_include_line = None
        for line in lines:
            if line.startswith("#include"):
                last_include_line = line
    
        if last_include_line:
            index = function_code.rfind(last_include_line) + len(last_include_line)
            function_code = function_code[index:]

    ## Skip the includes and the structs (typedef struct) in wrapper code
    last_typedef_struct_line = None
    lines = wrapper_code.split("\n")
    wrapper_code_typedef_struct_lines = []
    for line in lines:
        if line.startswith("typedef"):
            wrapper_code_typedef_struct_lines.append(line)
            last_typedef_struct_line = line
    if last_typedef_struct_line:
        index = wrapper_code.rfind(last_typedef_struct_line) + len(last_typedef_struct_line)
    else:
        last_include_line = None
        for line in lines:
            if line.startswith("#include"):
                last_include_line = line
    
        if last_include_line:
            index = wrapper_code.rfind(last_include_line) + len(last_include_line)
            
    new_typedef_struct_lines_to_insert = []
    for line in function_code_typedef_struct_lines:
        if line not in wrapper_code_typedef_struct_lines:
            new_typedef_struct_lines_to_insert.append(line)
    
    new_wrapper_code = wrapper_code[:index] + '\n'.join(new_typedef_struct_lines_to_insert) + '\n\n' + function_code + wrapper_code[index:]

    return new_wrapper_code    
            
def replace_wrapper_code(wrapper_code, function_code, function_declare):
    function_declare = function_declare[:-3]
    wrapper_code_lines = wrapper_code.split('\n')
    start_idx = 0
    flag = 0
    for i in range(len(wrapper_code_lines)):
        if wrapper_code_lines[i].startswith(function_declare):
            start_idx = i
            if wrapper_code_lines[i].endswith(";"):
                flag = 1
                end_idx = i + 1
            break
    
    if not flag:
        for i in range(start_idx, len(wrapper_code_lines)):
            if wrapper_code_lines[i].startswith('}'):
                end_idx = i + 1
                break
    
    # print("Start idx:", start_idx)
    # print("End idx:", end_idx)
    wrapper_code_function_definitions_beg = find_all_function_definitions('\n'.join(wrapper_code_lines[:start_idx]))
    function_code_function_definitions = find_all_function_definitions(function_code)
    
    # print(wrapper_code_function_definitions_beg)
    # print(function_code_function_definitions)
    removals = []
    for func in function_code_function_definitions:
        if func in wrapper_code_function_definitions_beg:
            removals.append(function_code_function_definitions[func])
    removals.sort()
    function_code = remove_function_definition(function_code, removals)
    wrapper_code_lines = wrapper_code.split('\n')
    start_idx = 0
    flag = 0
    for i in range(len(wrapper_code_lines)):
        if wrapper_code_lines[i].startswith(function_declare):
            start_idx = i
            if wrapper_code_lines[i].endswith(";"):
                flag = 1
                end_idx = i + 1
            break
    
    if not flag:
        for i in range(start_idx, len(wrapper_code_lines)):
            if wrapper_code_lines[i].startswith('}'):
                end_idx = i + 1
                break
    
    wrapper_code_function_definitions_end = find_all_function_definitions('\n'.join(wrapper_code_lines[end_idx:]))
    function_code_function_definitions = find_all_function_definitions(function_code)
    removals = []
    for func in wrapper_code_function_definitions_end:
        if func in function_code_function_definitions:
            removals.append(wrapper_code_function_definitions_end[func])
            
    removals.sort()
    # print("Wrapper code removals:", removals)
    wrapper_code = remove_function_definition(wrapper_code, removals)
    
    # print("Wrapper code after removals:", wrapper_code)
    
    wrapper_code_lines = wrapper_code.split('\n')
    
    # find the start of function body in function code
    last_typedef_struct_line = None
    lines = function_code.split("\n")
    for line in lines:
        if line.startswith("typedef"):
            last_typedef_struct_line = line
    if last_typedef_struct_line:
        index = function_code.rfind(last_typedef_struct_line) + len(last_typedef_struct_line)
        function_code = function_code[index:]
    else:
        last_include_line = None
        for line in lines:
            if line.startswith("#include"):
                last_include_line = line
    
        if last_include_line:
            index = function_code.rfind(last_include_line) + len(last_include_line)
            function_code = function_code[index:]
    
    # Replace the function signature with the function code
    new_wrapper_code = '\n'.join(wrapper_code_lines[:start_idx]) + '\n' + function_code + '\n' + '\n'.join(wrapper_code_lines[end_idx:])
    
    return new_wrapper_code

def insert_regex_impl(wrapper_code, regex_impl):
    """
    Inserts the regex implementation code after the last typedef struct or #include,
    but before any function definitions.
    """
    lines = wrapper_code.split("\n")
    
    # Find the insertion point - after the last typedef or include
    last_typedef_or_include_idx = -1
    for i, line in enumerate(lines):
        if line.startswith("typedef") or line.startswith("#include"):
            last_typedef_or_include_idx = i
    
    # If we found a typedef or include, insert after it
    if last_typedef_or_include_idx >= 0:
        insertion_point = last_typedef_or_include_idx + 1
        new_code = '\n'.join(lines[:insertion_point]) + '\n' + regex_impl + '\n' + '\n'.join(lines[insertion_point:])
    else:
        # Otherwise, just prepend it
        new_code = regex_impl + '\n' + wrapper_code
    
    return new_code

def run_wrapper_model(model, function_prototypes=None, filter_functions=None, partial=True, temperature=0.6):
    """
    Run a model and print the results.
    """
    oracle = oracles.KleeOracle(model, function_prototypes, temperature=temperature)
    if partial:
        if type(model).__name__ == 'RegexModule':
            oracle.build_eywa_regex_model()
        else:
            oracle.build_compositional_model()
    else:
        oracle.build_filter_and_test_model(filter_functions)
        
    return oracle