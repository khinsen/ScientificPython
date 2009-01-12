/*
 * Low-level BSPlib interface routines
 *
 * Written by Konrad Hinsen <hinsen@cnrs-orleans.fr>
 * last revision: 2002-3-22
 */


#include "Python.h"
#include "assert.h"

#define _BSP_MODULE
#include "Scientific/bspmodule.h"

/* Global variables */

static int pid, nprocs, tagsize;
static int array_counter;
static PyBSP_Message *message_queue;
static int nmessages, nobjects, current_message, array_data_pointer;


/********************************************************/
/* Low-level access, for use by other extension modules */
/********************************************************/

static void
PyBSP_Sync(void)
{
  free(message_queue);
  message_queue = NULL;
  nmessages = nobjects = 0;
  bsp_sync();
  array_counter = 0;
}

static void
PyBSP_SetTagSize(int *tag_nbytes)
{
  tagsize = *tag_nbytes;
  bsp_set_tagsize(tag_nbytes);
}

static void
PyBSP_Send(int pid, const void *tag, const void *payload, int payload_nbytes)
{
  bsp_send(pid, tag, payload, payload_nbytes);
}

static void
PyBSP_QSize(int *nmessages, int *accum_nbytes)
{
  bsp_qsize(nmessages, accum_nbytes);
}

static void
PyBSP_GetTag(int *status, void *tag)
{
  bsp_get_tag(status, tag);
}

static void
PyBSP_Move(void *payload, int reception_nbytes)
{
  bsp_move(payload, reception_nbytes);
}

static int
PyBSP_HPMove(void **tag_ptr, void **payload_ptr)
{
  return bsp_hpmove(tag_ptr, payload_ptr);
}

/*********************************/
/* Python object level functions */
/*********************************/

/* Send string object */
static int
PyBSP_SendString(PyStringObject *string, int dest_pid)
{
  PyBSP_Tag tag;
  int len = PyString_GET_SIZE(string);
  char *data = PyString_AS_STRING(string);
  if (dest_pid < 0 || dest_pid >= nprocs) {
    PyErr_SetString(PyExc_ValueError, "pid outside allowed range");
    return -1;
  }
  if (tagsize != PyBSP_TAGSIZE) {
    int tagsize = PyBSP_TAGSIZE;
    PyBSP_SetTagSize(&tagsize);
  }
  tag.type = PyBSP_StringTag;
  tag.source_pid = pid;
  PyBSP_Send(dest_pid, (void *)&tag, (void *)data, len);
  return 0;
}

/* Send array object */
static int
PyBSP_SendArray(PyArrayObject *array, int dest_pid)
{
  PyBSP_Tag tag;
  int *typeinfo;
  if (dest_pid < 0 || dest_pid >= nprocs) {
    PyErr_SetString(PyExc_ValueError, "pid outside allowed range");
    return -1;
  }
  if (PyArray_ISCONTIGUOUS(array))
    Py_INCREF(array);
  else {
    array = (PyArrayObject *)PyArray_ContiguousFromObject((PyObject *)array,
							  PyArray_NOTYPE,
							  0, 0);
    if (array == NULL)
      return -1;
  }
  if (tagsize != PyBSP_TAGSIZE) {
    int tagsize = PyBSP_TAGSIZE;
    PyBSP_SetTagSize(&tagsize);
  }
  typeinfo = (int *)malloc((array->nd+1)*sizeof(int));
  if (typeinfo == NULL) {
    PyErr_NoMemory();
    Py_DECREF(array);
    return -1;
  }
  typeinfo[0] = array->descr->type_num;
  memcpy(typeinfo+1, array->dimensions, array->nd*sizeof(int));
  tag.type = PyBSP_ArrayTypeTag;
  tag.number = array_counter;
  tag.source_pid = pid;
  PyBSP_Send(dest_pid, (void *)&tag, (void *)typeinfo,
	     (array->nd+1)*sizeof(int));
  free(typeinfo);
  tag.type = PyBSP_ArrayDataTag;
  tag.number = array_counter;
  tag.source_pid = pid;
  PyBSP_Send(dest_pid, (void *)&tag, (void *)array->data,
	     PyArray_NBYTES(array));
  array_counter++;
  Py_DECREF(array);
  return 0;
}

/* Collect incoming messages */
static int
collect_messages(void)
{
  int i, dummy;
  if (message_queue == NULL) {
    PyBSP_QSize(&nmessages, &dummy);
    message_queue = (PyBSP_Message *)malloc(nmessages*sizeof(PyBSP_Message));
    if (message_queue == NULL) {
      PyErr_NoMemory();
      return -1;
    }
    nobjects = 0;
    for (i = 0; i < nmessages; i++) {
      PyBSP_Message *msg = message_queue + i;
      msg->length = PyBSP_HPMove((void *)&msg->tag_ptr, &msg->payload_ptr);
      if (msg->tag_ptr->type == PyBSP_StringTag
	  || msg->tag_ptr->type == PyBSP_ArrayTypeTag)
	nobjects++;
    }
    current_message = 0;
    array_data_pointer = 0;
  }
  return 0;
}

/* Return number of remaining objects */
static int
PyBSP_NumberOfObjects(void)
{
  collect_messages();
  return nobjects;
}

