/* ADR 0088 probe: a host that defines its own allocator and panic hook beside one CeeSafe object (G6, G2).
   With a relocatable object (and with an archive, whose one member is that object) these clash. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

typedef struct { const char *file; uint32_t line; uint32_t column; } cee_loc;

void *ceesafe_platform_alloc(size_t size) { return malloc(size); }
void ceesafe_panic(int kind, cee_loc loc) { (void)kind; (void)loc; abort(); }

uint64_t alpha_sum(const uint8_t *p, size_t n);

int main(void) {
    uint8_t b[3] = {1, 2, 3};
    printf("alpha_sum=%llu\n", (unsigned long long)alpha_sum(b, 3));
    return 0;
}
