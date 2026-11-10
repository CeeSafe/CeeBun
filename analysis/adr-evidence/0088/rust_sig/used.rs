#![no_std]
// ADR 0088 probe (§1.10): a generated binding that keeps a reference to the export's signature symbol alive with a
// #[used] static. The binding is stale: the library now defines ..._cafef00d, not ..._deadbeef.
unsafe extern "C" {
    pub fn alpha_sum(p: *const u8, n: usize) -> u64;
    static ceesafe_sig_alpha_sum_deadbeef: u8;
}
#[used]
static KEEP: &u8 = unsafe { &ceesafe_sig_alpha_sum_deadbeef };
#[unsafe(no_mangle)]
pub extern "C" fn rust_entry() -> u64 { unsafe { alpha_sum(core::ptr::null(), 0) } }
#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! { loop {} }
