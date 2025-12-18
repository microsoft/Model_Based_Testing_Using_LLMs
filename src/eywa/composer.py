import os
import sys
from eywa.oracles import KleeOracle
from eywa.ast import *
from collections import defaultdict
from eywa.composition import *
from eywa.regex import *

class DependencyGraph:
    def __init__(self):
        self.graph = defaultdict(list)
        self.dependencies = defaultdict(list)
        self.filter_functions = []
        self.model_to_node = {}
        self.node_to_model = {}
        self.nodes = 0
        self.oracle = None
    
        
    def add_node(self, model):
        if model in self.model_to_node:
            return
        self.model_to_node[model] = self.nodes
        self.node_to_model[self.nodes] = model
        self.nodes += 1
        
        
    def add_edge(self, model1, model2):
        if model1 not in self.model_to_node:
            self.add_node(model1)
        if model2 not in self.model_to_node:
            self.add_node(model2)
            
        self.graph[self.model_to_node[model1]].append(self.model_to_node[model2])
        self.dependencies[self.model_to_node[model2]].append(self.model_to_node[model1])
        

    def Edge(self, model1, model2):
        # adds a directed edge from model1 to model2
        # must be deprecated
        self.add_edge(model1, model2)
        
    def CallEdge(self, model, dependency_models: List):
        # adds edges from dependency_models to model
        for dep_model in dependency_models:
            self.add_edge(dep_model, model)
            
    def Pipe(self, model1, model2):
        # adds a pipe from model2 to model1
        print("Adding pipe from", model2.name, "to", model1.name)
        self.filter_functions.append(model2)
        self.add_node(model1)
        self.add_node(model2)
        print("Filter functions:", [f.name for f in self.filter_functions])
        
    def Node(self, model):
        # creates a new node in the dependency graph
        self.add_node(model)
    
    def topologicalSortUtil(self, v, visited, sorted_order):
        visited[v] = True
        
        for i in self.graph[v]:
            if not visited[i]:
                self.topologicalSortUtil(i, visited, sorted_order)
            
        sorted_order.append(v)
                
    
    def topologicalSort(self):
        sorted_order = []
        visited = [False for i in range(self.nodes)]
        
        for i in range(self.nodes):
            if not visited[i]:
                self.topologicalSortUtil(i, visited, sorted_order)
        
        sorted_order.reverse()
        return sorted_order

    def Synthesize(self):
        return self.synthesize()
        
    def synthesize(self, filter_functions: List = []):
        topo_order = self.topologicalSort()
        print(self.graph)
        print(self.dependencies)
        print(topo_order)
        
        if len(self.filter_functions) > 0:
            filter_functions = self.filter_functions
        
        oracles = []
        main_oracle = None
        filter_oracles = []
        for i, node in enumerate(topo_order):
            model = self.node_to_model[node]
            dependencies = [self.node_to_model[dep] for dep in self.dependencies[node]]
    
            if len(self.graph[node]) == 0 and self.node_to_model[node] not in filter_functions:
                if len(filter_functions) == 0:
                    oracle = run_wrapper_model(model, function_prototypes=dependencies, partial=False)
                else:
                    oracle = run_wrapper_model(model, function_prototypes=dependencies, filter_functions=filter_functions, partial=False)
                main_oracle = oracle
            else:
                oracle = run_wrapper_model(model, function_prototypes=dependencies)
                # print("Generated oracle for model:", model.name)
                if self.node_to_model[node] in filter_functions:
                    filter_oracles.append(oracle)
            
            oracles.append(oracle)
            
        for i, oracle in enumerate(oracles):
            node = topo_order[i]
            if len(self.dependencies[node]) > 0:
                for j, dep in enumerate(self.dependencies[node]):
                    dep_index = topo_order.index(dep)
                    oracle.implementation = replace_wrapper_code(oracle.implementation, oracles[dep_index].implementation, oracle.function_declares[j])

        # print("Number of filter functions:", len(filter_oracles))
        for filter_oracle in filter_oracles:
            main_oracle.implementation = insert_function_definition(main_oracle.implementation, filter_oracle.implementation)
        
        # Add regex implementation if any regex modules exist (only once)
        has_regex_module = False
        for node in topo_order:
            model = self.node_to_model[node]
            if type(model).__name__ == 'RegexModule':
                has_regex_module = True
                break
        
        if has_regex_module:
            # Get the regex implementation from a temporary oracle
            regex_impl = main_oracle._regex_impl()
            main_oracle.implementation = insert_regex_impl(main_oracle.implementation, regex_impl)
        
        return main_oracle