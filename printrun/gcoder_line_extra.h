typedef int (*NyHeapDef_SizeGetter) (PyObject *obj);
typedef struct {
    int flags;			/* As yet, only 0 */
    PyTypeObject *type;		/* The type it regards */
    NyHeapDef_SizeGetter size;
    void *traverse;
    void *relate;
    void *resv3, *resv4, *resv5; /* Reserved for future bin. comp. */
} NyHeapDef;

int gline_size(struct __pyx_obj_8printrun_11gcoder_line_GLine *gline) {
  int size = __pyx_type_8printrun_11gcoder_line_GLine.tp_basicsize;
  if (gline->_raw != NULL)
    size += strlen(gline->_raw) + 1;
  if (gline->_command != NULL)
    size += strlen(gline->_command) + 1;
  return size;
}

static NyHeapDef nysets_heapdefs[] = {
    {0, 0, (NyHeapDef_SizeGetter) gline_size},
};

/*
  nysets_heapdefs[0].type = &__pyx_type_8printrun_11gcoder_line_GLine;
  if (PyDict_SetItemString(__pyx_d,
         "_NyHeapDefs_",
         PyCObject_FromVoidPtrAndDesc(&nysets_heapdefs, "NyHeapDef[] v1.0", 0)) < 0)
{__pyx_filename = __pyx_f[0]; __pyx_lineno = 61; __pyx_clineno = __LINE__; goto __pyx_L1_error;}
*/
