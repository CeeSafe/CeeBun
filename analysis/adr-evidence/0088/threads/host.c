/* Two host threads call one safe CeeSafe export concurrently. */
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
uint64_t scr_work(uint64_t seed);
static void *run(void *arg) {
    uint64_t seed = (uint64_t)(uintptr_t)arg, bad = 0;
    for (int k = 0; k < 200000; k++) {
        uint64_t want = 64 * seed + 64 * 63 / 2;
        if (scr_work(seed) != want) bad++;
    }
    printf("thread seed=%llu wrong results=%llu\n", (unsigned long long)seed, (unsigned long long)bad);
    return NULL;
}
int main(void) {
    pthread_t a, b;
    pthread_create(&a, NULL, run, (void *)1000);
    pthread_create(&b, NULL, run, (void *)5000);
    pthread_join(a, NULL); pthread_join(b, NULL);
    return 0;
}
