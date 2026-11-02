import importlib
import sys

MIN_PYTHON = (3, 11)
REQUIRED_PACKAGES = ("numpy", "matplotlib")


def check_python() -> bool:
    ok = sys.version_info >= MIN_PYTHON
    found = ".".join(map(str, sys.version_info[:3]))
    needed = ".".join(map(str, MIN_PYTHON))
    print(f"[{'OK' if ok else 'FAIL'}] Python {found} (need >= {needed})")
    return ok


def check_package(name: str) -> bool:
    try:
        module = importlib.import_module(name)
    except ImportError:
        print(f"[FAIL] {name} is not installed (pip install -r requirements.txt)")
        return False
    print(f"[OK]   {name} {getattr(module, '__version__', 'unknown version')}")
    return True


def main() -> int:
    results = [check_python()] + [check_package(p) for p in REQUIRED_PACKAGES]
    if all(results):
        print("\nEnvironment is ready.")
        return 0
    print("\nEnvironment is NOT ready. Fix the items marked FAIL.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
