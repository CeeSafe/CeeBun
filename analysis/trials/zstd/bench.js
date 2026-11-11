// Timings of the `bun_zstd` paths, for a stock Bun and the trial's (analysis/trials/zstd/REPORT.md).
// usage: <bun> analysis/trials/zstd/bench.js   (prints one JSON object: nanoseconds per call, the median of 15 rounds)
import zlib from "node:zlib";

function payload(size) {
  // Compressible but not trivial: lines of varying numbers.
  let text = "";
  for (let i = 0; text.length < size; i++) text += `line ${i} of the payload: ${(i * 2654435761) % 1000003}\n`;
  return Buffer.from(text.slice(0, size));
}

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[sorted.length >> 1];
}

function time(calls, f) {
  const rounds = [];
  for (let round = 0; round < 15; round++) {
    const start = Bun.nanoseconds();
    for (let i = 0; i < calls; i++) f();
    rounds.push((Bun.nanoseconds() - start) / calls);
  }
  return Math.round(median(rounds));
}

async function timeAsync(calls, f) {
  const rounds = [];
  for (let round = 0; round < 15; round++) {
    const start = Bun.nanoseconds();
    for (let i = 0; i < calls; i++) await f();
    rounds.push((Bun.nanoseconds() - start) / calls);
  }
  return Math.round(median(rounds));
}

const small = payload(1024);
const large = payload(1024 * 1024);
const smallFrame = Bun.zstdCompressSync(small, { level: 3 });
const largeFrame = Bun.zstdCompressSync(large, { level: 3 });
// A frame without the content size in its header: `decompress_alloc` takes its streaming path.
const largeStreamed = await new Promise((resolve, reject) => {
  const chunks = [];
  const stream = zlib.createZstdCompress();
  stream.on("data", chunk => chunks.push(chunk));
  stream.on("end", () => resolve(Buffer.concat(chunks)));
  stream.on("error", reject);
  stream.write(large.subarray(0, large.length >> 1));
  stream.end(large.subarray(large.length >> 1));
});
// Frame header descriptor (byte 4): no content-size flag and no single-segment flag means the size is absent.
const sizeAbsent = largeStreamed[4] >> 6 === 0 && (largeStreamed[4] & 0x20) === 0;
const roundTrip = Buffer.compare(Bun.zstdDecompressSync(largeStreamed), large) === 0;

const results = {};
// compress_append
results["compress 1 KB"] = time(20000, () => Bun.zstdCompressSync(small, { level: 3 }));
results["compress 1 MB"] = time(40, () => Bun.zstdCompressSync(large, { level: 3 }));
// decompress_alloc, size in the header
results["decompress 1 KB"] = time(20000, () => Bun.zstdDecompressSync(smallFrame));
results["decompress 1 MB"] = time(100, () => Bun.zstdDecompressSync(largeFrame));
// decompress_alloc, streaming path (ZstdReaderArrayList)
results["decompress 1 MB, size unknown"] = time(100, () => Bun.zstdDecompressSync(largeStreamed));

// StreamingDecoder: fetch of a `Content-Encoding: zstd` body.
const server = Bun.serve({
  port: 0,
  fetch: () => new Response(largeFrame, { headers: { "Content-Encoding": "zstd" } }),
});
let fetched = 0;
results["fetch 1 MB zstd body"] = await timeAsync(40, async () => {
  fetched = (await (await fetch(server.url)).arrayBuffer()).byteLength;
});
server.stop(true);

console.log(JSON.stringify({ results, checks: { sizeAbsent, roundTrip, fetched, frame: largeFrame.length } }));
