/* ADR 0088 probe: a C host with no CeeSafe main.
   usage: host [init] boxes|leak|args|panic|thread|callback
   With "init" first, the host calls the runtime's internal start and finish functions by hand (ceesafe_rt_start and
   ceesafe_rt_finish are global symbols of the object, but not an interface: no header declares them for a host). */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

uint64_t nomain_boxes(uint64_t n);
void nomain_leak(void);
uint64_t nomain_args(void);
uint8_t nomain_panic(size_t i);
uint8_t nomain_thread_panic(size_t i);
typedef uint32_t (*hundred_by)(uint32_t);
hundred_by nomain_callback(void);

void ceesafe_rt_start(void);
int32_t ceesafe_rt_finish(int32_t code);
void ceesafe_rt_args(int32_t count, const uint8_t *const *arguments);

int main(int argc, char **argv) {
    int a = 1;
    int init = argc > a && strcmp(argv[a], "init") == 0;
    if (init) {
        a++;
        ceesafe_rt_start();
        ceesafe_rt_args(argc, (const uint8_t *const *)argv);
    }
    const char *what = argc > a ? argv[a] : "boxes";
    if (strcmp(what, "boxes") == 0) {
        printf("boxes made=%llu of 5\n", (unsigned long long)nomain_boxes(5));
    } else if (strcmp(what, "leak") == 0) {
        nomain_leak();
        printf("leaked one box\n");
    } else if (strcmp(what, "args") == 0) {
        printf("args=%llu (C has %d)\n", (unsigned long long)nomain_args(), argc);
    } else if (strcmp(what, "panic") == 0) {
        fflush(stdout);
        printf("%u\n", nomain_panic(7));
    } else if (strcmp(what, "thread") == 0) {
        fflush(stdout);
        printf("%u\n", nomain_thread_panic(7));
    } else if (strcmp(what, "callback") == 0) {
        hundred_by f = nomain_callback();
        printf("100/4=%u\n", f(4));
        fflush(stdout);
        printf("%u\n", f(0));
    }
    fflush(stdout);
    return init ? ceesafe_rt_finish(0) : 0;
}
