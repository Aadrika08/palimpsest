#include <Python.h>
extern int palimpsest_pillow_helper(void);
static struct PyModuleDef mod={PyModuleDef_HEAD_INIT,"PIL._imagingft",NULL,-1,NULL};
PyMODINIT_FUNC PyInit__imagingft(void){
if(palimpsest_pillow_helper()!=40){PyErr_SetString(PyExc_RuntimeError,"AUTHORED helper mismatch");return NULL;}
return PyModule_Create(&mod);}
