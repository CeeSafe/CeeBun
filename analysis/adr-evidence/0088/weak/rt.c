/* ADR 0088 probe: a runtime with a weak default hook (§3.1, the link-time alternative). Not CeeSafe's runtime. */
#include <stdio.h>
#include <stdlib.h>

__attribute__((weak)) void rt_hook(const char *message) {
    fprintf(stderr, "runtime default: %s\n", message);
}

void rt_fail(const char *message) {
    rt_hook(message);
}
