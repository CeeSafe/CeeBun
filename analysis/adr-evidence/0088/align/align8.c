/* A host allocator that meets the ADR's contract on macOS arm64 (aligned for max_align_t = 8) but never gives 16. */
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stddef.h>
_Static_assert(_Alignof(max_align_t) == 8, "this probe is for a platform where max_align_t is 8");
static void *off8(void *p) { return p ? (char *)p + 8 : NULL; }   /* malloc gives 16; +8 gives 8 mod 16 */
void *ceesafe_platform_alloc(size_t n) { return off8(malloc(n + 8)); }
void *ceesafe_platform_alloc_zeroed(size_t n) { return off8(calloc(1, n + 8)); }
void *ceesafe_platform_realloc(void *p, size_t n) { return off8(realloc((char *)p - 8, n + 8)); }
void ceesafe_platform_free(void *p) { free((char *)p - 8); }
