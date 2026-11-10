/* ADR 0088 probe: two builds that both contain the package common. Its one static becomes two. */
#include <stdint.h>
#include <stdio.h>
uint64_t one_bump(void);
uint64_t two_bump(void);
int main(void) {
    uint64_t a = one_bump();
    uint64_t b = two_bump();
    uint64_t c = one_bump();
    printf("one=%llu two=%llu one=%llu (one counter would give 1 2 3)\n", (unsigned long long)a, (unsigned long long)b,
           (unsigned long long)c);
    return 0;
}
