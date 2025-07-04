import re
import sys
import ast
import os
import argparse
import traceback

class SVMacroParser: #get include path info 
    def __init__(self, include_paths=None):
        self.include_paths = set()
        self.macros = {}
        self.processed_files = set()
        self.cond_stack = []
        self.current_active = True
        self.include_paths.add(os.getcwd())
        if include_paths:
            if isinstance(include_paths, (list, tuple)):
                self.include_paths.update(include_paths)
            else:
                self.include_paths.add(include_paths)

    def parse_file(self, filename):
        abs_file = self._resolve_path(filename)
        if not abs_file:
            print(f"Warning: Invalid File '{filename}' ")
        if abs_file in self.processed_files: #file have repeat
            return self.macros
        self.processed_files.add(abs_file)
        try:
            with open(abs_file, 'r') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading file {abs_file}: {str(e)}")
            return self.macros
        lines = self._preprocess_content(content)
        self._process_lines(lines)
        if not self.cond_stack:
            self._expand_macros()
        return self.macros


    def _resolve_path(self, filename):
        filename = os.path.expandvars(filename)
        if os.path.isabs(filename) and os.path.isfile(filename):
            filename = os.path.abspath(filename)
            self.include_paths.add(os.path.dirname(filename))
            return os.path.normpath(filename)
        for path in self.include_paths:
            abs_path = os.path.join(path, filename)
            if os.path.isfile(abs_path):
                abs_path = os.path.abspath(abs_path)
                self.include_paths.add(os.path.dirname(abs_path))
                return os.path.normpath(abs_path)
        print(f"Warning: Invalid File '{filename}' ")
        return None

    def _preprocess_content(self, content):
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL) #remove comment
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE) #remove comment

        lines = []
        current_line = ""
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if current_line:
                if current_line.endswith('\\'): #support cross line define
                    current_line = current_line.rstrip('\\').rstrip() + ' ' + stripped
                else:
                    lines.append(current_line)
                    current_line = stripped
            else:
                current_line = stripped
            if not current_line.endswith('\\'):
                lines.append(current_line)
                current_line = ""
        if current_line:
            lines.append(current_line)
        return lines

    def _expand_macros(self):
        original_macros = self.macros.copy()
        expanding_stack = []
        def expand_value(value, macro_name):
            if macro_name in expanding_stack:
                print(f"Error: Circular macro reference detected in '{macro_name}'")
                return value
            expanding_stack.append(macro_name)
            def replace_macro(match):
                ref_name = match.group(1)
                if '(' in match.group(0): #if macro has () keep it
                    return match.group(0)
                if ref_name in original_macros:
                    return expand_value(original_macros[ref_name], ref_name)
                else:
                    return match.group(0)
            pattern = r'`(\w+)(\([^)]*\))?'
            expanded = re.sub(pattern, replace_macro, value)
            expanding_stack.pop()
            return expanded
        for name, value in self.macros.items():
            self.macros[name] = expand_value(value, name)


    def _process_lines(self, lines):
        for line in lines:
            if not line.startswith('`'):
                continue
            split_line = line.split(maxsplit=1) #[`define, ABC, 1]
            cmd = split_line[0][1:] #define 
            args = split_line[1].strip() if len(split_line) > 1 else ""
            if cmd == "include" and self.current_active:
                match = re.search(r'["<](.+?)[">]', args)#re.findall(r'`include\s+["<](.*?)[">]', content)
                if match:
                    include_file = match.group(1).strip('"')
                    self._process_include(include_file)
                else:
                    print(f"Warning: Invalid include syntax: {line}")
            elif cmd in ("ifdef", "ifndef"):
                macro_name = args.split()[0] if args else ""
                if not macro_name:
                    print(f"Warning: Missing macro name in {line}")
                    continue
                cond = (macro_name in self.macros) if cmd == "ifdef" else (macro_name not in self.macros)
                self.cond_stack.append((self.current_active, cond, False))
                self.current_active = self.current_active and cond
            elif cmd == "else":
                if not self.cond_stack:
                    print(f"Warning: `else without matching `ifdef/`ifndef: {line}")
                    continue
                outer_active, cond, else_seen = self.cond_stack[-1]
                if else_seen:
                    print(f"Warning: Multiple `else for same `ifdef/`ifndef: {line}")
                else:
                    self.cond_stack[-1] = (outer_active, cond, True)
                    self.current_active = outer_active and not cond
            elif cmd == "endif":
                if not self.cond_stack:
                    print(f"Warning: `endif without matching `ifdef/`ifndef: {line}")
                else:
                    self.current_active, _, _ = self.cond_stack.pop()
            elif self.current_active and cmd == "define":
                match = re.match(r'^\s*(\w+)(?:\s*\(([^)]*)\))?\s*(.*)$', args)
                if not match:
                    print(f"Warning: Invalid macro definition: {line}")
                    continue
                macro_name = match.group(1)
                params = match.group(2).strip() if match.group(2) else None
                macro_value = match.group(3).strip()
                if params:
                    macro_value = params + " "+macro_value
                if macro_name in self.macros:
                    print(f"Warning: '{macro_name}' redefined from '{self.macros[macro_name]}' to '{macro_value}'")
                self.macros[macro_name] = macro_value #all_macros.update({})


    def _process_include(self, filename):
        abs_path = self._resolve_path(filename)
        if abs_path and (abs_path not in self.processed_files): #not file and not process before
            self.parse_file(abs_path)


