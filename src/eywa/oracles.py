import io
import os
import tarfile
import tempfile
import uuid
from ast import NodeVisitor
from collections import OrderedDict
from typing import List
import textwrap

import docker
from docker.types import Ulimit

from eywa.ast import *
from eywa.llm import GPT4
from termcolor import colored

class KleeOracle:
    """
    An oracle that uses the KLEE symbolic execution engine to generate
    inputs for a user's function.
    """

    def __init__(self, function: Function, function_prototypes: List[Function]=None, constants: Dict[str, Const]=None):
        """
        Initializes the oracle with the given function.
        """
        self.function = function
        self.name = function.name
        self.description = function.description
        self.inputs = function.inputs
        self.result = function.result
        self.precondition = function.precondition
        self.function_prototypes = function_prototypes
        self.dependency_oracles = []
        self.timeout_sec = 60
        self.implementation = None
        self.has_valid_input_param = False
        self.function_declares = []
        self.constants = constants

    def build_model(self, temperature: float = 0.0) -> None:
        """
        Builds the model by filling in the implementation field with a
        complete C program that implements the user's function.
        """
        gpt4 = GPT4()
        user_prompt = self.user_prompt()
        print(colored("System prompt:", 'blue'), self.system_prompt())
        gpt4_response = gpt4.query_openai_endpoint(
            user_prompt, temperature=temperature, system_prompt=self.system_prompt())         
        klee_main = self._build_klee_main()
        # gpt4_response = ""
        if self.precondition is not None and Expr.has_match(self.precondition):
            implementation = gpt4_response + '\n\n' + self._regex_impl() + "\n" + klee_main
        else:
            implementation = gpt4_response + "\n\n" + klee_main
        
        print(colored("User prompt:", 'red', attrs=['bold']), user_prompt, "\n\n")
        self.implementation = implementation
        print(colored("GPT:", 'green', attrs=['bold']), self.implementation)
        
    def build_eywa_regex_model(self):
        lines = []
        self._build_function_definition(lines)
        body = self.function.build_regex_expr()
        for line in body:
            lines.append("    " + line)
        lines.append("}")
        self.implementation = '\n'.join(lines)
        
    def build_compositional_model(self, temperature: float = 0.0) -> None:
        """
        Builds the model by filling in the implementation field with a
        complete C program that implements the user's function.
        """
        gpt4 = GPT4()
        print(colored("System prompt:", 'blue'), self.system_prompt())
        user_prompt = self.user_prompt()
        gpt4_response = gpt4.query_openai_endpoint(
            user_prompt, temperature=temperature, system_prompt=self.system_prompt())
        # gpt4_response = ""
        print(colored("User prompt:", 'red', attrs=['bold']), user_prompt, "\n\n")
        self.implementation = gpt4_response
        print(colored("GPT:", 'green', attrs=['bold']), self.implementation)

    
    def build_filter_and_test_model(self, other: List[str] = None, temperature: float = 0.0):
        """
        Builds the model by filling in the implementation field with a
        C program that implements the user's function. It also provides
        utilizes filter functions to remove unwanted test cases
        """
        
        gpt4 = GPT4()
        user_prompt = self.user_prompt()
        print(colored("System prompt:", 'blue'), self.system_prompt())
        gpt4_response = gpt4.query_openai_endpoint(
            user_prompt, temperature=temperature, system_prompt=self.system_prompt()
        )
        # gpt4_response = ""
        if other is not None:
            klee_main = self._build_klee_filter_main(other)
        else:
            klee_main = self._build_klee_main()
        self.implementation = gpt4_response + '\n\n' + klee_main
        print("User prompt:", user_prompt, "\n\n")
        print("GPT:", self.implementation)
        if other is not None: self.has_valid_input_param = True
        
        
    def get_inputs(self, timeout_sec: Union[int, None] = None):
        """
        Gets the inputs for the user's function by using the generated
        model and the KLEE symbolic execution engine.
        """
        if self.implementation is None:
            raise Exception('Model not built yet')
        self.timeout_sec = timeout_sec
        klee_output = self._run_klee(self.implementation)
        results = []
        for klee_input in self._read_klee_inputs(klee_output):
            if self._is_valid_input(klee_input):
                if self.has_valid_input_param:
                    if not klee_input[-1]: # checking the validity condition
                        results.append(klee_input[:-1])
                else: 
                    results.append(klee_input)
            
        return results

    def _is_valid_input(self, klee_input) -> bool:
        """
        Determines if a KLEE input is valid or not based on the constraints
        given for the parameters. This is necessary because KLEE will generate
        some invalid inputs for cases that do not satisfy the constraints.
        """
        if self.precondition is None:
            return True
        assignment = dict(
            zip(map(lambda x: x.name, self.inputs + [self.result]), klee_input))
        return Expr.eval(self.precondition, assignment)

    def _read_klee_inputs(self, klee_output: str):
        """
        Reads the KLEE output and uses them to reconstruct
        the values of the inputs. Yields the inputs as Python values.
        """
        dict = {}
        name = None
        value = None
        for line in klee_output.splitlines():
            if "name:" in line:
                name = line.split("'")[1]
            if "uint:" in line:
                value = int(line.split("uint: ")[1])
                if name in dict:
                    yield self._create_input(dict)
                    dict = {}
                dict[name] = value
        yield self._create_input(dict)

    def _create_input(self, dict):
        """
        Converts an assignment of KLEE variables in a dict
        to a Python value.
        """
        # print(dict)
        reader = ResultReader(dict)
        inputs = []
        
        inp = list(self.inputs)
        if not isinstance(self.result.type, Void): 
            inp.append(self.result) 
        for parameter in inp:
            try:
                inputs.append(reader.visit(parameter.type))
            except:
                inputs.append(None)
            
        if self.has_valid_input_param:
            n = reader._next()
            inputs.append(bool(reader.assignment[n]))
        
        return tuple(inputs)

    def _get_all_types(self) -> List[Type]:
        """
        Gets all the types associated with the function
        from the input parameters.
        """
        result = []
        TypeCollector.collect(self.result.type, result)
        for input in self.inputs:
            TypeCollector.collect(input.type, result)
            
        return result

    def _build_docstring(self, result: List[str]):
        """
        Build a docstring to use in the GPT query that explains the
        code to be implemented by the language model.
        """
        if self.description is not None:
            for line in self.description.splitlines():
                result.append(f'// {line}')
            result.append('//')
        if len(self.inputs) > 0:
            result.append(f'// Parameters:')
            for input in self.inputs:
                if input is not None:
                    result.append(f'//     {input.name}: {input.description}')
            result.append('//')
        if not isinstance(self.result, Void):
            result.append(f'// Return Value:')
            if self.result.description is not None:
                result.append(f'//     {self.result.description}')
        result.append('//')
        return result

    def _build_function_definition(self, result: List[str]):
        """
        Builds the function definition to use in the GPT query.
        Fills in the result list with the lines of the function definition.
        """
        (l, r) = TypeBuilder.build(self.result.type)
        return_type = l + r
        parameters = []
        for i in range(len(self.inputs)):
            (left, right) = TypeBuilder.build(self.inputs[i].type)
            if isinstance(self.result.type, Void) and i == len(self.inputs) - 1 and not isinstance(self.inputs[i].type, Array):
                parameters.append(f"{left} *{self.inputs[i].name}")
            else:
                parameters.append(f"{left} {self.inputs[i].name}{right}")
        function_definition = f'{return_type} {self.name}(' + ", ".join(
            parameters) + ') {'
        result.append(function_definition)

    def _build_type_definitions(self, result: List[str]):
        """
        Builds the type definitions to use in the GPT query.
        Fills in the result list with the lines of the type definitions.
        """
        types = self._get_all_types()
        types = list(OrderedDict.fromkeys(types))
        
        type_definitions = []
        
        for type in types:
            definition = DefinitionBuilder.build(type)
            if definition is not None:
                result.append(definition)
                type_definitions.append(definition)
                
        return type_definitions
            
    @staticmethod            
    def _build_function_prototype_docstrings(fp, result:List[str]):
        if fp.description is not None:
            for line in fp.description.splitlines():
                result.append(f'// {line}')
            result.append('//')
        if len(fp.inputs) > 0:
            result.append(f'// Parameters:')
            for input in fp.inputs:
                if input is not None:
                    result.append(f'//     {input.name}: {input.description}')
            result.append('//')
        if not isinstance(fp.result, Void):
            result.append(f'// Return Value:')
            if fp.result.description is not None:
                result.append(f'//     {fp.result.description}')
        result.append('//')
        return result
    
    def _define_constants(self, result: List[str]):
        if self.constants is None:
            return
        
        for v in self.constants.keys():
            c = self.constants[v]
            (l, r) = TypeBuilder.build(c.type)
            if isinstance(c.type, Array):
                elements = c.constant
                s = f'{l} {v}{r} = ' +'{'
                first = True
                for e in elements:
                    if first:
                        first = False
                    else:
                        s = s + ", "
                    if isinstance(e, str):
                        s = s + f'"{e}"'
                    if isinstance(e, int):
                        s = s + f'{e}'
                    if isinstance(e, bool):
                        s = s + ('true' if e else 'false')
                
                s = s + '};'
                result.append(s)    
                        
            elif isinstance(c.type, Int):
                result.append(f'{l} {v}{r} = {c.constant};')
            elif isinstance(c.type, String):
                result.append(f'{l} {v}{r} = "{c.constant}";')
            elif isinstance(c.type, Bool):
                result.append(f'{l} {v}{r} = ' + ('true' if c.constant else 'false'))
                
    @staticmethod
    def _build_function_prototype_type_definitions(fp):
        types = []
        TypeCollector.collect(fp.result.type, types)
        for input in fp.inputs:
            TypeCollector.collect(input.type, types)
        
        types = list(OrderedDict.fromkeys(types))
         
        new_type_definitions = []
        for type in types:
            definition = DefinitionBuilder.build(type)
            if definition is not None:
                new_type_definitions.append(definition)
                
        return new_type_definitions
    
    def _build_function_prototypes(self, result: List[str], type_definitions: List[str]):
        if self.function_prototypes is None:
            return
        
        # build and insert the relevant type definitions for the function prototypes
        new_function_definitions = set()
        
        for fp in self.function_prototypes:
            fp_type_definitions = self._build_function_prototype_type_definitions(fp)
            new_function_definitions.update(fp_type_definitions)
            
        for definition in new_function_definitions:
            if definition not in type_definitions:
                result.append(definition)
            
        for fp in self.function_prototypes:
            (l, r) = TypeBuilder.build(fp.result.type)
            return_type = l + r
            parameters = []
            # print("Inputs:", fp.inputs)
            for i, input in enumerate(fp.inputs):
                (left, right) = TypeBuilder.build(input.type)
                if isinstance(fp.result.type, Void) and i == len(fp.inputs) - 1 and not isinstance(input.type, Array):
                    parameters.append(f"{left} *{input.name}")
                else:
                    parameters.append(f"{left} {input.name}{right}")
            
            function_definition = f'{return_type} {fp.name}(' + ", ".join(
                parameters) + ');\n\n'
            
            self.function_declares.append(function_definition)
            
            self._build_function_prototype_docstrings(fp, result)
            result.append(function_definition)
                
    def system_prompt(self):
        """
        Returns the constructed system prompt to use in the GPT query.
        """
        result = [
            "Your goal is to implement the C function provided by the user.",
            "The result should be the complete implementation of the code, including:",
            "  1. All the import statements needed, including those provided in the input. All the imports from the input should be included.",
            "  2. All the type definitions provided by the user. The type definitions should NOT be modified",
            "  3. ONLY write code for the function that has 'implement me' written in its function body.",
            "  4. If any additional function prototypes are provided, you can use them as helper functions. There is no need to define them. You can assume they will be done later by the user."
            "  5. Do NOT change the provided function declarations/prototypes."
            "  6. Whenever you define a struct, write it in one line. Do not put newline. e.g. struct { int x; int y; }",
            "",
            "Do NOT add a `main()` function or any examples, just implement the function.",
            "DO NOT USE fenced code blocks, just write the code.",
            "DO NOT USE C strtok function. Implement your own.",
            "",
            "Example Input:",
            "#include <stdint.h>",
            "#include <stdbool.h>",
            "#include <string.h>",
            "#include <stdlib.h>",
            "#include <klee/klee.h>",
            "#include <stdio.h>",
            "",
            "typedef uint32_t myint;",
            "",
            "myint add_one(myint x) {",
            "  // implement me",
            "}",
            "",
            "Example Output:",
            "#include <stdint.h>",
            "#include <stdbool.h>",
            "#include <string.h>",
            "#include <stdlib.h>",
            "#include <klee/klee.h>",
            "#include <stdio.h>",
            "",
            "typedef uint32_t myint;",
            "",
            "myint add_one(myint x) {",
            "    return x + 1",
            "}",
        ]
        return '\n'.join(result)

    def user_prompt(self):
        """
        Returns the constructed user prompt to use in the GPT query.
        """
        result = [
            "#include <stdint.h>",
            "#include <stdbool.h>",
            "#include <string.h>",
            "#include <stdlib.h>",
            "#include <klee/klee.h>",
            "#include <stdio.h>",
            ""
        ]
        
        type_definitions = self._build_type_definitions(result)
        self._define_constants(result)
        self._build_function_prototypes(result, type_definitions)
        self._build_docstring(result)
        self._build_function_definition(result)
        result.append('    // implement me')
        result.append('}')
        return '\n'.join(result)

    def _regex_impl(self):
        return """
// A regular expression operation.
typedef enum { OR, SEQ, STAR, RANGE } RegexOp;

// A regular expression AST node.
typedef struct Regex Regex;
struct Regex {
    RegexOp op;
    int clo;
    int chi;
    Regex* left;
    Regex* right;
};

// A regular expression continuation as a linked list
// of regular expressions in a list to be matched.
typedef struct RegexCont RegexCont;
struct RegexCont {
    Regex* regex;
    RegexCont* next;
};

// Match a regular expression against a string with a continuation.
static int match_cont(Regex* regex, RegexCont* cont, char *text) {
  // If the regex is null (empty) then return true only if the string is over.
  if (regex == NULL) {
    return *text == '\\0';
  }
  // Regex OR, check both sides.
  if (regex->op == OR) {
    return match_cont(regex->left, cont, text) || match_cont(regex->right, cont, text);
  }
  // Regex SEQ, check the first and pass the second as a continuation.
  if (regex->op == SEQ) {
    RegexCont c;
    c.next = cont;
    c.regex = regex->right;
    return match_cont(regex->left, &c, text);
  }
  // Regex STAR, case for iteration.
  if (regex->op == STAR) {
    Regex r;
    r.op = SEQ;
    r.left = regex->left;
    r.right = regex;
    return match_cont(cont->regex, cont->next, text) || (*text != '\\0' && match_cont(&r, cont, text));
  }
  // Regex RANGE, base case check match and continue to continuation.
  if (regex->op == RANGE) {
    char c = *text++;
    return c != '\\0' && c >= regex->clo && c <= regex->chi && match_cont(cont->regex, cont->next, text);
  }

  return 0;
}

// Match a regular expression against a string.
static int match(Regex* regex, char *text) {
    RegexCont cont;
    cont.next = NULL;
    cont.regex = NULL;
    return match_cont(regex, &cont, text);
}
"""

    def _build_klee_main(self):
        """
        Builds the KLEE main function.
        """
        result = ["int main() {"]
        lines = []
        builder = MainBuilder(lines)
        regex_builder = RegexBuilder(lines)
        void_builder = VoidReturnBuilder(lines)
        assignment = {}
        variables = []
        # create the symbolic inputs.
        # print("Inside build klee main")
        final_parameter = None
        if isinstance(self.result.type, Void):
            final_parameter = self.inputs[-1]
            inputs = self.inputs[:-1]
        else:
            inputs = self.inputs
        
        for parameter in inputs:
            if not isinstance(parameter.type, Void):
                var = builder.visit(parameter.type)
                assignment[parameter.name] = var
                variables.append(var)
                
        # create the symbolic output.
        if not isinstance(self.result.type, Void):
            var = builder.visit(self.result.type)
            assignment[self.result.name] = var
        else:
            void_builder.number = builder.number
            builder.number += 1
            var = void_builder.visit(final_parameter.type)
            assignment[final_parameter.name] = var
            variables.append('&' + var)
        
        # add a call to klee_assume for the condition.
        if self.precondition is not None:
            c_expr = ExprConverter.convert(
                self.precondition, regex_builder, assignment)
            lines.append(f'klee_assume({c_expr});')
        
        # create the call to the function/model.
        args = ", ".join(variables)
        
        result_lines = []
        if isinstance(self.result.type, Void):
            result_lines.append(f"{self.name}({args});")
        else:
            (l, r) = TypeBuilder.build(self.result.type)
            lines.append(f"{l} result_tmp{r} = {self.name}({args});")
            var = assignment[self.result.name]
            # add a call to klee_assume for the result.
            if self.result.name in assignment:
                condition = EqualityGenerator.generate(self.result.type, "result_tmp", var)
                lines.append(f'klee_assume({condition});')
                
        if isinstance(self.result.type, Void):
            var = builder.visit(final_parameter.type)
            condition = EqualityGenerator.generate(final_parameter.type, assignment[final_parameter.name], var)
            lines.extend(result_lines)
            lines.append(f'klee_assume({condition});')
        
        # create the function body.
        for line in lines:
            result.append("    " + line)
        result.append("    return 0;")
        result.append("}")
        return "\n".join(result)
    
    
    def _build_klee_filter_main(self, filter_functions: List[Function]):
        """
        Builds the KLEE main function.
        """
        result = ["int main() {"]
        lines = []
        builder = MainBuilder(lines)
        void_builder = VoidReturnBuilder(lines)
        assignment = {}
        variables = []
        # print("Inside build klee filter main")
        final_parameter = None
        if isinstance(self.result.type, Void):
            final_parameter = self.inputs[-1]
            inputs = self.inputs[:-1]
        else:
            inputs = self.inputs
            
        # create the symbolic inputs.
        for parameter in inputs:
            if not isinstance(parameter.type, Void):
                var = builder.visit(parameter.type)
                assignment[parameter.name] = var
                variables.append(var)
        # create the symbolic output.
        if not isinstance(self.result.type, Void):
            var = builder.visit(self.result.type)
            assignment[self.result.name] = var
        else:
            void_builder.number = builder.number
            var = void_builder.visit(final_parameter.type)
            assignment[final_parameter.name] = var
            variables.append('&' + var)
        
        lines.append("bool bad_input;")
        
        args = ", ".join(variables)
        
        if not isinstance(self.result.type, Void):
            (l, r) = TypeBuilder.build(self.result.type)
            lines.append(f"{l} result_tmp{r};")
            
        if isinstance(self.result.type, Void):
            builder.number = void_builder.number
            result_var = builder.visit(final_parameter.type)
            result_condition = EqualityGenerator.generate(final_parameter.type, assignment[final_parameter.name], result_var)
            
        n = builder.number
        lines.append("bool x" + str(n) + ";")            
        lines.append("klee_make_symbolic(&x" + str(n) + ", sizeof(x" + str(n) + "), \"x" + str(n) + "\");")
            
        ff_strings = []
        k = 0    
        for f in filter_functions:
            var_list = []
            for _ in range(len(f.inputs)):
                var_list.append(variables[k])
                k += 1
            
            filter_function_args = ", ".join(var_list)
            
            ff_strings.append(
                f.name + f"({filter_function_args})"
            )
            
        lines.append(f"if({' && '.join(ff_strings)})" + "{")
        
        # create the call to the function/model.
        if isinstance(self.result.type, Void):
            lines.append("    bad_input = false;")
            lines.append(f"    {self.name}({args});")
        else:
            lines.append("    bad_input = false;")
            lines.append(f"    result_tmp = {self.name}({args});")
            var = assignment[self.result.name]
            
        lines.append("}")
        lines.append("else{")
        lines.append("    bad_input = true;")
        if not isinstance(self.result.type, Void): lines.append("    result_tmp = false;")
        lines.append("}")
        
        # add a call to klee_assume for the result.
        if not isinstance(self.result.type, Void):
            var = assignment[self.result.name]
            if self.result.name in assignment:
                condition = EqualityGenerator.generate(self.result.type, "result_tmp", var)
                lines.append(f'klee_assume({condition});')
        else:  
            lines.append(f'klee_assume({result_condition});')
        
        lines.append(f'klee_assume(bad_input == x' + str(n) + ');')
        builder.number += 1
        # create the function body.
        for line in lines:
            result.append("    " + line)
        result.append("    return 0;")
        result.append("}")
        return "\n".join(result)
    
    def count_lines(self):
        lines = self.implementation.split('\n')
        count = 0
        for line in lines:
            if line.strip() != "":
                count += 1
        return count 

    def _run_klee(self, program: str) -> str:
        """
        Runs KLEE given the program source code and returns the raw output
        from the KLEE tool as a string that contains the symbolic variable assignments.
        """
        client = docker.from_env()
        repository = "klee/klee"
        tag = "3.0"

        # Check if the image already exists locally
        local_images = [img.tags[0]
                        for img in client.images.list() if img.tags]
        image_name = f"{repository}:{tag}"
        if image_name not in local_images:
            print(f"Pulling docker image {image_name}...")
            client.images.pull(repository, tag=tag)
            # Will raise an exception if the image cannot be pulled
            print(f"Successfully pulled {image_name}")

        # Create a container from the image
        container_name = f"klee_container_{self.name}"
        ulimits = [Ulimit(name='stack', soft=-1, hard=-1)]
        try:
            container = client.containers.get(container_name)
            # print(f"Container {container_name} already exists.")
            # answer = getpass("Do you want to reuse it? (yes/no): ")
            # if answer.lower() == "no":
            #     new_container_name = getpass("Enter new container name: ")
            #     container = client.containers.create(
            #         image_name,
            #         command="/bin/sh -c 'tail -f /dev/null'",  # keep the container running
            #         name=new_container_name,
            #         detach=True,
            #         ulimits=ulimits
            #     )
            #     print(f"Created new container {new_container_name}.")
        except docker.errors.NotFound:
            container = client.containers.create(
                image_name,
                name=container_name,
                command="/bin/sh -c 'tail -f /dev/null'",
                detach=True,
                ulimits=ulimits
            )
            print(f"Created new container {container_name}.")
            container.start()
            # Ensure the target directory exists
            result = container.exec_run("mkdir -p /home/klee/programs")
            if result.exit_code != 0:
                print("Failed to create directory inside container:",
                      result.output.decode())
                exit(1)
            script_content = textwrap.dedent("""\
                import subprocess
                import os
                import glob

                # Path to the directory containing .ktest files
                directory_path = 'klee-last'
                # Glob pattern to match all .ktest files
                file_pattern = os.path.join(directory_path, '*.ktest')
                # Output file
                output_file = 'output.txt'

                # Find all files in the directory matching the pattern
                ktest_files = glob.glob(file_pattern)

                # Open the output file in append mode
                with open(output_file, 'w') as file:
                    # Loop over the list of .ktest files
                    batch = 50000
                    batch_files = []
                    for ktest_file in ktest_files:
                        batch_files.append(ktest_file)
                        batch = batch - 1
                        if batch != 0:
                            continue
                        # Construct the command to execute
                        command = ['ktest-tool'] + batch_files
                        # Execute the command
                        try:
                            result = subprocess.run(command, capture_output=True, text=True, check=True)
                            file.write(f"{result.stdout}")
                        except subprocess.CalledProcessError as e:
                            file.write(f"Command failed for {ktest_file}: {e}")
                        batch = 50000
                        batch_files = []
                    if batch_files:
                        command = ['ktest-tool'] + batch_files
                        try:
                            result = subprocess.run(command, capture_output=True, text=True, check=True)
                            file.write(f"{result.stdout}")
                        except subprocess.CalledProcessError as e:
                            file.write(f"Command failed for {ktest_file}: {e}")                                       
                """)
            container_path = '/home/klee/programs/'
            # Create a temporary tar archive in memory
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                tarinfo = tarfile.TarInfo(name="script.py")
                tarinfo.size = len(script_content)
                tarinfo.mtime = tarinfo.mode = 0o755  # Ensure the file is executable
                tar.addfile(tarinfo, io.BytesIO(
                    script_content.encode('utf-8')))
            # Go back to the beginning of the BytesIO stream
            tar_stream.seek(0)
            container.put_archive(container_path, tar_stream)
        except Exception as e:
            print(f"An error occurred: {e}")
            exit(1)
        container.start()

        # Write program to a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp:
            temp.write(program)
            temp_filename = temp.name

        # Create a temporary tarfile
        with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as tar_temp:
            with tarfile.open(tar_temp.name, 'w') as tar:
                tar.add(temp_filename, arcname="test.c")
            tar_temp_filename = tar_temp.name

        # Copy tarfile to the container
        with open(tar_temp_filename, 'rb') as data:
            container.put_archive('/home/klee/programs', data)

        # Cleanup temporary files
        os.remove(temp_filename)
        os.remove(tar_temp_filename)

        # run the clang command
        _, output = container.exec_run(
            "/bin/bash -c 'cd /home/klee/programs && sudo chmod a+r test.c && clang -emit-llvm -g -c test.c -o test.bc'")
        clang_output = output.decode('utf-8')
        if "error" in clang_output or "Error" in clang_output:
            raise Exception(
                f'Unable to compile generated program with error\n{clang_output}')

        # run the klee command
        timeout = 5 if self.timeout_sec is None else self.timeout_sec
        _, output = container.exec_run(
            f"/bin/bash -c 'cd /home/klee/programs && klee --libc=uclibc --posix-runtime -max-time={timeout}s --external-calls=all test.bc'")
        klee_output = output.decode('utf-8')
        if 'KLEE: done:' not in klee_output:
            raise Exception(f'KLEE execution failed with error\n{klee_output}')

        result = container.exec_run(
            "/bin/bash -c 'cd /home/klee/programs && python3 script.py'")
        if result.exit_code != 0:
            print("Failed to run the test-tool script inside container:",
                  result.output.decode())
            exit(1)
        stream, _ = container.get_archive("/home/klee/programs/output.txt")
        file_like_object = io.BytesIO()
        for chunk in stream:
            file_like_object.write(chunk)
        file_like_object.seek(0)
        with tarfile.open(fileobj=file_like_object, mode='r|') as tar:
            # Assuming there's only one file in the tar archive, extract its content
            for member in tar:
                f = tar.extractfile(member)
                if f is not None:
                    ktest_output = f.read().decode('utf-8')
        # print("KTest Output:", ktest_output)
        return ktest_output


