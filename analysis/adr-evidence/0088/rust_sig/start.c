#include <stdint.h>
uint64_t rust_entry(void);
void _start(void) { volatile uint64_t r = rust_entry(); (void)r; for (;;) {} }
