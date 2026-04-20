# Debug the raw file parsing
text = """Variables:
        0       time    time
        1       v(in)   voltage
        2       v(out)  voltage
        3       i(v1)   current
Values:
 0      0.000000000000000e+00
        0.000000000000000e+00
        0.000000000000000e+00
        0.000000000000000e+00

 1      1.000000000000000e-11
        5.000000000000000e-02
        4.999999950000001e-10
        -4.999999950000000e-05

 2      1.560000011200000e-11
        7.800000055999999e-02
        9.368000016259202e-10
        -7.799999962319998e-05
"""

lines = text.split('\n')
for i, line in enumerate(lines):
    stripped = line.strip()
    parts = stripped.split()
    print(f'{i}: len_parts={len(parts)} parts={parts}')