class TypeBuilder(NodeVisitor):
    """
    A class that converts an Eywa type to a C type.
    """

    @staticmethod
    def build(type: Type) -> str:
        """
        Convert an Eywa type to a C type as a string.
        """
        return TypeBuilder().visit(type)

    def visit_Void(self, node):
        return "void", ""

    def visit_Bool(self, node):
        return "bool", ""

    def visit_Char(self, node):
        return "char", ""

    def visit_Int(self, node):
        if node.size == 64:
            return "uint64_t", ""
        if node.size == 32:
            return "uint32_t", ""
        if node.size == 16:
            return "uint16_t", ""
        if node.size == 8:
            return "uint8_t", ""
        return "int", f": {node.size}"

    def visit_String(self, node):
        return "char*", ""

    def visit_Enum(self, node):
        return node.name, ""

    def visit_Array(self, node):
        (left, right) = self.visit(node.element_type)
        return left, f"{right}[{node.maxsize}]"

    def visit_Struct(self, node):
        return node.name, ""

    def visit_Alias(self, node):
        return node.name, ""


class DefinitionBuilder(NodeVisitor):
    """
    A class that creates a C type definition (if needed) for
    a given Eywa type. This includes enums, structs, and aliases.
    """

    @staticmethod
    def build(type: Type) -> str:
        """
        Build a C type definition for an Eywa type if necessary.
        """
        return DefinitionBuilder().visit(type)

    def visit_Void(self, node):
        return None

    def visit_Bool(self, node):
        return None

    def visit_Char(self, node):
        return None

    def visit_Int(self, node):
        return None

    def visit_String(self, node):
        return None

    def visit_Enum(self, node):
        return f'typedef enum {{ {", ".join(node.values)} }} {node.name};\n'

    def visit_Array(self, node):
        return None

    def visit_Struct(self, node):
        field_strs = []
        # print(node.fields.items())
        
        for (field_name, field) in node.fields.items():
            # print("Field:", field_name, field)
            (left, right) = TypeBuilder.build(field)
            field_strs.append(f"{left} {field_name}{right};")
            # print("Bye")
        fields = " ".join(field_strs)
        return f'typedef struct {{ {fields} }} {node.name};\n'

    def visit_Alias(self, node):
        (left, right) = TypeBuilder.build(node.type)
        description = "" if node.description is None else '\n'.join(
            [f'// {line}' for line in node.description.splitlines()]) + '\n'
        return f'{description}typedef {left} {node.name}{right};\n'


