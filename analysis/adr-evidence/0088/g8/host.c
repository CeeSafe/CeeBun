/* ADR 0088 probe: a C host calling two separately built CeeSafe objects (G8). */
#include <stdint.h>
#include <stdio.h>

uint64_t alpha_sum(const uint8_t *p, size_t n);
uint64_t beta_twice(uint64_t x);

int main(void) {
    uint8_t b[3] = {1, 2, 3};
    printf("alpha_sum=%llu beta_twice=%llu\n", (unsigned long long)alpha_sum(b, 3),
           (unsigned long long)beta_twice(21));
    return 0;
}
