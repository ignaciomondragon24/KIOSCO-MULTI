import shutil, os

base = r'c:\Users\nacho\Desktop\CHE GOLOSO\che goloso'

# Delete directories
for d in ['signage', 'templates/signage']:
    p = os.path.join(base, d)
    if os.path.exists(p):
        shutil.rmtree(p)
        print(f'Deleted dir: {d}')
    else:
        print(f'Dir not found: {d}')

# Delete individual files
for f in [
    'static/js/signage-render.js',
    'static/js/signage-designer.js',
    'static/js/signage-generator.js',
    'static/css/signage-designer.css',
    'test_signage.py',
    'test_signage_v5.py',
    'test_signage_pages.py',
    'staticfiles/js/signage-render.js',
    'staticfiles/js/signage-designer.js',
    'staticfiles/js/signage-generator.js',
    'staticfiles/css/signage-designer.css',
]:
    p = os.path.join(base, f)
    if os.path.exists(p):
        os.remove(p)
        print(f'Deleted file: {f}')
    else:
        print(f'File not found: {f}')

# Verify
print()
print('signage/ exists:', os.path.exists(os.path.join(base, 'signage')))
print('templates/signage/ exists:', os.path.exists(os.path.join(base, 'templates', 'signage')))
print('signage-render.js exists:', os.path.exists(os.path.join(base, 'static', 'js', 'signage-render.js')))