class TypeCollector(NodeVisitor):
    """
    A class to recursively extract all of the Ewya sub-types in a type.
    """

    @staticmethod
    def collect(type: Type, results: List[Type]):
        """
        Collect all the Eywa types in a given type.
        """
        TypeCollector(results).visit(type)

    def __init__(self, result):
        self.result = result

    def visit_Void(self, node):
        self.result.append(node)

    def visit_Bool(self, node):
        self.result.append(node)

    def visit_Char(self, node):
        self.result.append(node)

    def visit_Int(self, node):
        self.result.append(node)

    def visit_String(self, node):
        self.result.append(node)

    def visit_Enum(self, node):
        self.result.append(node)

    def visit_Array(self, node):
        self.visit(node.element_type)
        self.result.append(node)

    def visit_Struct(self, node):
        for (_, field) in node.fields.items():
            self.visit(field)
        self.result.append(node)

    def visit_Alias(self, node):
        self.visit(node.type)
        self.result.append(node)


class MainBuilder(NodeVisitor):
    """
    A class to build the KLEE main function that creates the symbolic
    inputs and runs the implementation given by the GPT model.
    """

    def __init__(self, result):
        self.result = result
        self.number = 0

    def _next(self):
        n = self.number
        self.number = self.number + 1
        return f'x{n}'

    def _is_array(self, node):
        while isinstance(node, Alias):
            node = node.type
        return isinstance(node, Array)

    def visit_Void(self, node):
        raise Exception('Cannot create an instance of the Void type')

    def visit_Bool(self, node):
        var = self._next()
        self.result.append(f'bool {var};')
        self.result.append(
            f'klee_make_symbolic(&{var}, sizeof({var}), "{var}");')
        return var

    def visit_Char(self, node):
        var = self._next()
        self.result.append(f'char {var};')
        self.result.append(
            f'klee_make_symbolic(&{var}, sizeof({var}), "{var}");')
        return var

    def visit_Int(self, node):
        var = self._next()
        self.result.append(f'{TypeBuilder.build(node)[0]} {var};')
        self.result.append(
            f'klee_make_symbolic(&{var}, sizeof({var}), "{var}");')
        return var

    def visit_String(self, node):
        var1 = self._next()
        self.result.append(f'char {var1}[{node.maxsize + 1}];')
        for i in range(0, node.maxsize):
            cvar = self.visit(node.char_type)
            # assign the char to the array.
            self.result.append(f'{var1}[{i}] = {cvar};')
        self.result.append(f"{var1}[{node.maxsize}] = '\\0';")
        return var1

    def visit_Enum(self, node):
        var = self._next()
        self.result.append(f'{node.name} {var};')
        self.result.append(
            f'klee_make_symbolic(&{var}, sizeof({var}), "{var}");')
        self.result.append(f'klee_assume({var} >= 0);')
        self.result.append(f'klee_assume({var} < {len(node.values)});')
        return var

    def visit_Array(self, node):
        var = self._next()
        (l, r) = TypeBuilder.build(node.element_type)
        self.result.append(f'{l} {var}{r}[{node.maxsize}];')
        for i in range(0, node.maxsize):
            evar = self.visit(node.element_type)
            self.result.append(f'{var}[{i}] = {evar};')
        return var

    def visit_Struct(self, node):
        var = self._next()
        self.result.append(f'{node.name} {var};')
        for (field_name, field) in node.fields.items():
            field_var = self.visit(field)
            if self._is_array(field):
                self.result.append(
                    f'memcpy({var}.{field_name}, {field_var}, sizeof({field_var}));')
            else:
                self.result.append(f'{var}.{field_name} = {field_var};')
        return var

    def visit_Alias(self, node):
        return self.visit(node.type)
    
