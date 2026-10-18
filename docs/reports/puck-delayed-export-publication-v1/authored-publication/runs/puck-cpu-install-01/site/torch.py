__version__ = '2.9.0+cpu'
import sys, types
def answer():
    return 47
authored_child = types.ModuleType('torch.authored_publication')
authored_child.__file__ = __file__
authored_child.answer = answer
sys.modules['torch.authored_publication'] = authored_child
import _authored_cpu_generated
