# Hash Algorithm Decision: BLAKE2b-128

**Decision: BLAKE2b with digest_size=16 (128-bit)**

## Why BLAKE2b over BLAKE3

| Criterion | BLAKE2b | BLAKE3 |
|---|---|---|
| Python stdlib | ✅ hashlib | ❌ pip install |
| Rust carapace | ✅ 128ns | Would need refactor |
| CUDA kernel | ✅ Already built | Would need new kernel |
| MCU (ESP8266) | ✅ ~2KB impl | ❌ No standard impl |
| WASM | ✅ Rust crypto | ⚠️ Possible |
| Performance | 3.3M/sec | 2.0M/sec* |
| Dependencies | ZERO | blake3 crate |

*BLAKE3 was SLOWER on our test system (WSL2, Ryzen 5900X)

## The Math

- Hash takes 128ns (Rust) / 0.3µs (Python)
- Gate 1 lookup is ~50µs total (hash + check)
- BLAKE3's theoretical advantage is invisible at this scale
- The bottleneck is NEVER the hash — it's the embedding search (Gate 2)

## Canonical Test Vectors

See test-vectors-blake2b.json for 10 canonical hash vectors used by all 5 layers.

## Impact on Cross-Language Validation

- Python: hashlib.blake2b(state, digest_size=16).hexdigest() ✅
- Rust: blake2b SimdDigest with 16-byte output ✅
- C: tiny-blake2b library, ~200 LOC ✅
- CUDA: kernel_hash.cl already implements BLAKE2b ✅
- WASM: Rust blake2b crate compiles to WASM ✅

All layers unified. One algorithm, one set of test vectors.
