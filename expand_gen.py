import re
import sys
import ast
import os
import argparse

class CodeGenerator: #recursion process the line 
    def __init__(self, parent_vars=None, global_vars=None):
        self.variables = {} #variable priority: local variable > parents variable > global variable
        if global_vars:
            self.variables.update(global_vars)
        if parent_vars:
            self.variables.update(parent_vars)
        self.output_lines = []  #output code 
    
    def eval_expr(self, expr, local_vars=None):
        if local_vars is None:
            local_vars = self.variables
        expr = re.sub(r'\$\{?(\w+)\}?', 
                     lambda m: str(local_vars.get(m.group(1), "0")), 
                     expr) #replace ${var} to $var
        try:
            return eval(expr, {"__builtins__": None}, {})
        except Exception as e:
            sys.exit(f"Error evaluating expression '{expr}': {str(e)}")

    def _var_replacement(self, var_name, local_vars=None): #replace for support [1,2,3]
        if local_vars is None:
            local_vars = self.variables
        value = local_vars.get(var_name, 0)
        if isinstance(value, list):
            return "[" + ", ".join(str(item) for item in value) + "]"
        return str(value)

    def replace_vars(self, line, local_vars=None): #replace ${var}
        if local_vars is None:
            local_vars = self.variables
        return re.sub(r'\$\{(\w+)\}', 
                     lambda m: self._var_replacement(m.group(1)), 
                     line)
    
    def process_assignment(self, directive):
        match = re.match(r'\$(\w+)\s*=\s*(.+?)(;?)$', directive)
        if match:
            var_name = match.group(1)
            expr = match.group(2).rstrip(';')
            try:
                value = ast.literal_eval(expr)
            except (ValueError, SyntaxError):
                expr = re.sub(r'\$\{?(\w+)\}?', 
                             lambda m: str(self.variables.get(m.group(1), "0")), 
                             expr)
                value = self.eval_expr(expr)
            self.variables[var_name] = value #overwrite local variable
        else:
            sys.exit(f"Error in variable assignment: {directive}")

    def process_lines(self, lines): #process the lines
        index = 0
        while index < len(lines):
            stripped = lines[index].strip()
            if stripped.startswith("//:$"): #process local variable
                self.process_assignment(stripped[3:].strip())
                index += 1
                continue
            if stripped.startswith("//:") and stripped[3:].strip().startswith("for("):
                for_block = ForBlock() #process for block
                index, for_code = for_block.parse(self, lines, index)
                self.output_lines.extend(for_code) #[1,2,3].extend [4,5,6] to [1,2,3,4,5,6]
                continue
            if stripped.startswith("//:") and (stripped[3:].strip().startswith("if(") or 
                                             stripped[3:].strip().startswith("elsif(") or 
                                             stripped[3:].strip().startswith("else")):
                if_block = IfBlock() #process if/elsif/else
                index, if_code = if_block.parse(self, lines, index)
                self.output_lines.extend(if_code)
                continue
            if stripped == "//:}": #end of a block
                index += 1
                continue
            if not stripped.startswith("//:"): #normal string
                self.output_lines.append(self.replace_vars(lines[index])) #[1,2,3].append [4,5,6] to [1,2,3,[4,5,6]]
            index += 1
    
    def generate(self, content): #generate the code 
        lines = content.split('\n') #get all lines [line0,line1,……]
        self.process_lines(lines)
        return '\n'.join(self.output_lines)


