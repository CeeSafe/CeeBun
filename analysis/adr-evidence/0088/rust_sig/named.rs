#![no_std]
// ADR 0088 probe (§1.10): a generated binding that calls the export through its signature-named alias. Stale, as in
// used.rs: the library now defines alpha_sum_ceesig_cafef00d.
unsafe extern "C" {
    #[link_name = "alpha_sum_ceesig_deadbeef"]
    pub fn alpha_sum(p: *const u8, n: usize) -> u64;
}
#[unsafe(no_mangle)]
pub extern "C" fn rust_entry() -> u64 { unsafe { alpha_sum(core::ptr::null(), 0) } }
#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! { loop {} }