class VoidReturnBuilder(NodeVisitor):
    def __init__(self, result):
        self.result = result
        self.number = 0
        self.new_lines = []

    def _next(self):
        n = self.number
        self.number = self.number + 1
        return f'x{n}'

    def _is_array(self, node):
        while isinstance(node, Alias):
            node = node.type
        return isinstance(node, Array)

    def visit_Void(self, node):
        raise Exception('Cannot create an instance of the Void type')

    def visit_Bool(self, node):
        var = self._next()
        self.result.append(f'bool {var};')
        return var

    def visit_Char(self, node):
        var = self._next()
        self.result.append(f'char {var};')
        return var

    def visit_Int(self, node):
        var = self._next()
        self.result.append(f'{TypeBuilder.build(node)[0]} {var};')
        return var

    def visit_String(self, node):
        var1 = self._next()
        self.result.append(f'char {var1}[{node.maxsize + 1}];')
        return var1

    def visit_Array(self, node):
        var = self._next()
        (l, r) = TypeBuilder.build(node.element_type)
        self.result.append(f'{l} {var}{r}[{node.maxsize}];')
        return var

    def visit_Struct(self, node):
        var = self._next()
        self.result.append(f'{node.name} {var};')
        return var

    def visit_Alias(self, node):
        return self.visit(node.type)
    
    def add_symbolic_lines(self):
        self.result.extend(self.new_lines)
    
    