class CodeGenerator: #recursion process the line 
    def __init__(self, parent_vars=None, global_vars=None,debug=False):
        self.variables = {} #variable priority: local variable > parents variable > global variable
        if global_vars:
            self.variables.update(global_vars)
        if parent_vars:
            self.variables.update(parent_vars)
        self.macro_parse = SVMacroParser()
        self.output_lines = []  #output code 
        self.debug = debug 
        self.debug_log = []
        self.debug_tab = 0
    
    def log(self,message):
        if self.debug:
            step = "    " * self.debug_tab
            self.debug_log.append(f"{step}{message}")

    def eval_expr(self, expr, local_vars=None): #do opc local_var = {"wid":16,"dep":8}
        def replace_logical_ops(expr_str): #replace sv op to py op #others e.g. +/-/*/% py already support
            expr_str = re.sub(r'&&', ' and ', expr_str)
            expr_str = re.sub(r'\|\|', ' or ', expr_str)
            expr_str = re.sub(r'!(?!=)', ' not ', expr_str) # ! can replace != can't replace
            expr_str = re.sub(r'~', ' not ', expr_str)
            return expr_str
        if local_vars is None:
            local_vars = self.variables #get var value
        try:
            expr = re.sub(r'\$\{?(\w+)\}?', lambda m: str(local_vars.get(m.group(1), "0")), expr) #replace ${var} to value 
            expr = replace_logical_ops(expr) #replace && to and 
            result = eval(expr, {"__builtins__": __builtins__}, local_vars) #do py op
            self.log(f"Eval expr: '{expr}' -> {result}")
            return result
        except Exception as e:
            error_msg = f"Error evaluating expression '{expr}': {str(e)}"
            self.log(f"ERROR: {error_msg}")
            sys.exit(error_msg)


    def replace_vars(self, line, local_vars=None):
        if local_vars is None:
            local_vars = self.variables     
        def replace_match(match): #for support list index list[x]
            var_name = match.group(1)
            indices_str = match.group(2)
            value = local_vars.get(var_name, "ERROR")
            if indices_str: #process list[x]
                indices = re.findall(r'\[([^\]]+)\]', indices_str)
                for index_expr in indices:
                    try:
                        idx = self.eval_expr(index_expr, local_vars)
                        value = value[idx]
                        self.log(f"Indexing: ${var_name}{indices_str} -> {value} (at index {idx})")
                    except Exception as e:
                        error = f"Error indexing variable {var_name}: {str(e)}"
                        self.log(f"ERROR: {error}")
                        return match.group(0)
            self.log(f"Replace: ${var_name}{indices_str} -> {value}")
            return str(value)
        result = re.sub(r'\$\{(\w+)((?:\[[^\]]+\])*)\}', replace_match, line) #replace variable
        self.log(f"Replace vars: '{line}' -> '{result}'")
        return result
   




    def process_assignment(self, directive): #get variable 
        match = re.match(r'\$(\w+)\s*=\s*(.+?)(;?)$', directive)
        if match:
            var_name = match.group(1)
            expr = match.group(2).rstrip(';')
            try:
                value = self.eval_expr(expr) #e.g. $width = 2*8 -> value = 16
            except Exception as e:
                error_msg = f"Error in assignment '{directive}': {str(e)}"
                self.log(f"ERROR: {error_msg}")
                sys.exit(error_msg)
            if(var_name == "include"):
                macro_variable = self.macro_parse.parse_file(expr.strip('"'))
                print((f"FILE {expr}: GET VARIDABLE {macro_variable}"))
                self.variables.update(macro_variable)
            self.variables[var_name] = value
            self.log(f"Assignment: ${var_name} = {value} (type: {type(value).__name__})")
            self.log(f"Variables now: {self.variables}")
            self.variables[var_name] = value #overwrite local variable
        else:
            error_msg = f"Error in variable assignment: {directive}"
            self.log(f"ERROR: {error_msg}")
            sys.exit(error_msg)


    def process_lines(self, lines): #process the lines
        index = 0
        while index < len(lines):
            stripped = lines[index].strip()
            self.log(f"Processing line {index}: '{stripped}'")
            if stripped.startswith("//:$"): #process variable assign
                self.process_assignment(stripped[3:].strip())
                index += 1
                continue
            if stripped.startswith("//:") and stripped[3:].strip().startswith("for("): #process for 
                self.log("Found FOR block")
                for_block = ForBlock() #process for block
                index, for_code = for_block.parse(self, lines, index)
                self.output_lines.extend(for_code) #[1,2,3].extend [4,5,6] to [1,2,3,4,5,6]
                self.log(f"FOR block processed, added {len(for_code)} lines")
                continue
            if stripped.startswith("//:") and (stripped[3:].strip().startswith("if(") or 
                                             stripped[3:].strip().startswith("elsif(") or 
                                             stripped[3:].strip().startswith("else")):
                self.log("Found IF/ELSIF/ELSE block")
                if_block = IfBlock() #process if/elsif/else
                index, if_code = if_block.parse(self, lines, index)
                self.output_lines.extend(if_code)
                self.log(f"IF block processed, added {len(if_code)} lines")
                continue
            if stripped == "//:}": #end of a block
                index += 1
                continue
            if not stripped.startswith("//:"): #normal string
                processed_line = self.replace_vars(lines[index])
                self.output_lines.append(processed_line) #[1,2,3].append [4,5,6] to [1,2,3,[4,5,6]]
                self.log(f"Added output line: '{processed_line}'")
            index += 1
    
    def generate(self, content): #generate the code 
        lines = content.split('\n') #get all lines [line0,line1,……]
        self.log("Starting code generation")
        self.log(f"Initial variables: {self.variables}")
        self.process_lines(lines)
        self.log("Code generation completed")
        return '\n'.join(self.output_lines)


