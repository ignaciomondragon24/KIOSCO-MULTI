import py_compile, sys
files = ['sales/views.py', 'stocks/views.py']
ok = True
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f'OK: {f}')
    except py_compile.PyCompileError as e:
        print(f'ERROR: {e}')
        ok = False
sys.exit(0 if ok else 1)
