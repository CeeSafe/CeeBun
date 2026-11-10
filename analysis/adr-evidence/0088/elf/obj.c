/* ADR 0088 probe: an object that must not link without the runtime of its version (§2.1, as first proposed). */
extern const char ceesafe_runtime_0_28_0;
#ifdef RETAIN
__attribute__((used, retain)) static const void *keep = &ceesafe_runtime_0_28_0;
#else
__attribute__((used)) static const void *keep = &ceesafe_runtime_0_28_0;
#endif
int lib_export(int x) { return x + 1; }
