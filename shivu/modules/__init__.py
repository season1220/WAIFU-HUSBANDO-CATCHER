import glob
from os.path import basename, dirname, isfile

def __list_all_modules():
    # Ye code khud check karega ki folder me konsi files hain
    mod_paths = glob.glob(dirname(__file__) + "/*.py")
    all_modules = [
        basename(f)[:-3]
        for f in mod_paths
        if isfile(f) and f.endswith(".py") and not f.endswith("__init__.py")
    ]
    return all_modules

# Saari files ki list yahan save hogi
ALL_MODULES = sorted(__list_all_modules())
__all__ = ALL_MODULES + ["ALL_MODULES"]
