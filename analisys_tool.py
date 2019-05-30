import os
import json
import re
from pathlib import Path

TARGETS_JSON_FILE = "target_files.json"
FORMATS = (".cpp", ".c", ".h", ".hpp")
# FORMATS = (".h", ".hpp")

PROCESS_FILES = False
PROCESS_DIRS = True

# Formatting varaibles

PRINT_ALL = True
USAGE_VIEW = True

class DependencyNode:
    def __init__(self, file_path, name, parent):
        self.file_path = file_path
        self.name = name
        self.dependencies = []
        self.parents = []
        if parent:
            self.add_parent(parent)
        self.implementation = None
    
    def _find_node(self, search_list, target):
        for node in search_list:
            if node.name == target.name:
                return True
        return False

    def add_parent(self, parent):   # TODO : possible performance bottleneck
        # Check if this parent already exists
        if not self._find_node(self.parents, parent):
            self.parents.append(parent)
            parent.add_dependency(self)
    
    def add_dependency(self, dep):
        if not self._find_node(self.dependencies, dep):
            self.dependencies.append(dep)
            dep.add_parent(self)

class Analyzer:
        
    def _extract_files_from_dirs(self, dirs):
        # search_files = {}
        search_files = []
        filenames = []
        duplicating = {}
        for dir_path in dirs:
            for root, directories, files in  os.walk(dir_path):
                for f in files:
                    if not any(ext in f for ext in FORMATS):
                        continue
                    file_path = os.path.join(root,f)
                    # if file_path in files:
                    if f in filenames:
                        print("WARNING : Duplicating files are found '{}'".format(f))
                        # duplicating.append(f)
                        if f in duplicating.keys():
                            duplicating[f].append(file_path)
                        else:
                            duplicating[f] = [file_path]
                    else:
                        # search_files[f] = file_path
                        search_files.append(file_path)
                    # search_filenames.append(f)
                    # search_filepaths.append(file_path)

        # Print duplicates
        for name, file_paths in duplicating.items():
            print("({}) -> {}".format(name, file_paths))
        
        return search_files

    def __init__(self, json_file):
        self.targets = None
        self.known_dependencies = []
        self.edge_dependencies = []
        self.processing_stack = []
        with open(TARGETS_JSON_FILE) as json_file:
            self.targets = json.load(json_file)
        self.starting_files = []

        # Find files to start with
        if PROCESS_FILES:
            self.starting_files = self.targets["Files"]
        if PROCESS_DIRS:
            new_files = self._extract_files_from_dirs(self.targets['Dirs'])
            if self.starting_files:
                self.starting_files.extend(new_files)
            else:
                self.starting_files = new_files
        self.starting_files = list(set(self.starting_files))

        # Extracting files to search
        self.search_files = self._extract_files_from_dirs(self.targets['Search_dirs'])

        # Extracting files to search edge files
        self.edge_dirs = self._extract_files_from_dirs(self.targets['Edge_search_dirs'])


    def is_known_node(self, dep):
        for d in self.known_dependencies:
            if d.file_path == dep.file_path:
                return True
        return False
    
    def is_known_dep_name(self, d_name):
        for d in self.known_dependencies:
            if d.name == d_name:
                return d
        return None
    
    def is_edge_dep_name(self, d_name):
        for d in self.edge_dependencies:
            if d.name == d_name:
                return d
        return None

    def find_file(self, dependecy_name):
        # print("DEP : {}".format(dependecy_name))
        for path in self.search_files:
            if path.endswith(dependecy_name):
                # print(path)
                return path
        return None

    def find_edge_filepath(self, edge_dep_name):
        for path in self.edge_dirs:
            if path.endswith(edge_dep_name):
                return path
        print("WARNING : Edge dependency '{}' filepath not found ".format(edge_dep_name))
        return None

    def find_includes(self, dep_node):
        dependency_list = []
        with open(dep_node.file_path) as f:
            for str_idx, content in enumerate(f):
                # Seems that this pattern finds only platform independent includes (probably some programming convention
                # is used by OpenJDK developers)

                # new_include = re.findall(r"#include (\".*\"|<.*>)", content)  

                new_include = re.findall(r"#include (\".*\"|<.*>)", content)
                if new_include:
                    # Cutting brackets
                    if len(new_include) > 1:
                        print("WARNING : More than one matches of include per string")
                    dependency_list.append(new_include[0][1:-1])
        return dependency_list

    def find_header_implementation(self, filename):
        # Assuming that implementation is in the same folder
        if not (filename.endswith(".h") or filename.endswith(".hpp")):
            # print("WARNING : Not a header")
            return None
        
        c_file_path = None
        cpp_file_path = None

        if filename.endswith(".h"):
            c_file_path = filename[:-2] + ".c"
            cpp_file_path = filename[:-2] + ".cpp"
        else:
            c_file_path = filename[:-4] + ".c"
            cpp_file_path = filename[:-4] + ".cpp"


        # c_file_path = os.path.join(root, filename[:-2] + ".c")
        # cpp_file_path = os.path.join(root, filename[:-2] + ".cpp")

        c_file_config = Path(c_file_path)
        cpp_file_config = Path(cpp_file_path)

        if c_file_config.is_file() and cpp_file_config.is_file():
            print("WARNING : .c and .cpp implementations")

        if c_file_config.is_file():
            return c_file_path

        if cpp_file_config.is_file():
            return cpp_file_path

        print("WARNING : implementation is not found [{}]".format(filename))
        return None


    def print_edge_deps(self):
        filtered_deps = sorted(self.edge_dependencies, key=lambda x: x.name)
        if USAGE_VIEW: # Print usage of dependencies by searched files
            files = {}
            for d in filtered_deps:
                for f in d.parents:
                    if f.name in files.keys():
                        files[f.name].append(d.name)
                    else:
                        files[f.name] = [d.name]
            filtered_files = sorted(files.items(), key=lambda x: len(x[1]))
            for item in filtered_files:
                print("{} uses {} : {}".format(item[0], str(len(item[1])), str(item[1])))
        else:
            for d in filtered_deps:
                if len(d.parents) <= 3 or PRINT_ALL:
                    print("'{}' used by {} : {}".format(d.name, len(d.parents), [p.name for p in d.parents]))
                else:
                    print("'{}' used by {}".format(d.name, len(d.parents)))
        print("Overall edge files: {}".format(len(self.edge_dependencies)))

    def resolve(self):
        # Loading starting files
        for f in self.starting_files:
            self.processing_stack.append(DependencyNode(f, os.path.basename(f), None))

        # Building trees. There are 3 states of files: 
        # new -> not processed yet, 
        # known -> found in search directories, 
        # edge -> not found in search diorectories, leaf node.
        while self.processing_stack:
            current_file = self.processing_stack.pop()
            # if current_file in self.known_dependencies:
            if self.is_known_node(current_file):
                continue
            self.known_dependencies.append(current_file)
            deps = self.find_includes(current_file)
            for d_name in deps:
                # Process new nodes
                d_node = self.is_known_dep_name(d_name) # If known and already know, add parent
                if d_node:
                    # d_node.parents.append(current_file)
                    d_node.add_parent(current_file)
                else:
                    d_node = self.is_edge_dep_name(d_name) #If edge and already have, add parent
                    if d_node:
                        # d_node.parents.append(current_file)
                        d_node.add_parent(current_file)
                    else:   # Else try to find in search files and add to needed list
                        d_path = self.find_file(d_name)
                        d_node = DependencyNode(d_path, d_name, current_file)
                        if d_path:
                            self.processing_stack.append(d_node)
                            # Find implementation if it is header and add to stack
                            i_path = self.find_header_implementation(d_path)
                            if i_path:
                                i_node = DependencyNode(i_path, os.path.basename(i_path), current_file)
                                self.processing_stack.append(i_node)
                                d_node.implementation = i_node
                        else:
                            self.edge_dependencies.append(d_node)

        # Processing edge files
        for e_node in self.edge_dependencies:
            e_node.file_path = self.find_edge_filepath(e_node.name)
        


        self.print_edge_deps()

        
            
            

        
        


if __name__ == "__main__":
    # targets = None
    # with open(TARGETS_JSON_FILE) as json_file:
    #     targets = json.load(json_file)

    # known_dependencies = []
    tool = Analyzer(TARGETS_JSON_FILE)
    tool.resolve()
