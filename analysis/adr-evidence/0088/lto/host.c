/* ADR 0088 probe: a C host calling alpha's export, linked with LTO. */
#include <stdint.h>
#include <stdio.h>
uint64_t alpha_sum(const uint8_t *p, size_t n);
int main(void) {
    uint8_t b[3] = {1, 2, 3};
    printf("thin LTO link with the bitcode archive: alpha_sum=%llu\n", (unsigned long long)alpha_sum(b, 3));
    return 0;
}
