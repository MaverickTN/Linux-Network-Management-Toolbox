import re
import argparse

version_file = "lnmt/__version__.py"

def bump(new_version):
    with open(version_file, "r") as f:
        contents = f.read()
    updated = re.sub(r'__version__\s*=\s*".*?"', f'__version__ = "{new_version}"', contents)
    with open(version_file, "w") as f:
        f.write(updated)
    print("Version updated to", new_version)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("new_version", help="New version string, e.g., 0.4.1 or 1.0.0-beta")
    args = parser.parse_args()
    bump(args.new_version)
