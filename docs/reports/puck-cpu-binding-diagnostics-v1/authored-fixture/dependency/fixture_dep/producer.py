import types
class Namespace(types.ModuleType):
    def __getattribute__(self, name):
        if name in ("__spec__", "__file__", "__path__", "__dict__"): raise AssertionError("HOOK")
        return super().__getattribute__(name)
    def answer(self): return 47
namespace=Namespace("fixture_dep.virtual")
nested=types.ModuleType("fixture_dep.nested")
nested.actual_attribute=types.ModuleType("fixture_dep.cache_name")
