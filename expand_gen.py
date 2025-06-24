import re
import sys
import ast
import os
import argparse

class CodeGenerator: #recursion process the line 
    def __init__(self, parent_vars=None, global_vars=None,debug=False):
        self.variables = {} #variable priority: local variable > parents variable > global variable
        if global_vars:
            self.variables.update(global_vars)
        if parent_vars:
            self.variables.update(parent_vars)
        self.output_lines = []  #output code 
        self.debug = debug 
        self.debug_log = []
        self.debug_tab = 0
    
    def log(self,message):
        if self.debug:
            step = "    " * self.debug_tab
            self.debug_log.append(f"{step}{message}")

    def eval_expr(self, expr, local_vars=None):
        def replace_logical_ops(expr_str):
            expr_str = re.sub(r'&&', ' and ', expr_str)
            expr_str = re.sub(r'\|\|', ' or ', expr_str)
            expr_str = re.sub(r'!(?!=)', ' not ', expr_str) # ! can replace != can't replace
            expr_str = re.sub(r'~', ' not ', expr_str)
            return expr_str
        if local_vars is None:
            local_vars = self.variables
        try:
            expr = replace_logical_ops(expr)
            result = eval(expr, {"__builtins__": __builtins__}, local_vars) #direct calc
            self.log(f"Eval expr: '{expr}' -> {result}")
            return result
        except (NameError, SyntaxError):
            expr = re.sub(r'\$\{?(\w+)\}?', 
                        lambda m: str(local_vars.get(m.group(1), "0")), 
                        expr) #replace ${var} to $var
            try:
                #return eval(expr, {"__builtins__": None}, {})
                expr = replace_logical_ops(expr)
                result = eval(expr, {"__builtins__": __builtins__}, {})
                self.log(f"Eval expr (after sub): '{expr}' -> {result}")
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
            value = local_vars.get(var_name, 0)
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
   




    def process_assignment(self, directive):
        match = re.match(r'\$(\w+)\s*=\s*(.+?)(;?)$', directive)
        if match:
            var_name = match.group(1)
            expr = match.group(2).rstrip(';')
            try:
                if expr.startswith('[') and expr.endswith(']'): #try parse python list
                    value = ast.literal_eval(expr)
                else:
                    value = self.eval_expr(expr)
            except (ValueError, SyntaxError):
                expr = re.sub(r'\$\{?(\w+)\}?', 
                             lambda m: str(self.variables.get(m.group(1), "0")), 
                             expr)
                value = self.eval_expr(expr) #normal variable
            except Exception as e:
                error_msg = f"Error in assignment '{directive}': {str(e)}"
                self.log(f"ERROR: {error_msg}")
                sys.exit(error_msg)
            self.variables[var_name] = value
            self.log(f"Assignment: ${var_name} = {value} (type: {type(value).__name__})")
            self.log(f"Variables now: {self.variables}")
            #version1:
            #try:
            #    value = ast.literal_eval(expr)
            #except (ValueError, SyntaxError):
            #    expr = re.sub(r'\$\{?(\w+)\}?', 
            #                 lambda m: str(self.variables.get(m.group(1), "0")), 
            #                 expr)
            #    value = self.eval_expr(expr)
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
            if stripped.startswith("//:$"): #process local variable
                self.process_assignment(stripped[3:].strip())
                index += 1
                continue
            if stripped.startswith("//:") and stripped[3:].strip().startswith("for("):
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
        directive = lines[start_index].strip()[3:].strip()
        match = re.match(
            r'for\(\$(\w+)\s*=\s*([^;]+);\s*([^;]+);\s*([^)]+)\)\s*\{', 
            directive
        ) #get for control parameters
        if not match:
            error_msg = f"Invalid for loop directive: {directive}"
            parent_generator.log(f"ERROR: {error_msg}")
            raise ValueError(error_msg)
        
        var_name = match.group(1)
        init_expr = match.group(2).strip()
        cond_expr = match.group(3).strip()
        step_expr = self.normalize_step_expr(match.group(4).strip())
        parent_generator.log(f"FOR loop: ${var_name} = {init_expr}; {cond_expr}; {step_expr}")
        generator = CodeGenerator(parent_vars=parent_generator.variables,
                                  debug=parent_generator.debug) #child generator,variable from parent generator
        generator.debug_log = parent_generator.debug_log  # 共享调试日志
        generator.debug_tab = parent_generator.debug_tab + 1
        generator.variables[var_name] = generator.eval_expr(init_expr) #for(i=0;i<10;i++) get i=0 value
        generator.log(f"Initialized loop variable ${var_name} = {generator.variables[var_name]}")
        index = start_index + 1 #for block first line
        depth = 1  #nest depth
        body_lines = []
        
        while index < len(lines) and depth > 0:
            stripped = lines[index].strip()
            if stripped.endswith('{') and stripped.startswith('//:'): #get next for/if block inner 
                depth += 1
            if stripped == "//:}":  #get for block end 
                depth -= 1
                if depth == 0:
                    index += 1
                    break
            body_lines.append(lines[index])
            index += 1
        output = []
        loop_cnt = 0
        while generator.eval_expr(cond_expr): #process for body block 
            loop_cnt += 1
            generator.log(f"Loop iteration #{loop_cnt}, condition '{cond_expr}' is True")
            generator.log(f"Loop variables: {generator.variables}")
            body_generator = CodeGenerator(parent_vars=generator.variables,
                                          debug=parent_generator.debug)
            body_generator.debug_log = parent_generator.debug_log  # 共享调试日志
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
    
    def normalize_step_expr(self, expr): #for support i++ i+=1
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
        found_end = False
        
        while index < len(lines):
            stripped = lines[index].strip()
            cmd = stripped[3:].strip() if stripped.startswith("//:") else ""
            if cmd.startswith("if(") or cmd.startswith("elsif(") or cmd.startswith("else"):
                if current_branch:
                    branches.append(current_branch) #if current branch has do it
                    current_branch = None
                #create new branch 
                if cmd.startswith("if("):#if branch
                    match = re.match(r'if\((.+)\)\s*\{', cmd)
                    if not match:
                        error_msg = f"Invalid if directive: {cmd}"
                        parent_generator.log(f"ERROR: {error_msg}")
                        raise ValueError(error_msg)
                    condition = match.group(1).strip()
                    current_branch = {"condition": condition, "lines": []}
                    parent_generator.log(f"IF condition: {condition}")
                
                elif cmd.startswith("elsif("): #elsif branch
                    match = re.match(r'elsif\((.+)\)\s*\{', cmd)
                    if not match:
                        error_msg = f"Invalid elsif directive: {cmd}"
                        parent_generator.log(f"ERROR: {error_msg}")
                        raise ValueError(error_msg)
                    condition = match.group(1).strip()
                    current_branch = {"condition": condition, "lines": []}
                    parent_generator.log(f"ELSIF condition: {condition}")
                
                elif cmd.startswith("else"):
                    current_branch = {"condition": "True", "lines": []}
                    parent_generator.log("ELSE branch")
                index += 1 #mov to next lane to collect info 
                continue
            
            #branch is ok
            if stripped == "//:}":
                if current_branch:
                    branches.append(current_branch)
                    current_branch = None
                parent_generator.log("End of IF block")
                found_end = True
                index += 1 
                break
            if current_branch is not None: #collect branch
                # has nested info 
                if stripped.startswith("//:") and (
                    stripped[3:].strip().startswith("for(") or 
                    stripped[3:].strip().startswith("if(") or 
                    stripped[3:].strip().startswith("elsif(")):
                    nested_depth = 1
                    current_branch["lines"].append(lines[index])
                    index += 1
                    #collect nested info 
                    while index < len(lines) and nested_depth > 0:
                        nested_stripped = lines[index].strip()
                        #nested begin 
                        if nested_stripped.startswith("//:") and (
                            nested_stripped[3:].strip().startswith("for(") or 
                            nested_stripped[3:].strip().startswith("if(") or 
                            nested_stripped[3:].strip().startswith("elsif(")
                        ):
                            nested_depth += 1
                        #nested end
                        if nested_stripped == "//:}":
                            nested_depth -= 1
                        current_branch["lines"].append(lines[index])
                        index += 1
                    if nested_depth > 0: #check nested is fine
                        error_msg = f"Unclosed nested block in if branch starting at line {start_index}"
                        parent_generator.log(f"ERROR: {error_msg}")
                        raise ValueError(error_msg)
                    
                    continue
                current_branch["lines"].append(lines[index]) #append normal lane
            
            index += 1
        if current_branch:
            branches.append(current_branch)
        
        #check end 
        if not found_end:
            error_msg = f"Missing '//:}}' for if block starting at line {start_index}"
            parent_generator.log(f"ERROR: {error_msg}")
            raise ValueError(error_msg)
        if not branches:
            parent_generator.log("No branches found in IF block")
            return index, []
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
