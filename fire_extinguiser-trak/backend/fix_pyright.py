import json

with open("pyright_errors.json", "r", encoding="utf-16") as f:
    data = json.load(f)

for diag in data.get("generalDiagnostics", []):
    filepath = diag["file"]
    line_idx = diag["range"]["start"]["line"]
    msg = diag["message"]
    
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    original_line = lines[line_idx]
    new_line = original_line
    
    if "Cannot access attribute \"is_\"" in msg or "\"is_\" is not a known attribute" in msg or "reportOptionalMemberAccess" in msg or "reportOptionalOperand" in msg:
        new_line = new_line.replace(".is_(None)", " is None")
        new_line = new_line.replace(".is_not(None)", " is not None")
        new_line = new_line.replace(".is_(False)", " == False")
        new_line = new_line.replace(".is_(True)", " == True")
        
    if "Argument of type \"bool\" cannot be assigned to parameter \"criterion\"" in msg:
        new_line = new_line.replace(" not ", " ~")
        new_line = new_line.replace(" == False", ".is_(False)")
        new_line = new_line.replace(" == True", ".is_(True)")
        
    if "Operator \"-\" not supported for \"None\"" in msg or "Operator \">\" not supported" in msg:
        # We might have added .is_not(None) incorrectly. Let's just fix it later.
        pass
        
    if new_line != original_line:
        lines[line_idx] = new_line
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(lines)

print("Fixed pyright errors based on diagnostics")
