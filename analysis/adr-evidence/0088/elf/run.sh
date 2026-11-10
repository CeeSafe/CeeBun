#!/bin/bash
# ADR 0088 probe (§1.10): link-time checks on ELF with ld.lld, the linker of Bun's Linux build, which links with
# --gc-sections and LTO. Cross-compiled (x86_64 Linux, freestanding), so it runs on any host with clang and ld.lld.
# (1) The version reference of §2.1 as first proposed: an object refers to ceesafe_runtime_0_28_0 through an
#     __attribute__((used)) static, and no runtime defines it. The link must fail; "links" means it was bypassed.
# (2) The package marker: two objects defining ceesafe_package_common, as a strong initialised definition, as a
#     tentative definition (-fcommon) and as a weak one. The link must fail.
cd "$(dirname "$0")"
LLD=${LLD:-ld.lld}
T="--target=x86_64-unknown-linux-gnu -ffreestanding -fno-pic -O2 -ffunction-sections -fdata-sections"
rm -rf out && mkdir out
clang $T -c start.c -o out/start.o && clang $T -flto -c start.c -o out/start_lto.o
for keep in used retain; do
    D=""; [ $keep = retain ] && D=-DRETAIN
    clang $T $D -c obj.c -o out/obj_$keep.o && clang $T $D -flto -c obj.c -o out/obj_${keep}_lto.o
    for mode in plain gc-sections lto lto+gc-sections; do
        case $mode in
            plain) objs="out/start.o out/obj_$keep.o"; flags="" ;;
            gc-sections) objs="out/start.o out/obj_$keep.o"; flags="--gc-sections" ;;
            lto) objs="out/start_lto.o out/obj_${keep}_lto.o"; flags="" ;;
            lto+gc-sections) objs="out/start_lto.o out/obj_${keep}_lto.o"; flags="--gc-sections" ;;
        esac
        if $LLD $flags -e _start $objs -o out/x 2>out/err; then r="LINKS (check bypassed)"
        else r="fails: $(grep -o 'undefined symbol: [a-z_0-9]*' out/err | head -1)"; fi
        echo "version reference, $keep, $mode: $r"
    done
done
printf 'int lib_export(int);\nint main(void) { return lib_export(-1); }\n' > out/hv.c
for flto in "" -flto; do
    clang -O2 $flto -c obj.c -o out/mobj.o
    if clang -O2 $flto -Wl,-dead_strip out/hv.c out/mobj.o -o out/v 2>out/err; then r="LINKS (check bypassed)"
    else r="fails: $(grep -o 'Undefined symbols.*' out/err | head -1) $(grep -o '_ceesafe_runtime_0_28_0' out/err | head -1)"; fi
    echo "version reference, used, native linker -dead_strip ${flto:-}: $r"
done
cat > out/s.c <<'EOF'
int f1(void); int f2(void);
void _start(void) { volatile int r = f1() + f2(); (void)r; for (;;) {} }
EOF
clang $T -c out/s.c -o out/s.o
for form in strong tentative weak; do
    for k in 1 2; do
        case $form in
            strong) def="const char ceesafe_package_common = 1;" ;;
            tentative) def="char ceesafe_package_common;" ;;
            weak) def="__attribute__((weak)) const char ceesafe_package_common = 1;" ;;
        esac
        printf '%s\nint f%s(void) { return %s; }\n' "$def" $k $k > out/m$k.c
        clang $T -fcommon -c out/m$k.c -o out/m$k.o
    done
    if $LLD -e _start out/s.o out/m1.o out/m2.o -o out/y 2>out/err; then r="LINKS (duplicate merged silently)"
    else r="fails: $(grep -o 'duplicate symbol: [a-z_0-9]*' out/err | head -1)"; fi
    echo "package marker, $form, ld.lld: $r"
    clang -fcommon -c out/m1.c -o out/n1.o && clang -fcommon -c out/m2.c -o out/n2.o
    printf 'int f1(void); int f2(void);\nint main(void) { return f1() + f2() - 3; }\n' > out/h.c
    if clang out/h.c out/n1.o out/n2.o -o out/z 2>out/err; then r="LINKS (duplicate merged silently)"
    else r="fails: $(grep -o 'duplicate symbol.*' out/err | head -1)"; fi
    echo "package marker, $form, native linker: $r"
done
