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

def run_wrapper_model(model, function_prototypes=None, filter_functions=None, partial=True, regex_impl=False):
    """
    Run a model and print the results.
    """
    oracle = oracles.KleeOracle(model, function_prototypes)
    if partial:
        if type(model).__name__ == 'RegexModule':
            oracle.build_eywa_regex_model()
        else:
            oracle.build_compositional_model()
    else:
        oracle.build_filter_and_test_model(filter_functions, temperature=0.6)
        
    return oracle


# with open("prefixLengthToSubnetMask.txt", 'r') as f:
#     prefixLengthtoSubnetMask = f.read()
    
# with open("isValidPrefixList.txt", 'r') as f:
#     isValidPrefixList = f.read()
    
# with open("isValidRoute.txt", 'r') as f:
#     isValidRoute = f.read()
    
# with open("isValidRouteMap.txt", 'r') as f:
#     isValidRouteMap = f.read()
    
# pfxl_code = replace_wrapper_code(isValidPrefixList, prefixLengthtoSubnetMask, "uint32_t prefixLenToSubnetMask(uint32_t maskLength) {")
# route_code = replace_wrapper_code(isValidRoute, prefixLengthtoSubnetMask, "uint32_t prefixLenToSubnetMask(uint32_t maskLength) {")
# rmap_code = replace_wrapper_code(isValidRouteMap, route_code, "bool isValidRoute(Route route) {")
# print(rmap_code)

# rmap_code = replace_wrapper_code(rmap_code, pfxl_code, "bool isValidPrefixList(PrefixListEntry prefixList[2]) {")
# print("\n")
# print(rmap_code)

# code = """#include <stdint.h>
# #include <stdbool.h>
# #include <string.h>
# #include <stdlib.h>
# #include <klee/klee.h>
# #include <stdio.h>

# typedef struct { uint32_t prefix; uint8_t prefixLength; uint32_t nextHop; uint32_t localPref; uint32_t community[1]; uint32_t med; } Route;

# typedef struct { uint32_t prefix; uint8_t prefixLength; uint32_t le; uint32_t ge; bool any; bool permit; } PrefixListEntry;

# typedef struct { PrefixListEntry matchPrefixList[2]; uint32_t matchLocalPref; uint32_t matchMed; uint32_t setLocalPref; uint32_t setMed; uint32_t setNextHop; uint32_t setCommunity; } RouteMapStanza;

# typedef struct { RouteMapStanza stanza[1]; } RouteMap;





# uint32_t prefixLenToSubnetMask(uint32_t maskLength) {
#     if (maskLength > 32) {
#         return 0;
#     }
#     return ~((1 << (32 - maskLength)) - 1);
# }

# bool isValidPrefixList(PrefixListEntry prefixList[2]) {
#     if (memcmp(&prefixList[0], &prefixList[1], sizeof(PrefixListEntry)) == 0) {
#         return false;
#     }

#     for (int i = 0; i < 2; i++) {
#         if (prefixList[i].any) {
#             if (prefixList[i].prefix != 0 || prefixList[i].prefixLength != 0 || prefixList[i].ge != 0 || prefixList[i].le != 32) {
#                 return false;
#             }
#         } else {
#             if (prefixList[i].prefix < 1671377732 || prefixList[i].prefix > 1679687938) {
#                 return false;
#             }

#             if (prefixList[i].prefixLength > 32 || prefixList[i].le > 32 || prefixList[i].ge > 32) {
#                 return false;
#             }

#             if (prefixList[i].prefixLength > prefixList[i].ge || prefixList[i].ge > prefixList[i].le) {
#                 return false;
#             }

#             uint32_t subnetMask = prefixLenToSubnetMask(prefixList[i].prefixLength);
#             if ((prefixList[i].prefix & subnetMask) == 0) {
#                 return false;
#             }
#         }
#     }

#     return true;
# }

# bool isValidRoute(Route route);

# bool isValidRouteRmap(Route route, RouteMap routeMap) {
#     if (!isValidRoute(route)) {
#         return false;
#     }

#     for (int i = 0; i < 2; i++) {
#         if (!isValidPrefixList(routeMap.stanza[0].matchPrefixList)) {
#             return false;
#         }
#     }

#     if (routeMap.stanza[0].matchLocalPref < 100 || routeMap.stanza[0].matchLocalPref > 200) {
#         return false;
#     }

#     if (routeMap.stanza[0].matchMed < 20 || routeMap.stanza[0].matchMed > 50) {
#         return false;
#     }

#     if (routeMap.stanza[0].setLocalPref < 300 || routeMap.stanza[0].setLocalPref > 400) {
#         return false;
#     }

#     if (routeMap.stanza[0].setMed < 70 || routeMap.stanza[0].setMed > 90) {
#         return false;
#     }

#     if (routeMap.stanza[0].setNextHop < 1671377732 || routeMap.stanza[0].setNextHop > 1679687938) {
#         return false;
#     }

#     if (routeMap.stanza[0].setCommunity < 10 || routeMap.stanza[0].setCommunity > 20) {
#         return false;
#     }

#     return true;
# }"""

# code2 = """#include <stdint.h>
# #include <stdbool.h>
# #include <string.h>
# #include <stdlib.h>
# #include <klee/klee.h>
# #include <stdio.h>

# typedef struct { uint32_t prefix; uint8_t prefixLength; uint32_t nextHop; uint32_t localPref; uint32_t community[1]; uint32_t med; } Route;



# uint32_t prefixLenToSubnetMask(uint32_t maskLength) {
#     if (maskLength > 32) {
#         return 0;
#     }
#     return ~((1 << (32 - maskLength)) - 1);
# }

# bool isValidRoute(Route route) {
#     uint32_t subnetMask = prefixLenToSubnetMask(route.prefixLength);
#     uint32_t ipaddr = route.prefix;
#     uint32_t localPref = route.localPref;
#     uint32_t med = route.med;
#     uint32_t nextHop = route.nextHop;
#     uint32_t community = route.community[0];

#     if (ipaddr < 1671377732 || ipaddr > 1679687938) {
#         return false;
#     }

#     if (route.prefixLength > 32) {
#         return false;
#     }

#     if ((ipaddr & subnetMask) == 0) {
#         return false;
#     }

#     if (localPref < 100 || localPref > 200) {
#         return false;
#     }

#     if (med < 20 || med > 50) {
#         return false;
#     }

#     if (nextHop < 1671377732 || nextHop > 1679687938) {
#         return false;
#     }

#     if (community != 0) {
#         return false;
#     }

#     return true;
# }"""

# final_code = replace_wrapper_code(code, code2, "bool isValidRoute(Route route) {")

# print(final_code)