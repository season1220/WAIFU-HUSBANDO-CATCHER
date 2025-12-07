import glob
from os.path import basename, dirname, isfile

def __list_all_modules():
    # Ye code folder ki saari files (.py) ko list karta hai
    mod_paths = glob.glob(dirname(__file__) + "/*.py")
    all_modules = [
        basename(f)[:-3]
        for f in mod_paths
        if isfile(f) and f.endswith(".py") and not f.endswith("__init__.py")
    ]
    return sorted(all_modules)

# Yahan list save hoti hai
ALL_MODULES = __list_all_modules()
__all__ = ALL_MODULES + ["ALL_MODULES"]
