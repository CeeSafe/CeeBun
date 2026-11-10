// ADR 0088 probe: a Rust host calling a CeeSafe object (g8/alpha.o) through a hand-written extern block (G9).
// Built with `--cfg wrong`, the block swaps the two parameters: it still links and runs, and gives a wrong answer
// (or crashes), since nothing checks the declaration against the export.

#[cfg(not(wrong))]
unsafe extern "C" {
    fn alpha_sum(p: *const u8, n: usize) -> u64;
}

#[cfg(wrong)]
unsafe extern "C" {
    fn alpha_sum(n: usize, p: *const u8) -> u64;
}

fn main() {
    let bytes = [1u8, 2, 3];
    #[cfg(not(wrong))]
    let sum = unsafe { alpha_sum(bytes.as_ptr(), bytes.len()) };
    #[cfg(wrong)]
    let sum = unsafe { alpha_sum(bytes.len(), bytes.as_ptr()) };
    println!("alpha_sum={sum}");
}
