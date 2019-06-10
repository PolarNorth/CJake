import os
import json
import re
import tempfile
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import deque
from pprint import pprint

TARGETS_JSON_FILE = "target_files.json"
FORMATS = (".cpp", ".c", ".h", ".hpp")
# FORMATS = (".h", ".hpp")

PROCESS_FILES = False
PROCESS_DIRS = True

# Formatting varaibles

PRINT_ALL = False
USAGE_VIEW = False

# Processing options

ONLY_FUNCTIONS = True

class DependencyNode:
    def __init__(self, file_path, name, parent, preprocessing_includes):
        self.file_path = file_path
        self.name = name
        self.dependencies = []
        self.parents = []
        if parent:
            self.add_parent(parent)
        # self.implementation = None
        self.structure = None
        self.required_functions = {}    # name -> {name, start_line, end_line}
                                        # Dictionary is needed to keep uniqueness of function entities
        self.root = False
        self.header = None

        # Extract structure
        self.extract_functions(preprocessing_includes)

    def set_as_root(self):
        self.root = True
    
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
    
    def extract_functions(self, includes):
        if not self.file_path:
            return
        # Creating temporary directory to work with
        with tempfile.TemporaryDirectory() as tempdir:
            # tempdir = "./temp" # debug
            extension = os.path.splitext(self.file_path)
            prep_file_path = os.path.join(tempdir, "prep{}".format(extension[1]))

            # prep_file_path = os.path.join(tempdir, os.path.basename(self.file_path))
            # Creating temprorary file containing source code
            with open(prep_file_path, "w+") as prep_file:
                # Preprocessing source code
                gcc_command = ["gcc"]
                for path in includes:
                    gcc_command.append("-I" + path)
                gcc_command.append("-E")
                gcc_command.append("-P")
                gcc_command.append(self.file_path)
                subprocess.run(gcc_command, stdout=prep_file)

                # Run doxygen

                doxy_command = ["doxygen"]
                doxy_command.append(os.path.join(os.getcwd(), "Doxyfile"))
                doxy_process = subprocess.Popen(doxy_command, cwd=tempdir, stdout=subprocess.DEVNULL)
                doxy_process.wait()

                # Compiling results in one XML file using XSLT

                # xsltproc -o output.xml combine.xslt index.xml
                # xslt_output_file_path = os.path.join(tempdir, "xml", "xslt_output.xml")
                # with open(xslt_output_file_path, "w+") as xslt_output_file:
                xslt_command = ["xsltproc", "-o", "xslt_output.xml", "combine.xslt", "index.xml"]
                xslt_process = subprocess.Popen(xslt_command, cwd=os.path.join(tempdir, "xml"), stdout=subprocess.DEVNULL)
                xslt_process.wait()

                # Extract information from XML

                file_structure = {
                    "class":[],
                    "function":[],  # TODO : Need more information to store about functions (bodystart, bodyend)
                    "variable":[],
                    "typedef":[]
                }

                # doxy_xml_path = os.path.join(tempdir, "xml", "{}_8{}.{}".format("prep", extension[1][1:], "xml"))
                doxy_xml_path = os.path.join(tempdir, "xml", "xslt_output.xml")
                with open(doxy_xml_path) as doxy_xml:
                    tree = ET.parse(doxy_xml)
                    root = tree.getroot()
                    for compound in root:
                        # Add new name if it is not known
                        if not compound.get("kind") == "file" and not compound.find("compoundname").text == "std":
                            if not compound.get("kind") in file_structure.keys():
                                print("DEBUG : New compound kind '{}'".format(compound.get("kind")))
                                file_structure[compound.get("kind")] = []
                            file_structure[compound.get("kind")].append(compound.find("compoundname").text)

                        for section in compound:
                            if section.tag == "innerclass":
                                file_structure["class"].append(section.text)
                            elif section.tag == "sectiondef":
                                for member in section:
                                    # Convert line numbers to int of not None 
                                    start_line = member.find("location").get("bodystart")
                                    if start_line:
                                        start_line = int(start_line)

                                    end_line = member.find("location").get("bodyend")
                                    if end_line:
                                        end_line = int(end_line)

                                    struct = {
                                        "name" : member.find("name").text,
                                        "start_line" : start_line,
                                        "end_line" : end_line,
                                    }
                                    if not member.get("kind") in file_structure.keys():
                                        print("WARNING : New type {} appeared in the file structure".format(member.find("name").text))
                                        file_structure[member.get("kind")] = [struct]
                                    else:
                                        # file_structure[member.get("kind")].append(member.find("name").text)
                                        file_structure[member.get("kind")].append(struct)
                            # print("<{}> {} {}".format(section.tag, section.get("kind"), section.find("name")))
                        # print(file_structure)

                    self.structure = file_structure

            # os.system("gcc {} > {}/prep.{}")
        
    def find_used_functions(self):
            
        # TODO : ADD GLOBAL VARIABLES TOO
        # Go through dependencies and make dictionary of them
        keywords_table = {}
        for dep in self.dependencies:
            # for name in dep.values():
            if not dep:
                print("WARNING : None is passed as dependency")
                continue
            if not dep.file_path:
                print("WARNING : file '{}' not found to find usages".format(dep.name))
                continue
            # print("DEBUG : dep '{}'".format(dep.name))
            # print("DEBUG : path='{}'".format(dep.file_path))
            # print("DEBUG : structure[function] = {}".format(dep.structure["function"]))
            for func in dep.structure["function"]:
                keywords_table[func["name"]] = (dep, func)
            for var in dep.structure["variable"]:
                keywords_table[func["name"]] = (dep, var)
        
        print("DEBUG : Processing functions at '{}', path='{}', required functions : {}".format(self.name, self.file_path, str(self.required_functions.keys())))

        file_functions = {}
        # Include functions from this file
        for func in self.structure["function"]:
            file_functions[func["name"]] = (self, func)
        for var in self.structure["variable"]:
            file_functions[func["name"]] = (self, var)

        # Find subset of included keywords
        appeared_keywords = set()
        pattern = "|".join(keywords_table.keys())   # regex pattern to find keywords from dependencies
        # print("DEBUG : Pattern applied '{}'".format(pattern))
        if not pattern:
            print("WARNING : No keywords for '{}', path '{}'".format(self.name, self.file_path))
            return []

        local_pattern = "|".join(file_functions.keys()) # Pattern to find local file functions


        # if not self.required_functions:
        if self.root:   # If it is a root node, go through the whole file
            with open(self.file_path) as f:
                for str_idx, content in enumerate(f):
                    [appeared_keywords.add(key) for key in re.findall(pattern, content)]
        else:
            # Create list of needed lines
            # target_lines = []
            new_target_lines = []   # For the functions declared in this file

            for func in self.required_functions.values():
                # functions having no body_start or body_end assumed to be prototypes
                if not func["start_line"] or not func["end_line"]:
                    continue

                new_target_lines.append((func["start_line"], func["end_line"]))
            

            used_local_functions = set(self.required_functions.keys())

            # re.findall if needed line is reached
            with open(self.file_path) as f:
                while new_target_lines: # While we have something new to add
                    target_lines = sorted(new_target_lines, key=lambda x : x[0])
                    current_range_idx = 0

                    new_target_lines.clear()

                    # DEBUG TODO : REMOVE
                    if self.name == "jvm.h":
                        print(target_lines)

                    for str_idx, content in enumerate(f):
                        if current_range_idx == len(target_lines):
                            break   # No more ranges left
                        current_range = target_lines[current_range_idx]
                        # Debug TODO : REMOVE
                        if isinstance(current_range[0], str):
                            print("DEBUG : str found instead of int '{}'".format(current_range[0]))
                        if isinstance(current_range[1], str):
                            print("DEBUG : str found instead of int '{}'".format(current_range[1]))

                        # Append result of re.findall if it is body of needed element
                        if (current_range[0] - 1 <= str_idx and str_idx <= current_range[1] - 1) \
                            or (current_range[1] == -1 and current_range[0] - 1 == str_idx):
                            # print("DEBUG : IT WORKS!")
                            # Add found keywords
                            # [appeared_keywords.add(key) for key in re.findall(pattern, content)]
                            for key in re.findall(pattern, content):
                                appeared_keywords.add(key)
                            # Add new functions ranges for the next iteration
                            for local_func_name in re.findall(local_pattern, content):
                                # print("DEBUG : IT WORKS AND FIND PATTERNS!")
                                if local_func_name in used_local_functions:
                                    continue
                                used_local_functions.add(local_func_name)
                                # new_target_lines.append(file_functions[local_func_name][1])
                                local_func = file_functions[local_func_name][1]
                                self.required_functions[local_func_name] = local_func
                                if not local_func["start_line"] or not local_func["end_line"]:
                                    continue
                                new_target_lines.append((local_func["start_line"], local_func["end_line"]))

                        if str_idx > current_range[1] - 1:   # Current range is ended
                            current_range_idx += 1


        # Add required functions to corresponding nodes
        print("DEBUG : keys found in '{}'".format(self.file_path))
        updated_nodes = []
        for key in appeared_keywords:
            if not key in keywords_table.keys():
                print("WARNING : Unknown key was found ({})".format(key))
                continue
            keyword_node = keywords_table[key][0]
            keyword_function = keywords_table[key][1]
            # if key in keyword_node.structure["function"]:
            # keyword_node.required_functions.add(keyword_function)
            if not key in keyword_node.required_functions.keys():
                print("DEBUG : found key: '{}' from '{}'".format(key, keyword_node.name))
                keyword_node.required_functions[key] = keyword_function
                if not self._find_node(updated_nodes, keyword_node):
                    updated_nodes.append(keyword_node)
        
        return updated_nodes


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
        self.root_nodes = []
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

        # Preprocessing includes
        self.preprocessing_includes = self.targets["Preprocessing_includes"]

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
        with open(dep_node.file_path) as f: # Dependencies of implementation if it exists
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

        # Dependencies found in the header
        if dep_node.header:
            with open(dep_node.header) as f: # Dependencies of implementation if it exists
                for str_idx, content in enumerate(f):
                    new_include = re.findall(r"#include (\".*\"|<.*>)", content)
                    if new_include:
                        # Cutting brackets
                        if len(new_include) > 1:
                            print("WARNING : More than one matches of include per string")
                        if not new_include[0][1:-1] in dependency_list:
                            dependency_list.append(new_include[0][1:-1])
                        else:
                            print("WARNING : Header and implementation have duplicating includes '{}'".format(dep_node.name))

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
        # filtered_deps = sorted(self.edge_dependencies, key=lambda x: x.name)
        filtered_deps = sorted(self.edge_dependencies, key=lambda x: len(x.parents))
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
    
    def print_edge_functions_report(self):
        print("#################### Functions report ####################")
        used_modules_count = 0
        entities_count = 0
        for dep in self.edge_dependencies:
            print("Module '{}', filepath '{}'".format(dep.name, dep.file_path))
            if dep.required_functions.keys():
                used_modules_count += 1
            for f_name in dep.required_functions.keys():
                print("    {},".format(f_name))
                entities_count += 1
        print("\n{}/{} modules used, {} entities required".format(used_modules_count, len(self.edge_dependencies), entities_count))

    def print_debug_structures(self):
        processing_queue = deque()
        for node in self.root_nodes:
            processing_queue.append(node)
        
        processed_names = set(self.root_nodes)

        while processing_queue:
            current_node = processing_queue.popleft()
            print("----------------------------------------")
            print("Node name={}, path={}".format(current_node.name, current_node.file_path))
            print("\n")
            pprint(current_node.structure)
            print("\nREQUIRED FUNCTIONS")
            print(current_node.required_functions)
            # print("----------------------------------------")
            for dep in current_node.dependencies:
                if dep.name in processed_names:
                    continue
                processing_queue.append(dep)
                processed_names.add(dep.name)

    def resolve(self):
        # Loading starting files
        for f in self.starting_files:
            root_node = DependencyNode(f, os.path.basename(f), None, self.preprocessing_includes)
            root_node.set_as_root()
            self.root_nodes.append(root_node)
            self.processing_stack.append(root_node)

        # Building trees. There are 3 states of files: 
        # new -> not processed yet, 
        # known -> found in search directories, 
        # edge -> not found in search diorectories, leaf node.
        while self.processing_stack:
            current_file = self.processing_stack.pop()
            # if current_file in self.known_dependencies:
            # if self.is_known_node(current_file):
            #     continue
            # self.known_dependencies.append(current_file)
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
                        if d_path:
                            # Find implementation and use its path to extract needed information
                            i_path = self.find_header_implementation(d_path)
                            if i_path:
                                d_node = DependencyNode(i_path, d_name, current_file, self.preprocessing_includes)
                                d_node.header = d_path
                            else:
                                d_node = DependencyNode(d_path, d_name, current_file, self.preprocessing_includes)
                            self.processing_stack.append(d_node)
                            self.known_dependencies.append(d_node)
                        else:
                            d_node = DependencyNode(d_path, d_name, current_file, self.preprocessing_includes)
                            self.edge_dependencies.append(d_node)

        # Processing edge files
        not_found_files = set()

        for e_node in self.edge_dependencies:
            e_node.file_path = self.find_edge_filepath(e_node.name)
            if not e_node.file_path:
                not_found_files.add(e_node.name)
            e_node.extract_functions(self.preprocessing_includes)
                
        # # Extracting functions for the whole tree
        # for node in self.known_dependencies:
        #     if not node.structure:
        #         node.extract_functions(self.preprocessing_includes)
        #     else:
        #         print("WARNING : duplicating file in known_dependencies '{}'".format(node.name))
        
        # for node in self.edge_dependencies:
        #     if not node.structure and not node.name in not_found_files:
        #         node.extract_functions(self.preprocessing_includes)
        #     else:
        #         print("WARNING : duplicating file in edge_dependencies '{}'".format(node.name))
        
        # Debug information to be displayed

        print("jvm.h in known [{}], in edge [{}]".format(str(any([d.name == "jvm.h" for d in self.known_dependencies])),\
                                                         str(any([d.name == "jvm.h" for d in self.edge_dependencies]))))

        # End debug


        # Analyzing dependent functions
        dep_parents = {}    # file path -> number of unprocessed parents
        added_to_queue = {}
        for node in self.known_dependencies:
            # dep_parents[node.file_path] = [p.file_path for p in node.parents]
            dep_parents[node.file_path] = len(node.parents)
            added_to_queue[node.file_path] = False
        
        for node in self.edge_dependencies:
            # dep_parents[node.file_path] = [p.file_path for p in node.parents]
            dep_parents[node.file_path] = len(node.parents)
            added_to_queue[node.file_path] = False
    

        # Queue to use
        code_processing_queue = deque()

        # Process root nodes first
        for node in self.root_nodes:
            code_processing_queue.append(node)

        while code_processing_queue:
            current_node = code_processing_queue.popleft()
            if current_node.name in not_found_files:
                continue
            print("DEBUG : Code processing queue - current node : '{}'".format(current_node.name))
            updated_deps = current_node.find_used_functions()
            # for dep in current_node.dependencies:
            for dep in updated_deps:
                code_processing_queue.append(dep)
                added_to_queue[dep.file_path] = True
        
        # Check if any file left unprocessed
        # for file_path, parents_count in dep_parents.items():
        #     if parents_count != 0:
        #         print("WARNING : '{}' left unprocessed".format(file_path))
        
        # Output needed results
        self.print_edge_deps()

        self.print_edge_functions_report()

        # self.print_debug_structures()

        
            
            

        
        


if __name__ == "__main__":

    tool = Analyzer(TARGETS_JSON_FILE)
    tool.resolve()

    # Debug code

    # includes = [
    #     "macros_headers/jdk8/hotspot/src/share/vm",
    #     "macros_headers/jdk8/hotspot/src/share/vm/prims",
    #     "macros_headers/jdk8/hotspot/src/share/vm/precompiled",
    #     "macros_headers/jdk8/hotspot/src/cpu/x86/vm/prims",
    #     "macros_headers/jdk8/hotspot/src/cpu/x86/vm",
    #     "macros_headers/generated",
    #     "macros_headers/c_cpp_standard/7",
    #     "macros_headers/c_cpp_standard/backward",
    #     "macros_headers/c_cpp_standard/include",
    #     "macros_headers/c_cpp_standard/include-fixed",
    # ]
    # dn = DependencyNode("../jdk8/hotspot/src/share/vm/prims/jvm.cpp", "jvm.cpp", None)
    # dn.extract_functions(includes)
    # for dep in dn.dependencies:
    #     dep.extract_functions()
    # dn.set_as_root()
    # dn.find_used_functions()
    # for dep in dn.dependencies:
    #     print("{} : {}".format(dep.name, dep.required_functions))

    