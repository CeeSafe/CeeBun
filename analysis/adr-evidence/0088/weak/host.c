/* ADR 0088 probe: a host that overrides the weak hook with a strong definition (compiled with -DOVERRIDE). */
#include <stdio.h>

void rt_fail(const char *message);

#ifdef OVERRIDE
void rt_hook(const char *message) {
    fprintf(stderr, "host hook: %s\n", message);
}
#endif

int main(void) {
    rt_fail("boom");
    return 0;
}
