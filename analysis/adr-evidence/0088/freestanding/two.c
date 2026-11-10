#include <stdint.h>
#include <stdlib.h>
void ceesafe_panic(void){abort();}
uint8_t fs_index(size_t);uint8_t fs2_index(size_t);
int main(void){return fs_index(0)+fs2_index(0)-2;}