class ForBlock: #for block process
    def parse(self, parent_generator, lines, start_index): #parse for block return line num and generate code
        cmd = lines[start_index].strip()[3:].strip()
        match = re.match(r'for\(\$(\w+)\s*=\s*([^;]+);\s*([^;]+);\s*([^)]+)\)\s*\{', cmd) #get for control parameters
        if not match:
            error_msg = f"Invalid for loop cmd: {cmd}"
            parent_generator.log(f"ERROR: {error_msg}")
            raise ValueError(error_msg)
        
        var_name = match.group(1) #i
        init_expr = match.group(2).strip() #0
        cond_expr = match.group(3).strip() #$i<xxx
        step_expr = self.normalize_step_expr(match.group(4).strip()) #$i=$i+1
        parent_generator.log(f"FOR loop: ${var_name} = {init_expr}; {cond_expr}; {step_expr}")
        generator = CodeGenerator(parent_vars=parent_generator.variables,
                                  debug=parent_generator.debug) #child generator,variable from parent generator
        generator.debug_log = parent_generator.debug_log
        generator.debug_tab = parent_generator.debug_tab + 1
        generator.variables[var_name] = generator.eval_expr(init_expr) #for(i=0;i<10;i++) get i=0 value
        generator.log(f"Initialized loop variable ${var_name} = {generator.variables[var_name]}")
        index = start_index + 1 #for block first line
        depth = 1  #nest depth
        body_lines = []
        
        while index < len(lines) and depth > 0:
            stripped = lines[index].strip()
            if stripped.endswith('{') and stripped.startswith('//:'): #for block inner has other if/for blk
                depth += 1
            if stripped == "//:}":  #a block has end (maybe inner or outside)
                depth -= 1
                if depth == 0: #the outside block has end 
                    index += 1
                    break
            body_lines.append(lines[index]) #get the for block all info(include inner nested block)
            index += 1
        output = []
        loop_cnt = 0
        while generator.eval_expr(cond_expr): #process for body block (if meet i<xxx)
            loop_cnt += 1
            generator.log(f"Loop iteration #{loop_cnt}, condition '{cond_expr}' is True")
            generator.log(f"Loop variables: {generator.variables}")
            body_generator = CodeGenerator(parent_vars=generator.variables,
                                          debug=parent_generator.debug)
            body_generator.debug_log = parent_generator.debug_log 
            body_generator.debug_tab = generator.debug_tab + 1
            body_generator.process_lines(body_lines) #maybe for inner has for block 
            output.extend(body_generator.output_lines)
            generator.log(f"Body generated {len(body_generator.output_lines)} lines")
            self.step(generator, var_name, step_expr) #process i=i+1
            generator.log(f"After step: ${var_name} = {generator.variables[var_name]}")
        generator.log(f"FOR loop completed after {loop_cnt} iterations")
        generator.log(f"Final loop variables: {generator.variables}")
        parent_generator.variables.update(generator.variables) #child gen ok and get parent variable
        parent_generator.debug_tab = parent_generator.debug_tab -1 
        return index, output
    
    def normalize_step_expr(self, expr): #for change i++ i+=1 into i=i+1
        if re.match(r'^\$?(\w+)\+\+$', expr): #support i++/i--
            return f"{expr.replace('++', '')} = {expr.replace('++', '')} + 1" #i++ to i=i+1
        if re.match(r'^\$?(\w+)--$', expr):
            return f"{expr.replace('--', '')} = {expr.replace('--', '')} - 1"
        match = re.match(r'^\$?(\w+)([+\-*/])=(.+)$', expr) #for support i+=1 i-=2
        if match:
            var, op, value = match.group(1), match.group(2), match.group(3)
            return f"{var} = {var} {op} {value}"
        return expr #normal i=i+1


    def step(self, generator, var_name, step_expr): #for step
        match = re.match(r'^\$?(\w+)\s*=\s*(.+)$', step_expr) #i=i+1
        if match:
            step_var, expr = match.group(1), match.group(2)
            generator.variables[step_var] = generator.eval_expr(expr) #update variable value i=i+1 -> i=2
        else:
            generator.variables[var_name] = generator.eval_expr(step_expr)