class ResultReader(NodeVisitor):
    """
    Class to read the results of a KLEE run and convert them to Python values.
    """

    def __init__(self, assignment: Dict[str, int]):
        self.number = 0
        self.assignment = assignment
        self.mx = 0
        for key in assignment:
            self.mx = max(int(key[-1]), self.mx)
        
    def _lookup(self):
        n = self._next()
        while n not in self.assignment:
            n = self._next()
            if int(n[-1]) > self.mx:
                break
        if n in self.assignment:
            return self.assignment[n]
        raise Exception("Invalid assignment")

    def _next(self):
        n = self.number
        self.number = self.number + 1
        return f'x{n}'

    def visit_Void(self, node):
        raise Exception('Cannot create an instance of the Void type')

    def visit_Bool(self, node):
        return bool(self._lookup())

    def visit_Char(self, node):
        return chr(self._lookup())

    def visit_Int(self, node):
        return int(self._lookup())

    def visit_String(self, node):
        self._next()  # char[] variable
        str = ""
        done = False
        for _ in range(0, node.maxsize):
            c = self.visit(node.char_type)
            if c == '\0':
                done = True
            if not done:
                str = str + c
        return str

    def visit_Enum(self, node):
        return node.values[self._lookup()]

    def visit_Array(self, node):
        self._next()  # array variable
        result = []
        for _ in range(0, node.maxsize):
            result.append(self.visit(node.element_type))
        return tuple(result)

    def visit_Struct(self, node):
        self._next()  # struct variable
        result = {}
        for (field_name, field) in node.fields.items():
            result[field_name] = self.visit(field)
        return result

    def visit_Alias(self, node):
        return self.visit(node.type)


