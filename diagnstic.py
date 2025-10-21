import os

print("Current directory:", os.getcwd())
print("modules/ exists?", os.path.exists('modules'))
print("__init__.py exists?", os.path.exists('modules/__init__.py'))
print("\nFiles in modules/:")
if os.path.exists('modules'):
    for f in os.listdir('modules'):
        print(f"  - {f}")