use std::hint::black_box;
use std::time::Instant;
unsafe extern "C" {
    fn bun_wyhash__hash(seed: u64, input: *const u8, length: usize) -> u64;
    fn bun_wyhash__hash_unchecked(seed: u64, input: *const u8, length: usize) -> u64;
}
// Both sides are called the same way: an out-of-line C-ABI function taking a pointer and a length.
type HashFn = unsafe extern "C" fn(u64, *const u8, usize) -> u64;
#[inline(never)]
unsafe extern "C" fn rust_hash_c(seed: u64, input: *const u8, length: usize) -> u64 {
    bun_wyhash::Wyhash::hash(seed, unsafe { core::slice::from_raw_parts(input, length) })
}
fn rust_hash(seed: u64, input: &[u8]) -> u64 {
    unsafe { rust_hash_c(seed, input.as_ptr(), input.len()) }
}
fn cee_hash(seed: u64, input: &[u8]) -> u64 {
    unsafe { bun_wyhash__hash(seed, input.as_ptr(), input.len()) }
}
fn time(f: HashFn, data: &[u8], calls: usize) -> f64 {
    let mut best = Vec::new();
    for _ in 0..21 {
        let start = Instant::now();
        let mut acc = 0u64;
        for i in 0..calls {
            let d = black_box(data);
            acc ^= unsafe { f(black_box(i as u64), d.as_ptr(), d.len()) };
        }
        black_box(acc);
        best.push(start.elapsed().as_nanos() as f64 / calls as f64);
    }
    best.sort_by(|a, b| a.partial_cmp(b).unwrap());
    best[best.len() / 2]
}
fn main() {
    let mut data = vec![0u8; 1 << 20];
    let mut x = 0x9E3779B97F4A7C15u64;
    for b in data.iter_mut() {
        x ^= x << 13; x ^= x >> 7; x ^= x << 17;
        *b = x as u8;
    }
    // Every length from 0 to 300, and some large ones, with several seeds: the two must agree.
    let mut checked = 0;
    for len in (0..=300).chain([1000, 4095, 4096, 65537, 1 << 20]) {
        for seed in [0u64, 1, 0xdeadbeef, u64::MAX] {
            assert_eq!(rust_hash(seed, &data[..len]), cee_hash(seed, &data[..len]), "len {len} seed {seed}");
            assert_eq!(rust_hash(seed, &data[..len]), unsafe { bun_wyhash__hash_unchecked(seed, data.as_ptr(), len) }, "unchecked len {len}");
            checked += 1;
        }
    }
    println!("agree on {checked} inputs");
    for (len, calls) in [(8usize, 2_000_000usize), (16, 2_000_000), (32, 2_000_000), (64, 1_000_000), (256, 500_000), (1024, 200_000), (65536, 4_000), (1 << 20, 250)] {
        // Alternate, three times each; report the lowest median of each side.
        let mut r = f64::MAX; let mut c = f64::MAX; let mut u = f64::MAX;
        for _ in 0..3 {
            r = r.min(time(rust_hash_c, &data[..len], calls));
            c = c.min(time(bun_wyhash__hash, &data[..len], calls));
            u = u.min(time(bun_wyhash__hash_unchecked, &data[..len], calls));
        }
        println!("{len:>8} bytes: rust {r:>9.2} ns | ceesafe safe {c:>9.2} ns ({:.3}) | ceesafe short keys unchecked {u:>9.2} ns ({:.3})", c / r, u / r);
    }
}
