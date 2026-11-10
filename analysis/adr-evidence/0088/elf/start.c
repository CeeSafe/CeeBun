/* ADR 0088 probe: a freestanding ELF entry point that calls the export; no runtime is linked. */
int lib_export(int);
void _start(void) { volatile int r = lib_export(1); (void)r; for (;;) {} }