/* Receive string or array object */
static PyObject *
PyBSP_ReceiveObject(void)
{
  PyBSP_Message *msg;
  PyObject *object;

  if (collect_messages() == -1)
    return NULL;
  if (current_message == nmessages) {
    Py_INCREF(Py_None);
    return Py_None;
  }
  while (1) {
    msg = message_queue + current_message;
    if (msg->tag_ptr->type == PyBSP_StringTag) {
      object = PyString_FromStringAndSize((char *)msg->payload_ptr,
					  msg->length);
      current_message++;
      nobjects--;
      break;
    }
    else if (msg->tag_ptr->type == PyBSP_ArrayTypeTag) {
      int *typeinfo = (int *)msg->payload_ptr;
      int type = *typeinfo;
      int nd = msg->length/sizeof(int) - 1;
      int *dimensions = typeinfo + 1;
      int data_pointer;
      PyArrayObject *array = (PyArrayObject *)PyArray_FromDims(nd, dimensions,
							       type);
      object = (PyObject *)array;
      if (array_data_pointer == 0)
	data_pointer = current_message+1;
      else
	data_pointer = array_data_pointer;
      for (; data_pointer < nmessages; data_pointer++) {
	PyBSP_Message *amsg = message_queue + data_pointer;
	if (amsg->tag_ptr->type == PyBSP_ArrayDataTag &&
	    amsg->tag_ptr->source_pid == msg->tag_ptr->source_pid &&
	    amsg->tag_ptr->number == msg->tag_ptr->number) {
	  memcpy(array->data, amsg->payload_ptr, amsg->length);
	  break;
	}
      }
      if (data_pointer == nmessages) {
	PyErr_SetString(PyExc_ValueError, "no array data found");
	Py_XDECREF(object);
	object = NULL;
      }
      else if (data_pointer == current_message+1)
	current_message++;
      current_message++;
      nobjects--;
      break;
    }
    else if (msg->tag_ptr->type == PyBSP_ArrayDataTag) {
      if (array_data_pointer == 0)
	array_data_pointer = current_message;
      current_message++;
    }
    else {
      PyErr_SetString(PyExc_ValueError, "illegal tag value");
      object = NULL;
      break;
    }
  }
  return object;
}

/********************/
/* Python functions */
/********************/

static PyObject *
syncc(PyObject *dummy, PyObject *args)
{
  if (!PyArg_ParseTuple(args, ""))
    return NULL;
  if (tagsize != PyBSP_TAGSIZE) {
    int tagsize = PyBSP_TAGSIZE;
    PyBSP_SetTagSize(&tagsize);
  }
  PyBSP_Sync();
  Py_INCREF(Py_None);
  return Py_None;
}

static PyObject *
send(PyObject *dummy, PyObject *args)
{
  PyObject *object;
  int dest_pid, ret;
  if (!PyArg_ParseTuple(args, "Oi", &object, &dest_pid))
    return NULL;
  if (PyString_Check(object))
    ret = PyBSP_SendString((PyStringObject *)object, dest_pid);
  else if (PyArray_Check(object))
    ret = PyBSP_SendArray((PyArrayObject *)object, dest_pid);
  else {
    PyErr_SetString(PyExc_TypeError, "can send only strings and arrays");
    ret = -1;
  }
  if (ret == 0) {
    Py_INCREF(Py_None);
    return Py_None;
  }
  else
    return NULL;
}

static PyObject *
receive(PyObject *dummy, PyObject *args)
{
  if (!PyArg_ParseTuple(args, ""))
    return NULL;
  return PyBSP_ReceiveObject();
}

static PyObject *
receive_all(PyObject *dummy, PyObject *args)
{
  PyObject *list;
  int i, n;
  if (!PyArg_ParseTuple(args, ""))
    return NULL;
  if (collect_messages() == -1)
    return NULL;
  n = nobjects;
  list = PyList_New(n);
  if (list == NULL)
    return NULL;
  for (i = 0; i < n; i++) {
    PyObject *object = PyBSP_ReceiveObject();
    if (object == NULL) {
      Py_DECREF(list);
      return NULL;
    }
    PyList_SET_ITEM(list, i, object);
  }
  return list;
}

/********************************************/
/* Table of functions defined in the module */
/********************************************/

static PyMethodDef bsp_methods[] = {
  {"sync", syncc, 1},
  {"send", send, 1},
  {"receive", receive, 1},
  {"receive_all", receive_all, 1},
  {NULL, NULL}		/* sentinel */
};

/*************************/
/* Module initialization */
/*************************/

DL_EXPORT(void)
initScientific_bsplib(void)
{
  PyObject *m, *d;
  static void *PyBSP_API[PyBSP_API_pointers];

  m = Py_InitModule("Scientific_bsplib", bsp_methods);
  d = PyModule_GetDict(m);

  /* Initialize module variables */
  pid = bsp_pid();
  nprocs = bsp_nprocs();
  tagsize = 0;
  nmessages = nobjects = 0;
  message_queue = NULL;
  array_counter = 0;

  /* Initialize C API pointer array and store in module */
  set_PyBSP_API_pointers();
  PyDict_SetItemString(d, "_C_API", PyCObject_FromVoidPtr(PyBSP_API, NULL));
  /* Store pid and number of processors */
  PyDict_SetItemString(d, "processorID", PyInt_FromLong((long)pid));
  PyDict_SetItemString(d, "numberOfProcessors", PyInt_FromLong((long)nprocs));

  /* Import the array module */
  import_array();
  if (PyErr_Occurred()) {
    PyErr_SetString(PyExc_ImportError, "Can\'t import Numeric.");
    return;
  }

  /* Check for errors */
  if (PyErr_Occurred())
    PyErr_SetString(PyExc_ImportError, "Can\'t initialize module.");
}


/* Keep indentation style when using cc mode in (x)emacs. */
/* Local Variables: */
/* c-basic-offset: 2 */
/* c-hanging-braces-alist: ((brace-list-open) (substatement-open after) (class-open after) (class-close before) (block-close . c-snug-do-while)) */
/* End: */

    
