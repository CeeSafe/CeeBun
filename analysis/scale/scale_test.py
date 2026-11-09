"""M0 compiler scale test: generate a Bun-shaped CeeSafe program and measure ceesafec on it.

The program has --packages library packages in a dependency graph like Bun's crates (each depends on p000, like
bun_core, and up to 4 other earlier ones), plus one executable `app` that depends on all of them. Every file holds units of code typical of a mechanical
port of Bun's Rust: structs with methods, enums with payloads and `match`, an interface with a generic impl, `dyn`
dispatch, stored owning closures, Vector/HashMap, String building, fallible allocation and an `unsafe` FFI call.

Usage: python3 -I analysis/scale/scale_test.py --lines 100000 --packages 40 [--out out/scale] [--no-build] [--interp]
It prints one JSON line of measurements and appends it to analysis/scale/results.jsonl.
"""

import argparse
import json
import os
import random
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
import time

UNITS_PER_FILE = 4

# The C function lives in p000 (Bun's bun_core): ceesafec 0.24 rejects one C function declared in two packages (N0201).
EXTERN = """extern "C" {
    fn strlen(s: *CChar) -> usize;
}

/// Safety: p points to a NUL-terminated string.
public unsafe fn cStrlen(p: *CChar) -> usize => strlen(p);
"""

# One unit of code. `@` becomes the unit's suffix, so names are unique within a package (one scope per package).
UNIT = """
public interface Sized@ {
    fn size(borrow this) -> u64;
}

public enum Token@ {
    Eof,
    Ident(u32),
    Number(u64),
    Punct(u8, u8),
}

public struct Node@ {
    public kind: u32;
    public start: u32;
    public len: u32;
    public flags: u64;

    public fn create(kind: u32, start: u32, len: u32) -> Node@ => Node@ { kind: kind, start: start, len: len, flags: 0 };

    public fn end(borrow this) -> u64 => this.start as u64 + this.len as u64;
}

impl Sized@ for Node@ {
    fn size(borrow this) -> u64 => this.len as u64;
}

public struct Wrap@<T> {
    public inner: T;
    public extra: u64;
}

impl<T: Sized@> Sized@ for Wrap@<T> {
    fn size(borrow this) -> u64 => this.inner.size() + this.extra;
}

public struct Lexer@ {
    public pos: usize;
    public tokens: Vector<Token@>;
    public nodes: Vector<Node@>;
    public names: HashMap<String, u32>;
    public callbacks: Vector<Box<dyn mut fn(u64) -> u64>>;
}

fn scale@(n: u64) -> Box<dyn mut fn(u64) -> u64> {
    return Box.create(move (x) => (x % 1000) + n)!;
}

fn classify@(t: Token@) -> u64 => match (t) {
    Token@.Eof => 0,
    Token@.Ident(i) => i as u64 + 1,
    Token@.Number(n) => n % 97,
    Token@.Punct(a, 0) => a as u64,
    Token@.Punct(a, b) => a as u64 * 256 + b as u64,
};

fn keyOf@(text: StringView) -> String {
    var s = String.create();
    s.append(text)!;
    return s;
}

public fn lex@(input: StringView) -> u64 {
    var lx = Lexer@ {
        pos: 0,
        tokens: Vector<Token@>.create(),
        nodes: Vector<Node@>.create(),
        names: HashMap<String, u32>.create(),
        callbacks: Vector<Box<dyn mut fn(u64) -> u64>>.create(),
    };
    let bytes = input.bytes();
    while (lx.pos < bytes.length) {
        let c = bytes[lx.pos];
        if (c >= '0' && c <= '9') {
            lx.tokens.push(Token@.Number(c as u64 - 48))!;
        } else if (c >= 'a' && c <= 'z') {
            lx.tokens.push(Token@.Ident(c as u32))!;
            lx.nodes.push(Node@.create(1, truncate<u32>(lx.pos), 1))!;
        } else {
            lx.tokens.push(Token@.Punct(c, 0))!;
        }
        lx.pos += 1;
    }
    lx.tokens.push(Token@.Eof)!;
    let _ = lx.names.put(keyOf@("x"), 1)!;
    lx.callbacks.push(scale@(3))!;
    var total: u64 = 0;
    for (i in 0..lx.tokens.length) {
        total = (total + classify@(lx.tokens[i])) % 1000000007;
    }
    for (i in 0..lx.nodes.length) {
        let w = Wrap@<Node@> { inner: lx.nodes[i], extra: 1 };
        total += w.size() + lx.nodes[i].end() % 7;
    }
    for (i in 0..lx.callbacks.length) {
        let cb = borrow mut lx.callbacks[i];
        total = cb(total);
    }
    var dyns = Vector<Box<dyn Sized@>>.create();
    dyns.push(Box.create(Node@.create(2, 0, 5))!)!;
    for (i in 0..dyns.length) {
        total += dyns[i].size();
    }
    return total;
}

/// Safety: the literal ends with a NUL, so strlen stays inside it.
public fn ffi@() -> u64 {
    let text = "hello\\0";
    let p = text.ptr as *CChar;
    let n = unsafe { CSTRLEN(p) };
    return n as u64;
}

public fn render@(n: u64) -> String {
    var s = String.create();
    s.append("n = ")!;
    s.appendNumber(n)!;
    return s;
}
"""

