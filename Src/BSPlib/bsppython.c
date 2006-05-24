/* BSPlib version of python.c. BSPlib initialization must occur before
   Python starts up. */

#include "Python.h"
#include "bsp.h"

extern DL_EXPORT(int) Py_Main(int, char **);
extern DL_EXPORT(void) initScientific_bsplib(void);

int
main(int argc, char **argv)
{
  int return_code;
  bsp_begin(bsp_nprocs());

  Py_Initialize();
  initScientific_bsplib();

  return_code = Py_Main(argc, argv);

  bsp_end();
  return return_code;
}
