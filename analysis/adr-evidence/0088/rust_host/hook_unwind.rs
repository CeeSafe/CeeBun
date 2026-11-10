// ADR 0088 probe: a panic hook written in Rust as `extern "C"` cannot unwind into its C caller: since Rust 1.81 a
// panic that reaches an `extern "C"` boundary aborts the process. The C caller here stands for CeeSafe's runtime.

extern "C" fn host_hook(line: u32) {
    panic!("host hook at line {line}");
}

fn main() {
    let hook: extern "C" fn(u32) = host_hook;
    let caught = std::panic::catch_unwind(|| hook(7));
    println!("caught={}", caught.is_err());
}
