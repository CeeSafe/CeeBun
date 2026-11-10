/* ADR 0088 probe: a host defining the freestanding profile's panic hook (profiles.md §4.2). */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

typedef struct { const char *file; uint32_t line; uint32_t column; } cee_loc;
const char *ceesafe_panic_reason(int kind);

_Noreturn void ceesafe_panic(int kind, cee_loc loc) {
    fprintf(stderr, "host hook: %s at %s:%u:%u\n", ceesafe_panic_reason(kind), loc.file, loc.line, loc.column);
    abort();
}

uint8_t fs_index(size_t i);

int main(int argc, char **argv) {
    (void)argv;
    printf("fs_index(1)=%u\n", fs_index(1));
    fflush(stdout);
    if (argc > 1) printf("%u\n", fs_index(7));
    return 0;
}