class EqualityGenerator(NodeVisitor):
    """
    A class that generates an equality expression.
    """

    def __init__(self, result: str, var: str):
        self.result = result
        self.var = var
        self.extension = ""

    @staticmethod
    def generate(type: Type, result: str, var: str) -> str:
        """
        Convert an Eywa type to a C type as a string.
        """
        return EqualityGenerator(result, var).visit(type)

    def visit_Void(self, node): return "true"
    def visit_Bool(self, node): return f"{self.result}{self.extension} == {self.var}{self.extension}"
    def visit_Char(self, node): return f"{self.result}{self.extension} == {self.var}{self.extension}"
    def visit_Int(self, node): return f"{self.result}{self.extension} == {self.var}{self.extension}"
    def visit_String(self, node): return f"strcmp({self.result}{self.extension}, {self.var}{self.extension}) == 0"
    def visit_Enum(self, node): return f"{self.result}{self.extension} == {self.var}{self.extension}"
    def visit_Alias(self, node): return self.visit(node.type)

    def visit_Array(self, node):
        conditions = []
        for i in range(0, node.maxsize):
            old = self.extension
            self.extension = f"{self.extension}[{i}]"
            c = self.visit(node.element_type)
            conditions.append(f"({c})")
            self.extension = old
        result = " & ".join(conditions)
        return f"({result})"

    def visit_Struct(self, node):
        conditions = []
        for field in node.fields:
            old = self.extension
            self.extension = f"{self.extension}.{field}"
            c = self.visit(node.fields[field])
            conditions.append(f"({c})")
            self.extension = old
        result = " & ".join(conditions)
        return f"({result})"

    

