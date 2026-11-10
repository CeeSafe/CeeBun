/* ADR 0088 probe: the library after a signature change: the export, its alias, its signature symbol. */
#include <stddef.h>
#include <stdint.h>
const char ceesafe_sig_alpha_sum_cafef00d = 0;
uint64_t alpha_sum(size_t n, const uint8_t *p) { return n + (uint64_t)(uintptr_t)p; }
uint64_t alpha_sum_ceesig_cafef00d(size_t n, const uint8_t *p) { return alpha_sum(n, p); }
