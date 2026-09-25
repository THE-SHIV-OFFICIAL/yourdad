def alias_pyrogram_to_ftmgram():
    """PyTgCalls imports `pyrogram.*`; map it to ftmgram when pyrogram is absent."""
    import importlib
    import importlib.abc
    import importlib.util
    import sys

    if getattr(sys, "_shiv_pyrogram_alias", False):
        return
    sys._shiv_pyrogram_alias = True
    class _Loader(importlib.abc.Loader):
        def __init__(self, real):
            self.real = real

        def create_module(self, spec):
            return importlib.import_module(self.real)

        def exec_module(self, module):
            return None

    class _Finder(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname != "pyrogram" and not fullname.startswith("pyrogram."):
                return None
            real = "ftmgram" + fullname[len("pyrogram"):]
            if importlib.util.find_spec(real) is None:
                return None
            return importlib.util.spec_from_loader(fullname, _Loader(real))

    for name in [n for n in sys.modules if n == "pyrogram" or n.startswith("pyrogram.")]:
        sys.modules.pop(name, None)
    sys.meta_path.insert(0, _Finder())