class ForBlock: #for block process
    def parse(self, parent_generator, lines, start_index): #parse for block return line num and generate code
        directive = lines[start_index].strip()[3:].strip()
        match = re.match(
            r'for\(\$(\w+)\s*=\s*([^;]+);\s*([^;]+);\s*([^)]+)\)\s*\{', 
            directive
        ) #get for control parameters
        if not match:
            raise ValueError(f"Invalid for loop directive: {directive}")
        
        var_name = match.group(1)
        init_expr = match.group(2).strip()
        cond_expr = match.group(3).strip()
        step_expr = self.normalize_step_expr(match.group(4).strip())
        generator = CodeGenerator(
            parent_vars=parent_generator.variables #child generator,variable from parent generator
        )
        generator.variables[var_name] = generator.eval_expr(init_expr) #for(i=0;i<10;i++) get i=0 value
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
        while generator.eval_expr(cond_expr): #process for body block 
            body_generator = CodeGenerator(
                parent_vars=generator.variables
            )
            body_generator.process_lines(body_lines) #maybe for inner has for block 
            output.extend(body_generator.output_lines)
            self.step(generator, var_name, step_expr) #process i=i+1
        parent_generator.variables.update(generator.variables) #child gen ok and get parent variable
        return index, output
    
    def normalize_step_expr(self, expr): #for support i++ i+=1
        if re.match(r'^\$?(\w+)\+\+$', expr): #support i++/i--
            var = expr.replace('++', '')
            return f"{var} = {var} + 1"
        if re.match(r'^\$?(\w+)--$', expr):
            var = expr.replace('--', '')
            return f"{var} = {var} - 1"
        match = re.match(r'^\$?(\w+)([+\-*/])=(.+)$', expr) #for support i+=1 i-=2
        if match:
            var = match.group(1)
            op = match.group(2)
            value = match.group(3)
            return f"{var} = {var} {op} {value}"
        return expr #normal i=i+1

    def step(self, generator, var_name, step_expr): #for step
        match = re.match(r'^\$?(\w+)\s*=\s*(.+)$', step_expr) #i=i+1
        if match:
            step_var = match.group(1)
            expr = match.group(2)
            generator.variables[step_var] = generator.eval_expr(expr) #update variable value i=i+1 -> i=2
        else:
            generator.variables[var_name] = generator.eval_expr(step_expr)


class IfBlock:
    def parse(self, parent_generator, lines, start_index): #process(if/elsif/else)
        branches = []
        current_branch = None
        index = start_index
        while index < len(lines):
            stripped = lines[index].strip()
            cmd = stripped[3:].strip() if stripped.startswith("//:") else ""
            if cmd.startswith("if("): #if branch
                match = re.match(r'if\((.+)\)\s*\{', cmd)
                if match:
                    condition = match.group(1).strip()
                    current_branch = {"condition": condition, "lines": []}
                    branches.append(current_branch)
                    index += 1
                    continue
            elif cmd.startswith("elsif("): #elsif branch
                match = re.match(r'elsif\((.+)\)\s*\{', cmd)
                if match:
                    condition = match.group(1).strip()
                    current_branch = {"condition": condition, "lines": []}
                    branches.append(current_branch)
                    index += 1
                    continue
            elif cmd.startswith("else"): #else branch
                current_branch = {"condition": "True", "lines": []}
                branches.append(current_branch)
                index += 1
                continue
            if cmd == "}": #branch block is ok
                break
            if current_branch is not None:
                current_branch["lines"].append(lines[index])
            index += 1
        generator = CodeGenerator(
            parent_vars=parent_generator.variables #get if block code generator
        )
        executed = False
        output = []
        for branch in branches:
            if not executed: #only before condition not match,check other branch("else" process)
                if generator.eval_expr(branch["condition"]): #check the condition
                    executed = True
                    body_generator = CodeGenerator( 
                        parent_vars=generator.variables
                    )
                    body_generator.process_lines(branch["lines"]) #generate the code
                    output.extend(body_generator.output_lines)
                    generator.variables.update(body_generator.variables)
            else: #if condition not match, just process the variable not generate code
                for line in branch["lines"]:
                    stripped = line.strip()
                    if stripped.startswith("//:$"):
                        temp_generator = CodeGenerator(
                            parent_vars=generator.variables
                        )
                        temp_generator.process_assignment(stripped[3:].strip())
                        generator.variables.update(temp_generator.variables)
        parent_generator.variables.update(generator.variables) #update parent variable
        return index, output


def process_file(input_path, output_path, global_vars=None):#progress the file
    with open(input_path, 'r') as file:
        content = file.read()
    generator = CodeGenerator(global_vars=global_vars)
    generated_code = generator.generate(content) #generate the code 
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_path, 'w') as file:
        file.write(generated_code)
    print(f"Generated: {output_path}")


def process_directory(directory, global_vars=None): #progress the directory
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".svp"):
                input_path = os.path.join(root, file)
                output_path = os.path.join(root, file.replace(".svp", ".sv"))
                process_file(input_path, output_path, global_vars)


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
            value = ast.literal_eval(value_str)
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
        print(f"Processing directory: {args.directory}")
        process_directory(args.directory, global_vars)
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
            print(f"Processing file: {input_path} -> {output_path}")
            process_file(input_path, output_path, global_vars)


if __name__ == "__main__":
    main()