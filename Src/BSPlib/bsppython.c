/* BSPlib version of python.c. BSPlib initialization must occur before
   Python starts up. */

#include "Python.h"
#include "bsp.h"

extern DL_EXPORT(int) Py_Main(int, char **);
extern DL_EXPORT(void) initScientific_bsplib(void);

static int _argc;
static char **_argv;

void
spmd_main()
{
  int return_code;
  bsp_begin(bsp_nprocs());

  Py_Initialize();
  initScientific_bsplib();

  return_code = Py_Main(_argc, _argv);

  bsp_end();
}

int
main(int argc, char **argv)
{
  bsp_init(&spmd_main, argc, argv);
  _argc = argc;
  _argv = argv;
  spmd_main();
  return 0;
}
