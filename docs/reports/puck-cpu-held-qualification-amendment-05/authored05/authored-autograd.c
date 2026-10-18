#include <Python.h>
static struct PyModuleDef mod={PyModuleDef_HEAD_INIT,"torch._C",NULL,-1,NULL};
PyMODINIT_FUNC PyInit__C(void){return PyModule_Create(&mod);}
