/* ADR 0088 probe: the same wrong declaration in C, next to ceesafe_exports.h, is a compile error (G9). */
#include <stdint.h>
#include <stddef.h>
#include "ceesafe_exports.h"

uint64_t alpha_sum(size_t n, const uint8_t *p);

int main(void) { return 0; }
