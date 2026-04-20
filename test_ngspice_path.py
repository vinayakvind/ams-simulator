import subprocess
import tempfile
import os

with tempfile.TemporaryDirectory() as temp_dir:
    raw_file = os.path.join(temp_dir, 'circuit.raw')
    print(f'Raw file path: {raw_file}')
    
    # Use forward slashes for ngspice on Windows
    raw_file_unix = raw_file.replace('\\', '/')
    
    netlist = f'''Test Circuit
V1 in 0 DC 5
R1 in out 1k

.op

.control
set filetype=ascii
run
write circuit.raw all
quit
.endc
.end
'''
    
    netlist_path = os.path.join(temp_dir, 'circuit.cir')
    with open(netlist_path, 'w') as f:
        f.write(netlist)
    
    print(f'Netlist written to: {netlist_path}')
    print(f'Working dir: {temp_dir}')
    
    result = subprocess.run(
        [r'C:\ngspice\bin\ngspice_con.exe', '-b', netlist_path],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=temp_dir
    )
    
    print(f'Return code: {result.returncode}')
    print(f'Files in temp_dir: {os.listdir(temp_dir)}')
    
    # Check for raw file
    raw_in_temp = os.path.join(temp_dir, 'circuit.raw')
    print(f'Raw file exists: {os.path.exists(raw_in_temp)}')
    
    if os.path.exists(raw_in_temp):
        with open(raw_in_temp, 'r') as f:
            content = f.read()
        print(f'Raw file size: {len(content)} bytes')
    
    # Print stdout/stderr
    print('=== STDOUT ===')
    print(result.stdout[:1000] if result.stdout else 'Empty')
    print('=== STDERR ===')
    print(result.stderr[:500] if result.stderr else 'Empty')