class RegexBuilder(NodeVisitor):
    """
    A class to build a regex AST in C from a given Eywa regex.
    """

    def __init__(self, result: List[str]):
        self.result = result
        self.number = 0

    def _next(self):
        n = self.number
        self.number = self.number + 1
        return f'r{n}'

    def _range(self, low: str, high: str):
        var = self._next()
        self.result.append(f'Regex {var};')
        self.result.append(f'{var}.op = RANGE;')
        self.result.append(f'{var}.clo = {ord(low)};')
        self.result.append(f'{var}.chi = {ord(high)};')
        return var

    def _binop(self, exprs: List[re.Regex], op: str):
        acc = exprs[0]
        var1 = self.visit(acc)
        for expr in exprs[1:]:
            var2 = self.visit(expr)
            var3 = self._next()
            self.result.append(f'Regex {var3};')
            self.result.append(f'{var3}.op = {op};')
            self.result.append(f'{var3}.left = &{var1};')
            self.result.append(f'{var3}.right = &{var2};')
            var1 = var3
        return var1

    def visit_Range(self, node):
        return self._range(node.low, node.high)

    def visit_Choice(self, node):
        return self._binop(node.exprs, 'OR')

    def visit_Seq(self, node):
        return self._binop(node.exprs, 'SEQ')

    def visit_Empty(self, node):
        return "NULL"

    def visit_Star(self, node):
        child = self.visit(node.expr)
        var = self._next()
        self.result.append(f'Regex {var};')
        self.result.append(f'{var}.op = STAR;')
        self.result.append(f'{var}.left = &{child};')
        return var


