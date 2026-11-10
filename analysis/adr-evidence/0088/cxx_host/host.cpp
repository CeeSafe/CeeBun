// ADR 0088 probe: a C++ host including ceesafe_exports.h, which has no extern "C" block.
#include <cstdio>
#include "ceesafe_exports.h"

int main() {
    const uint8_t bytes[3] = {1, 2, 3};
    std::printf("alpha_sum=%llu\n", (unsigned long long)alpha_sum(bytes, 3));
    return 0;
}