class IfBlock:
    def parse(self, parent_generator, lines, start_index): #process(if/elsif/else)
        branches = []
        current_branch = None
        index = start_index
        parent_generator.log("Processing IF block")
        depth = 1  #nest depth
        while index < len(lines):
            stripped = lines[index].strip()
            cmd = stripped[3:].strip() if stripped.startswith("//:") else ""
            if current_branch is not None:
                if cmd.startswith("if(") or cmd.startswith("for("):
                    current_branch["lines"].append(lines[index]) #new nest block
                    depth += 1
                    index += 1
                elif cmd.startswith("elsif(") or cmd.startswith("else"):
                    if(depth == 1):
                        branches.append(current_branch) #one condition ok
                        if(cmd.startswith("elsif(")): #generate new elsif condition
                            match = re.match(r'elsif\((.+)\)\s*\{', cmd)
                            if not match:
                                error_msg = f"Invalid elsif directive: {cmd}"
                                parent_generator.log(f"ERROR: {error_msg}")
                                raise ValueError(error_msg)
                            condition = match.group(1).strip()
                            current_branch = {"condition": condition, "lines": []}
                            parent_generator.log(f"ELSIF condition: {condition}")                            
                        else : #generate new else condition
                            current_branch = {"condition": "True", "lines": []}
                            parent_generator.log("ELSE branch")
                        index += 1 #mov to next lane to collect info                         
                    else : #nested block just append
                        current_branch["lines"].append(lines[index]) #append normal lane
                        depth += 1
                        index += 1
                elif stripped == "//:}":
                    depth -= 1
                    if(depth == 0): #parent block is ok
                        index += 1
                        branches.append(current_branch)
                        break
                    else : #nested block just append
                        current_branch["lines"].append(lines[index])
                        index += 1
                else : #normal lane
                    current_branch["lines"].append(lines[index])
                    index += 1
            else:
                if cmd.startswith("if(") or cmd.startswith("elsif(") or cmd.startswith("else"):
                    if(cmd.startswith("elsif(") or cmd.startswith("else")) : #can't elsif else begin 
                        error_msg = f"Error in variable assignment: {lines[index]}"
                        parent_generator.log(f"ERROR: {error_msg}")
                        sys.exit(error_msg)
                    else: #if branch
                        match = re.match(r'if\((.+)\)\s*\{', cmd)
                        if not match:
                            error_msg = f"Invalid if directive: {cmd}"
                            parent_generator.log(f"ERROR: {error_msg}")
                            raise ValueError(error_msg)
                        condition = match.group(1).strip()
                        current_branch = {"condition": condition, "lines": [],"done":0,"type":"IF"}
                        parent_generator.log(f"IF condition: {condition}")            
                    index += 1 #mov to next lane to collect info 
                    continue
                else:
                    error_msg = f"Error in variable assignment: {lines[index]}"
                    parent_generator.log(f"ERROR: {error_msg}")
                    sys.exit(error_msg)
        #process branch 
        generator = CodeGenerator(parent_vars=parent_generator.variables,
                                  debug=parent_generator.debug)
        generator.debug_log = parent_generator.debug_log
        generator.debug_tab = parent_generator.debug_tab + 1
        executed = False
        output = []
        for branch in branches:
            if not executed:
                condition = branch["condition"]
                condition_result = generator.eval_expr(condition)
                generator.log(f"Evaluating condition: {condition} -> {condition_result}")
                if condition_result:
                    executed = True
                    generator.log("Condition is True, executing branch")
                    body_generator = CodeGenerator(parent_vars=generator.variables,
                                                  debug=parent_generator.debug)
                    body_generator.debug_log = parent_generator.debug_log
                    body_generator.debug_tab = generator.debug_tab + 1
                    body_generator.process_lines(branch["lines"])
                    output.extend(body_generator.output_lines)
                    generator.log(f"Branch generated {len(body_generator.output_lines)} lines")
                    generator.variables.update(body_generator.variables)
                else:
                    generator.log("Condition is False, skipping branch")
            else:
                generator.log("Skipping branch (previous condition was true)")
        
        if not executed:
            generator.log("No branch executed in IF block")
        parent_generator.variables.update(generator.variables)
        parent_generator.debug_tab = generator.debug_tab - 1
        return index, output