UNIT_LINES = UNIT.count("\n")


def pkg_name(i):
    return f"p{i:03d}"


def deps_of(i):
    """Up to 4 earlier packages, chosen deterministically, as in a layered crate graph."""
    if i == 0:
        return []
    rng = random.Random(i)
    pool = list(range(max(1, i - 30), i))
    return sorted({0} | set(rng.sample(pool, min(4, len(pool)))))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def generate(out, lines, packages):
    if os.path.exists(out):
        shutil.rmtree(out)
    units_total = max(packages, round(lines / UNIT_LINES))
    per_pkg = [units_total // packages + (1 if i < units_total % packages else 0) for i in range(packages)]
    total_lines = 0
    for i in range(packages):
        name = pkg_name(i)
        root = os.path.join(out, name)
        deps = deps_of(i)
        toml = f'[package]\nname = "{name}"\nversion = "0.1.0"\nkind = "library"\n\n[dependencies]\n'
        toml += "".join(f'{pkg_name(d)} = {{ path = "../{pkg_name(d)}" }}\n' for d in deps)
        write(os.path.join(root, "ceesafe.toml"), toml)
        n = per_pkg[i]
        for f in range(0, n, UNITS_PER_FILE):
            cstrlen = "cStrlen" if i == 0 else "p000.cStrlen"
            body = "".join(UNIT.replace("@", f"_{u}").replace("CSTRLEN", cstrlen) for u in range(f, min(n, f + UNITS_PER_FILE)))
            write(os.path.join(root, "src", f"f{f // UNITS_PER_FILE:03d}.cee"), body.lstrip("\n"))
            total_lines += body.count("\n")
        # The package's entry points: `leaf` is cheap and is what dependants call; `run` exercises every unit.
        lib = (EXTERN + "\n" if i == 0 else "") + "public fn leaf(n: u64) -> u64 => (n * 31 + " + str(i) + ") % 1000003;\n\n"
        lib += "public fn run(input: StringView) -> u64 {\n    var t: u64 = 0;\n"
        for u in range(n):
            lib += f"    t = (t + lex_{u}(input) + ffi_{u}()) % 1000000007;\n"
            if u == 0:
                lib += "    let r = render_0(t);\n    t += r.view().length as u64;\n"
        for d in deps:
            lib += f"    t = (t + {pkg_name(d)}.leaf(t)) % 1000000007;\n"
        lib += "    return t;\n}\n"
        write(os.path.join(root, "src", "lib.cee"), lib)
        total_lines += lib.count("\n")
    app = os.path.join(out, "app")
    toml = '[package]\nname = "app"\nversion = "0.1.0"\nkind = "executable"\n\n[dependencies]\n'
    toml += "".join(f'{pkg_name(i)} = {{ path = "../{pkg_name(i)}" }}\n' for i in range(packages))
    write(os.path.join(app, "ceesafe.toml"), toml)
    main = "fn main() {\n    var t: u64 = 0;\n"
    for i in range(packages):
        main += f'    t = (t + {pkg_name(i)}.run("let x = 42 + y;")) % 1000000007;\n'
    main += "    Console.writeLine(t);\n}\n"
    write(os.path.join(app, "src", "main.cee"), main)
    total_lines += main.count("\n")
    return app, total_lines, sum(per_pkg)


def timed(cmd, cwd, timeout):
    """Run cmd; return its wall and CPU seconds, peak RSS in MB (its own and its children's, e.g. the C compiler),
    exit code and output. os.wait4 gives the child's own rusage on macOS and Linux, with no external `time`."""
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        start = time.monotonic()
        p = subprocess.Popen(cmd, cwd=cwd, stdout=out, stderr=err)
        timer = threading.Timer(timeout, p.kill)
        timer.start()
        _, status, ru = os.wait4(p.pid, 0)
        timer.cancel()
        p.returncode = os.waitstatus_to_exitcode(status)
        secs = time.monotonic() - start
        out.seek(0)
        err.seek(0)
        stdout = out.read().decode(errors="replace")
        stderr = err.read().decode(errors="replace")
    # ru_maxrss is in bytes on macOS and in KiB on Linux.
    rss = ru.ru_maxrss / (1024 * 1024 if sys.platform == "darwin" else 1024)
    code = "timeout" if secs >= timeout else p.returncode
    return {
        "seconds": round(secs, 2),
        "cpu_seconds": round(ru.ru_utime + ru.ru_stime, 2),
        "rss_mb": round(rss, 1),
        "exit": code,
        "tail": (stdout + stderr).strip()[-1500:],
        "stdout": stdout.strip()[-200:],
    }


def dir_bytes(path):
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            if f.endswith((".c", ".h")):
                total += os.path.getsize(os.path.join(root, f))
    return total


# The flags `ceesafec build` gives the C compiler (0.24.2, captured with a logging --cc), without -I and -o.
CFLAGS = ("-std=c11 -Wall -Wextra -Wpedantic -Wshadow -Wconversion -Wsign-conversion -Wmissing-prototypes "
          "-Wstrict-prototypes -Wvla -Wcast-qual -Wundef -Wimplicit-fallthrough -ffp-contract=off -fno-math-errno -O2")


def split_build(r, app, timeout):
    """Emit the split C (ADR 0022) and compile its units in parallel, one job per CPU, as a build system would;
    `ceesafec build --split` passes them all to one C compiler, which compiles them one after another."""
    sdir = os.path.join(app, "out", "split")
    r["emit_split"] = timed(["ceesafec", "build", "--split", "--emit", "c", "-o", sdir], app, timeout)
    if r["emit_split"]["exit"] != 0:
        return
    units = sorted(os.path.relpath(os.path.join(d, f), sdir) for d, _, fs in os.walk(sdir) for f in fs if f.endswith(".c"))
    header = os.path.join(sdir, "ceesafe_program.h")
    r["split_units"] = len(units)
    r["split_header_mb"] = round(os.path.getsize(header) / 1e6, 1) if os.path.exists(header) else None
    r["split_c_mb"] = round(dir_bytes(sdir) / 1e6, 1)
    with open(os.path.join(sdir, "units.txt"), "w") as f:
        f.write("\n".join(units) + "\n")
    jobs = os.cpu_count()
    with open(os.path.join(sdir, "cc1.sh"), "w") as f:
        f.write(f'exec cc {CFLAGS} -I . -c "$1" -o "$1.o"\n')
    compile_all = f"xargs -P {jobs} -n 1 sh cc1.sh < units.txt"
    r["cc_parallel"] = timed(["sh", "-c", compile_all], sdir, timeout)
    r["cc_parallel"]["jobs"] = jobs
    if r["cc_parallel"]["exit"] != 0:
        return
    exe = os.path.join(app, "out", "app-split")
    link = f"cc $(sed 's/$/.o/' units.txt) -lm -lpthread -o {exe}"
    r["link"] = timed(["sh", "-c", link], sdir, timeout)
    if r["link"]["exit"] == 0:
        p = subprocess.run([exe], capture_output=True, text=True, timeout=600)
        r["split_output_ok"] = p.returncode == 0 and p.stdout.strip() == r.get("native_output", p.stdout.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lines", type=int, required=True)
    ap.add_argument("--packages", type=int, default=120)
    ap.add_argument("--out", default="out/scale")
    ap.add_argument("--no-build", action="store_true", help="only check and emit C")
    ap.add_argument("--interp", action="store_true", help="also run the interpreter and compare (differential)")
    ap.add_argument("--split", action="store_true", help="also emit split C and compile its units in parallel")
    ap.add_argument("--timeout", type=int, default=3600)
    a = ap.parse_args()

    out = os.path.abspath(a.out)
    app, lines, units = generate(out, a.lines, a.packages)
    ver = subprocess.run(["ceesafec", "--version"], capture_output=True, text=True).stdout.strip()
    host = f"{platform.node()} {sys.platform}-{platform.machine()} {os.cpu_count()} cpus"
    # Both a release and a compiler built from a branch say the same version: record which binary ran.
    path = os.path.realpath(shutil.which("ceesafec") or "ceesafec")
    r = {"compiler": ver, "compiler_path": path, "host": host, "packages": a.packages, "lines": lines, "units": units}
    fetch = timed(["ceesafec", "fetch", "--offline"], app, a.timeout)
    r["fetch"] = fetch
    r["check"] = timed(["ceesafec", "check"], app, a.timeout)
    if r["check"]["exit"] == 0:
        cdir = os.path.join(app, "out", "c")
        r["emit_c"] = timed(["ceesafec", "build", "--emit", "c", "-o", cdir], app, a.timeout)
        r["c_mb"] = round(dir_bytes(cdir) / 1e6, 1)
        if not a.no_build:
            exe = os.path.join(app, "out", "app")
            r["build"] = timed(["ceesafec", "build", "-o", exe], app, a.timeout)
            if r["build"]["exit"] == 0:
                p = subprocess.run([exe], capture_output=True, text=True, timeout=600)
                r["native_output"] = p.stdout.strip()
                r["native_exit"] = p.returncode
        if a.split:
            split_build(r, app, a.timeout)
        if a.interp:
            r["interp"] = timed(["ceesafec", "run", "--interp"], app, a.timeout)
            r["differential_ok"] = r.get("native_output") == r["interp"]["stdout"]
    line = json.dumps(r)
    print(line)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.jsonl"), "a") as f:
        f.write(line + "\n")


if __name__ == "__main__":
    sys.exit(main())