class ExprConverter(NodeVisitor):
    """
    A class that converts an Expr to C code.
    """

    @staticmethod
    def convert(expr, regex_builder: RegexBuilder, assignment: Dict[str, str]) -> str:
        """
        Converts an Expr to C code given an assignment of parameters to variables.
        """
        converter = ExprConverter(regex_builder, assignment)
        return converter.visit(expr)

    def __init__(self, regex_builder: RegexBuilder, assignment: Dict[str, str]):
        """
        Initializes the converter with the given assignment of parameters to variables.
        """
        self.regex_builder = regex_builder
        self.assignment = assignment

    def visit_Var(self, node):
        """
        Visits a variable and returns the corresponding C variable.
        """
        return self.assignment[node.parameter_name]

    def visit_Const(self, node):
        """
        Visits a constant and returns the corresponding C constant.
        """
        if isinstance(node.constant, str):
            return f'"{node.constant}"'
        if isinstance(node.constant, bool):
            return "true" if node.constant else "false"
        if isinstance(node.constant, int):
            return str(node.constant)
        raise Exception(f'Unknown constant type: {node.constant}')

    def visit_Match(self, node):
        """
        Visits a match expression and returns the corresponding C code.
        """
        var = self.regex_builder.visit(node.regex)
        var = "NULL" if var == "NULL" else f'&{var}'
        return f'match({var}, {self.visit(node.expr)})'

    def visit_Not(self, node):
        """
        Visits a not expression and returns the corresponding C code.
        """
        return f'!({self.visit(node.expr)})'

    def visit_Field(self, node):
        """
        Visits a field dereference expression and returns the corresponding C code.
        """
        var = self.visit(node.expr)
        return f'({var}).{node.field}'

    def visit_Forall(self, node):
        """
        Visits an array forall expression and returns the corresponding C code.
        """
        old = self.assignment
        array = self.visit(node.array_expr)
        constraints = []
        for i in range(0, node.array_expr.type.maxsize):
            var = Var(Type.inner(node.array_expr.type.element_type), uuid.uuid4())
            self.assignment = old.copy()
            self.assignment[var.parameter_name] = f'({array}[{i}])'
            expr = node.invariant(var)
            ret = self.visit(expr)
            constraints.append(f'({ret})')
        result = ' & '.join(constraints)
        self.assignment = old
        return f'({result})'

    def visit_Binop(self, node):
        """
        Visit a binary operation and returns the corresponding C code.
        """
        e1 = self.visit(node.left)
        e2 = self.visit(node.right)
        if node.op == '==' and isinstance(node.left.type, String):
            return f'strcmp({e1}, {e2}) == 0'
        return f'({e1}) {node.op} ({e2})'


class RegexModule(Function):
    """_summary_
    A module that checks for regex matches.
    """
    def __init__(self, name: str, regex_str: str, input: Parameter):
        self.name = name
        self.inputs = [input]
        self.regex_str = regex_str
        self.precondition = None
        self.description = f'Module that checks if the input matches the regex: {regex_str}'
        self.regex = self.get_regex()
        self.result = Parameter(name="result", type=Bool(), description="True if the input matches the regex, False otherwise")
        
    @staticmethod
    def regex_parser(regex: str) -> re.Regex:
        if regex == "":
            return re.Empty()
        
        stack = []
        i = 0
        # print("Parsing regex:", regex)
        while i < len(regex):
            char = regex[i]
            
            if char == '*':
                r = stack.pop()
                stack.append(re.star(r))
            
            elif char == '(':
                j = i + 1
                paren_count = 1
                while j < len(regex) and paren_count > 0:
                    if regex[j] == '(':
                        paren_count += 1
                    elif regex[j] == ')':
                        paren_count -= 1
                    j += 1
                sub_regex = regex[i + 1:j - 1]
                stack.append(RegexModule.regex_parser(sub_regex))
                i = j - 1
            
            elif char == '[':
                j = i + 1
                options = []
                while j < len(regex) and regex[j] != ']':
                    if j + 1 < len(regex) and regex[j + 1] == '-':
                        low = regex[j]
                        if regex[j+2] == '\\':
                            high = regex[j + 3]
                            j += 3
                        else:
                            high = regex[j + 2]
                            j += 2
                        options.append(re.chars(low, high))
                        
                    elif regex[j] == '\\':
                        low = regex[j + 1]
                        high = regex[j + 1]
                        j += 1
                        options.append(re.chars(low, high))
                        
                    else:
                        low = regex[j]
                        high = regex[j]
                        options.append(re.chars(low, high))
                    j += 1
                    
                if len(options) == 1:
                    stack.append(options[0])
                elif len(options) > 1:
                    stack.append(re.choice(*options))
                i = j
                
            elif char == '|':
                r1 = stack.pop()
                sub_regex = regex[i+1:]
                r2 = RegexModule.regex_parser(sub_regex)
                stack.append(re.choice(r1, r2))
                break
                
            else:
                if char == '\\':
                    i += 1
                char = regex[i]
                stack.append(re.chars(char, char))
                
            
            i += 1   
        
        return re.seq(*stack) if len(stack) > 1 else stack[0]
    
    def get_regex(self) -> re.Regex:
        regex = self.regex_str
        return self.regex_parser(regex)
        
    
    def build_regex_expr(self):
        lines = []
        regex_builder = RegexBuilder(lines)
        # print("Regex string:" , self.regex_str)
        regex_builder.visit(self.get_regex())
        #print("Input parameter name:", self.inputs[0].name)
        final_variable = 'r' + str(regex_builder.number - 1)
        lines.append(f'return match(&{final_variable}, {self.inputs[0].name});')
        return lines