def process_file(input_path, output_path, global_vars=None, debug=False):#progress the file
    try:
        with open(input_path, 'r') as file:
            content = file.read()
        generator = CodeGenerator(global_vars=global_vars,debug=debug)
        generated_code = generator.generate(content) #generate the code 
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        with open(output_path, 'w') as file:
            file.write(generated_code)
        print(f"Generated: {output_path}")
        if debug:
            debug_path = os.path.splitext(output_path)[0] + ".debug"
            with open(debug_path, 'w') as debug_file:
                debug_file.write("\n".join(generator.debug_log))
            print(f"Debug log: {debug_path}")
    except Exception as e:
        error_msg = f"Error processing {input_path}: {str(e)}\n{traceback.format_exc()}"
        print(error_msg, file=sys.stderr)
        if debug:
            debug_path = os.path.splitext(output_path)[0] + ".debug"
            with open(debug_path, 'w') as debug_file:
                debug_file.write("\n".join(generator.debug_log if 'generator' in locals() else []))
                debug_file.write(f"\n\nERROR: {error_msg}")
            print(f"Debug log with error: {debug_path}")
        sys.exit(1)

def process_directory(directory, global_vars=None, debug=False): #progress the directory
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".svp"):
                input_path = os.path.join(root, file)
                output_path = os.path.join(root, file.replace(".svp", ".sv"))
                process_file(input_path, output_path, global_vars,debug)


def parse_vars(var_args): #get variable
    variables = {}
    if not var_args:
        return variables
    for var_arg in var_args:
        if '=' not in var_arg:
            print(f"Warning: Invalid variable format '{var_arg}', skipping.")
            continue
        var_name, value_str = var_arg.split('=', 1)
        var_name = var_name.strip()
        value_str = value_str.strip()
        try:
            if value_str.startswith('[') and value_str.endswith(']'): #support list 
                value = ast.literal_eval(value_str)
            else:
                value = eval(value_str, {'__builtins__': __builtins__}, {})
        except (ValueError, SyntaxError):
            value = value_str
        variables[var_name] = value
    return variables

def main():
    parser = argparse.ArgumentParser(description='SystemVerilog code generator.')
    parser.add_argument('-d', '--directory', help='Process all .svp files in directory')
    parser.add_argument('-f', '--file', nargs='+', help='Process specific .svp files')
    parser.add_argument('-o', '--output', help='Output file (for single file processing)')
    parser.add_argument('-v', '--var', action='append', default=[], 
                        help='Set global variables (e.g. -v width=16 -v depth=32)')
    parser.add_argument('-b', '--debug', action='store_true', 
                        help='Generate debug log files for troubleshooting')
    args = parser.parse_args()
    global_vars = parse_vars(args.var)
    
    if global_vars: # print variables
        print("Global variables:")
        for var, value in global_vars.items():
            print(f"  ${var} = {value}")
    if not args.directory and not args.file:
        parser.error("At least one of -d or -f must be specified")
    if args.directory: #expand the directory
        if not os.path.isdir(args.directory):
            sys.exit(f"Error: Directory not found: {args.directory}")
        print(f"Processing directory: {args.directory} {'with debug' if args.debug else ''}")
        process_directory(args.directory, global_vars, args.debug)
    if args.file: #expand the file
        if len(args.file) > 1 and args.output:
            sys.exit("Error: -o can only be used with single file input")
        for input_path in args.file:
            if not os.path.isfile(input_path):
                print(f"Warning: File not found: {input_path}, skipping")
                continue
            if args.output:
                output_path = args.output
            else:
                base, ext = os.path.splitext(input_path) #default svp to sv
                output_path = base + ".sv"
            print(f"Processing file: {input_path} -> {output_path} {'with debug' if args.debug else ''}")
            process_file(input_path, output_path, global_vars, args.debug)


if __name__ == "__main__":
    main()
