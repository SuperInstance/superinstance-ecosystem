# Cross-Language Schemas — SuperInstance Metal Stack

Defines every interface boundary in the stack so that C, Rust, Python, WASM, CUDA, and JavaScript produce **bit-identical results** for the same inputs.

---

## 1. Wire Format: Tile Data (Binary, Language-Agnostic)

### 1.1 Layout

All multi-byte fields are **little-endian**. Total size is padded to 256-byte alignment.

```
Offset  Size    Field
──────  ──────  ────────────────────────────────────────
0       4       Magic: 0x54494C45 ("TILE" in ASCII)
4       2       Version (uint16), currently 1
6       2       Flags (uint16)
                bit 0: has_embeddings
                bit 1: has_metadata
                bit 2: compressed (zstd)
                bits 3–15: reserved (zero)
8       4       n_tiles (uint32)
12      4       n_actions (uint32)
16      4       dim (uint32) — embedding dimensionality
20      4       reserved (uint32, must be 0)
24      8       timestamp_ns (uint64, Unix epoch nanoseconds)
32      32      checksum — BLAKE2b-256 of everything after this field

── Per-tile entry (repeats n_tiles times) ──
64+     16      hash — BLAKE2b-128 (state identifier)
80+     4×n_a   scores — n_actions × float32 (Q-values, little-endian)
80+4na  4×n_a   visits — n_actions × uint32 (visit counts)
varies  4       metadata_len (uint32) — 0 unless flags bit 1
varies  ?       metadata blob (msgpack if present)
varies  pad     Zero-pad to 8-byte boundary within entry
── End per-tile ──

Total   pad     Zero-pad to next 256-byte boundary
```

### 1.2 Entry Size Formula

```
entry_size = 16 + (4 * n_actions) + (4 * n_actions) + 4 + metadata_len
           = 16 + 8*n_actions + 4 + metadata_len
           = 20 + 8*n_actions + metadata_len
```

Padded to 8-byte boundary:
```
entry_padded = ceil(entry_size / 8) * 8
```

### 1.3 Total Size

```
header_size    = 64
data_size      = n_tiles * entry_padded
total_unpadded = header_size + data_size
total          = ceil(total_unpadded / 256) * 256
```

### 1.4 Validation Checklist (All Languages)

1. Read magic → must equal `0x54494C45`
2. Read version → must be `≤ CURRENT_VERSION`
3. Verify BLAKE2b checksum over `[64..end]`
4. Verify `n_tiles * entry_padded + 64 == total_unpadded`
5. All reserved fields must be zero

### 1.5 Pseudocode (Portable)

```c
// C / Rust / CUDA kernel host code
struct tile_header {
    uint32_t magic;       // 0x54494C45
    uint16_t version;
    uint16_t flags;
    uint32_t n_tiles;
    uint32_t n_actions;
    uint32_t dim;
    uint32_t reserved;
    uint64_t timestamp_ns;
    uint8_t  checksum[32];
};
_Static_assert(sizeof(struct tile_header) == 64, "header must be 64 bytes");

struct tile_entry {
    uint8_t  hash[16];
    float    scores[];    // n_actions floats, flexible array
    uint32_t visits[];    // n_actions uints, follows scores
    // then metadata_len (uint32) + metadata blob if flagged
};
```

```python
# Python
import struct, hashlib
MAGIC = 0x54494C45
HEADER_FMT = '<IHHIIIIQ32s'  # 64 bytes

def parse_header(buf: bytes):
    return struct.unpack_from(HEADER_FMT, buf, 0)
```

```javascript
// JavaScript / WASM interop
const MAGIC = 0x54494C45;
function parseHeader(dv /* DataView */) {
    return {
        magic:       dv.getUint32(0, true),
        version:     dv.getUint16(4, true),
        flags:       dv.getUint16(6, true),
        n_tiles:     dv.getUint32(8, true),
        n_actions:   dv.getUint32(12, true),
        dim:         dv.getUint32(16, true),
        timestamp_ns: dv.getBigUint64(24, true),
    };
}
```

---

## 2. IPC Protocol: Fastloop-Guard UDS Daemon

Unix Domain Socket at `$FASTLOOP_SOCK` (default `/tmp/superinstance/fastloop.sock`).

### 2.1 Framing

Each message is length-prefixed:

```
[4 bytes: body length as uint32 LE] [body bytes (UTF-8 JSON)]
```

Max body size: 64 KiB. Requests exceeding this are rejected with an error response.

### 2.2 Request Schema

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["op", "id"],
    "properties": {
        "op": {
            "type": "string",
            "enum": ["lookup", "store", "stats", "ping", "shutdown"]
        },
        "id": {
            "type": "string",
            "description": "UUID v4 for request-response correlation"
        },
        "query": {
            "type": "string",
            "description": "Required for 'lookup' and 'store'. BLAKE3 hex of the state hash."
        },
        "response": {
            "type": "string",
            "description": "Required for 'store'. The raw response text to cache."
        },
        "scores": {
            "type": "array",
            "items": {"type": "number"},
            "description": "Required for 'store'. Q-values to persist."
        },
        "visits": {
            "type": "array",
            "items": {"type": "integer", "minimum": 0},
            "description": "Required for 'store'. Visit counts."
        },
        "threshold": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "default": 0.95,
            "description": "Similarity threshold for 'lookup'."
        },
        "top_k": {
            "type": "integer",
            "minimum": 1,
            "maximum": 100,
            "default": 1
        }
    }
}
```

### 2.3 Response Schema

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["id", "ok"],
    "properties": {
        "id": {
            "type": "string",
            "description": "Echo of request id"
        },
        "ok": {
            "type": "boolean",
            "description": "false if any error occurred"
        },
        "hit": {
            "type": "boolean",
            "description": "Present for 'lookup'. Whether a match was found."
        },
        "gate": {
            "type": "integer",
            "enum": [1, 2, 3],
            "description": "Which gate matched: 1=exact, 2=fuzzy, 3=semantic"
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Match confidence"
        },
        "latency_us": {
            "type": "integer",
            "minimum": 0,
            "description": "Server-side processing time in microseconds"
        },
        "command": {
            "type": "string",
            "description": "Cached response text for hits"
        },
        "scores": {
            "type": "array",
            "items": {"type": "number"}
        },
        "visits": {
            "type": "array",
            "items": {"type": "integer"}
        },
        "stats": {
            "type": "object",
            "description": "Present for 'stats'",
            "properties": {
                "tiles_stored": {"type": "integer"},
                "total_lookups": {"type": "integer"},
                "hit_rate": {"type": "number"},
                "avg_latency_us": {"type": "number"},
                "memory_bytes": {"type": "integer"}
            }
        },
        "error": {
            "type": "string",
            "description": "Present when ok=false"
        }
    }
}
```

### 2.4 Example Exchange

```
→ [0x7B length] {"op":"lookup","id":"a1b2c3","query":"a4f2...e8","threshold":0.95}
← [0x45 length] {"id":"a1b2c3","ok":true,"hit":true,"gate":1,"confidence":0.99,"latency_us":42,"command":"move_north"}
```

### 2.5 Timeout

Default: 50 ms. Client MUST treat timeout as cache miss (proceed to full pipeline).

---

## 3. WASM API

Exported functions from the SuperInstance WASM module.

### 3.1 Exported Functions

| Function | Signature | Description |
|---|---|---|
| `hash_intent` | `(ptr: *u8, len: u32) → *u8` | Takes UTF-8 string, returns pointer to 32-char hex BLAKE2b-128 hash (null-terminated) |
| `embed_intent` | `(ptr: *u8, len: u32, out_ptr: *u8) → u32` | Takes UTF-8 string, writes Float64Array to `out_ptr`, returns length |
| `gate_pipeline` | `(state_ptr: *u8, state_len: u32, actions_ptr: *u8, actions_len: u32) → u32` | Runs full gate pipeline. Returns pointer to a result struct |

### 3.2 Memory Management

- WASM module exports `alloc(size: u32) → *u8` and `free(ptr: *u8)`
- All returned pointers are valid until next call or explicit `free`
- Linear memory is shared; host must not write to returned buffers

### 3.3 Gate Pipeline Result Struct (WASM Memory)

```
Offset  Size  Field
0       1     gate (u8): 0=miss, 1=exact, 2=fuzzy, 3=semantic
1       1     padding
2       4     confidence (float32 LE)
6       4     latency_us (uint32 LE)
10      4     command_len (uint32 LE)
14      ?     command (UTF-8 string, null-terminated)
```

### 3.4 JavaScript Binding

```javascript
class SuperInstanceWASM {
    constructor(wasmBuffer) {
        this.exports = instantiate(wasmBuffer);
    }

    hashIntent(text) {
        const ptr = this._allocAndWrite(text);
        const resultPtr = this.exports.hash_intent(ptr, text.length);
        const hash = this._readString(resultPtr);
        this.exports.free(ptr);
        this.exports.free(resultPtr);
        return hash;
    }

    embedIntent(text) {
        const ptr = this._allocAndWrite(text);
        const outPtr = this.exports.alloc(text.length * 8);
        const len = this.exports.embed_intent(ptr, text.length, outPtr);
        const result = new Float64Array(this.exports.memory.buffer, outPtr, len);
        const copy = new Float64Array(result); // copy out before free
        this.exports.free(ptr);
        this.exports.free(outPtr);
        return copy;
    }

    async gatePipeline(state, actionsJSON) {
        const sPtr = this._allocAndWrite(state);
        const aPtr = this._allocAndWrite(actionsJSON);
        const rPtr = this.exports.gate_pipeline(sPtr, state.length, aPtr, actionsJSON.length);
        const dv = new DataView(this.exports.memory.buffer, rPtr);
        const gate = dv.getUint8(0);
        const confidence = dv.getFloat32(2, true);
        const latency_us = dv.getUint32(6, true);
        const cmdLen = dv.getUint32(10, true);
        const command = new TextDecoder().decode(
            new Uint8Array(this.exports.memory.buffer, rPtr + 14, cmdLen)
        );
        this.exports.free(sPtr);
        this.exports.free(aPtr);
        this.exports.free(rPtr);
        return { gate, command, confidence, latency_us };
    }
}
```

---

## 4. CUDA Kernel Interface

### 4.1 Kernel Launch Parameters

```c
// Host-side launch configuration
struct tile_launch_config {
    dim3 grid;          // gridDim = ceil(n_tiles / BLOCK_SIZE)
    dim3 block;         // blockDim = {BLOCK_SIZE, 1, 1}, typically 256 or 512
    size_t shared_mem;  // shared memory per block in bytes
    cudaStream_t stream;
};
```

### 4.2 Kernel Signature

```c
__global__ void tile_query_kernel(
    // Input
    const uint8_t*  __restrict__ query_hashes,   // [n_queries, 16]
    uint32_t                        n_queries,
    const uint8_t*  __restrict__ tile_hashes,    // [n_tiles, 16]
    const float*    __restrict__ tile_scores,    // [n_tiles, n_actions]
    const uint32_t* __restrict__ tile_visits,    // [n_tiles, n_actions]
    uint32_t                        n_tiles,
    uint32_t                        n_actions,
    float                           threshold,
    // Output
    int32_t*        __restrict__ out_match_idx,  // [n_queries] -1 = no match
    float*          __restrict__ out_confidence, // [n_queries]
    uint8_t*        __restrict__ out_gate,       // [n_queries] 0=miss,1=exact,2=fuzzy
    // Workspace
    float*          __restrict__ scratch         // [n_queries * n_tiles] min 4 bytes each
);
```

### 4.3 Launch Wrapper

```c
tile_launch_config tile_default_launch_config(uint32_t n_queries, uint32_t n_tiles) {
    const int BLOCK_SIZE = 256;
    return (tile_launch_config){
        .grid       = dim3((n_queries + BLOCK_SIZE - 1) / BLOCK_SIZE),
        .block      = dim3(BLOCK_SIZE),
        .shared_mem = 16 * n_tiles, // tile hashes in shared mem if they fit
        .stream     = 0             // default stream
    };
}

cudaError_t tile_query_launch(
    const tile_launch_config* config,
    /* ... same params as kernel ... */
) {
    tile_query_kernel<<<config->grid, config->block, config->shared_mem, config->stream>>>(
        query_hashes, n_queries, tile_hashes, tile_scores, tile_visits,
        n_tiles, n_actions, threshold,
        out_match_idx, out_confidence, out_gate, scratch
    );
    return cudaGetLastError();
}
```

### 4.4 Synchronization & Error Reporting

```
After launch:
  1. Check cudaGetLastError() immediately → launch-time errors
  2. Check cudaStreamSynchronize(stream) → runtime errors
  3. Inspect out_match_idx[i]: -1 means no match found (not an error)

Error propagation:
  - Kernel sets out_gate[i] = 255 on internal error
  - Host polls: if any out_gate[i] == 255, log and fall back to CPU
  - CUDA errors are converted to a unified error enum (see §6)
```

### 4.5 Shared Memory Strategy

- If `n_tiles * 16 <= shared_mem_available`: load all tile hashes into shared memory
- Otherwise: each block loads a tile batch, iterates through tile chunks
- Query hashes always in registers or shared memory (small per-thread)

---

## 5. Cross-Language Test Vectors

These 10 (state, action, score) triples MUST produce bit-identical results across all implementations.

### 5.1 BLAKE2b-128 Test Vectors

Each state is hashed to BLAKE2b with `digest_size=16` (128-bit, hex). Implementations MUST produce these exact hashes:

```
Vector  State Input                          Expected Hash (128-bit BLAKE2b hex)
─────── ──────────────────────────────────── ────────────────────────────────────────
v0      ""                                 → cae66941 d9efbd40 4e4d8875 8ea67670
v1      "hello"                            → 46fb7408 d4f28522 8f4af516 ea25851b
v2      "action:north"                     → 75d42cb7 5f1d04b6 cdee14b8 065041d0
v3      "state:grid[3,7];prev:east"        → 6aa1971b a80e2d9f bacb22c2 315fe9f7
v4      "state:grid[0,0];prev:null"        → 5b5b877e d4633615 3f8580dd 503f266a
v5      "embed:test_positive"              → d88a6abc e3406aca 046bd863 bc5ad34e
v6      "embed:test_negative"              → 690fa5ad ed3d16d3 815e0dae 479346bc
v7      "gate:exact_match"                 → 2f0926c1 9e383666 1b91ea93 e57ca4ea
v8      "gate:fuzzy_match"                 → 71cb317c 174bd4d1 1909f632 6cd71183
v9      "gate:semantic_miss"               → 81127796 7e7e8064 f8dedf55 39c14ae5
```

> **Note:** These are canonical BLAKE2b-128 hashes generated by `hashlib.blake2b(state, digest_size=16)` in Python. All implementations must produce identical results. In Rust: `blake2b_simd::Params::new().hash_length(16).hash(state)`. In C: `blake2b(state, state_len, hash, 16)`. In JS: `crypto.createHash('blake2b512').update(state).digest('hex').slice(0, 32)`.

### 5.2 Scoring Test Vectors

For each vector, given a fixed set of 4 actions `[north, east, south, west]`, the scoring function must produce:

```
Vector  Scores (float32 LE hex)                              Best Action
─────── ──────────────────────────────────────────────────── ────────────
v0      [0000803f, 00000000, 00000000, 00000000]             north (0.5)
v1      [cdcc4c3e, 0000803f, 9a99993e, 00000000]             east  (1.0)
v2      [0000803f, 0000803f, 0000803f, 0000803f]             tie (all 0.5)
v3      [0000403f, db0f4940, 00000000, 6666663f]             east  (3.14)
v4      [00000000, 00000000, 00000000, 00000000]             tie (all 0.0)
v5      [0100803f, 010080bf, 00000000, 0100003f]             north (1.0001)
v6      [00000000, 00000000, 00000000, 0000803f]             west  (1.0)
v7      [9a999941, 0000803f, 00000000, 00000000]             north (9.8)
v8      [cdcccc3d, cdcccc3d, 0000803f, cdcccc3d]             south (1.0)
v9      [00000000, 00000000, 00000000, 00000000]             tie (all 0.0)
```

Where float32 values are IEEE 754 little-endian. Verification:
- `0x3F800000` = 1.0f
- `0x3F000000` = 0.5f
- `0x3E4CCCCD` = 0.2f
- `0x3DCCCCCD` = 0.1f
- `0x40490FDB` ≈ 3.14159f
- `0x4199999A` ≈ 9.8f
- `0x3F800001` ≈ 1.0001f (ulp test)
- `0xBF800001` ≈ -1.0001f (negative ulp test)
- `0x3F000001` ≈ 0.50000006f (ulp test)

### 5.3 Wire Format Round-Trip Test

For test vector `v2` with `n_tiles=1, n_actions=4`:

```
Expected binary header (hex, first 64 bytes):
54 49 4C 45   -- magic "TILE"
01 00         -- version 1
00 00         -- flags 0
01 00 00 00   -- n_tiles = 1
04 00 00 00   -- n_actions = 4
00 00 00 00   -- dim = 0 (no embeddings)
00 00 00 00   -- reserved
XX XX XX XX XX XX XX XX   -- timestamp_ns (varies)
XX XX XX XX XX XX XX XX
XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX  -- checksum (32B)

Entry (after header):
75 d4 2c b7 5f 1d 04 b6 cd ee 14 b8 06 50 41 d0  -- hash
00 00 80 3f 00 00 80 3f 00 00 80 3f 00 00 80 3f  -- scores [0.5, 0.5, 0.5, 0.5]
04 00 00 00 04 00 00 00 04 00 00 00 04 00 00 00  -- visits [4, 4, 4, 4]
00 00 00 00  -- metadata_len = 0
00 00 00 00  -- padding to 8-byte boundary

Total entry size = 16 + 16 + 16 + 4 + 4 = 56 bytes (already 8-aligned)
Total file = 64 + 56 = 120 bytes → padded to 256
```

### 5.4 Gate Pipeline Test Vectors

```
Vector  Input State                  Threshold  Expected Gate  Expected Confidence
─────── ──────────────────────────── ────────── ───────────── ───────────────────
v7      "gate:exact_match"           0.95       1 (exact)     1.0
v8      "gate:fuzzy_match"           0.80       2 (fuzzy)     0.85
v8      "gate:fuzzy_match"           0.95       0 (miss)      0.0
v9      "gate:semantic_miss"         0.60       3 (semantic)  0.65
v9      "gate:semantic_miss"         0.95       0 (miss)      0.0
v0      ""                           0.95       0 (miss)      0.0
```

### 5.5 Conformance Test Harness

Every implementation MUST include a test binary that:

1. Reads test vectors from `test-vectors.json` (same format across all languages)
2. For each vector:
   a. Hashes the state input → compare to expected hash
   b. Encodes scores as float32 LE → compare byte-for-byte
   c. Builds a wire-format tile entry → parse it back → compare
   d. Runs gate pipeline → compare gate + confidence (within ±1 ULP for floats)
3. Exits 0 on success, 1 on first mismatch with diagnostic output

Test vector file: `test-vectors.json`
```json
{
    "version": 1,
    "vectors": [
        {
            "id": "v0",
            "state": "",
            "scores": [0.5, 0.0, 0.0, 0.0],
            "visits": [1, 0, 0, 0],
            "actions": ["north", "east", "south", "west"],
            "expected_hash_hex": "affc3a150bd25f57d5e1b042a5e3c798"
        }
    ]
}
```

---

## 6. Unified Error Codes

All layers use the same error space:

```
Code    Constant                        Layer(s)      Meaning
────    ─────────────────────────────── ──────────    ──────────────────────────
0       OK                              all           Success
1       ERR_INVALID_MAGIC               wire          Bad magic bytes
2       ERR_VERSION_TOO_NEW             wire          Unsupported version
3       ERR_CHECKSUM_MISMATCH           wire          BLAKE2b verification failed
4       ERR_ALIGNMENT                   wire          Buffer not 256-byte aligned
5       ERR_TRUNCATED                   wire          Buffer too short for header
6       ERR_INVALID_OP                  ipc           Unknown operation
7       ERR_MISSING_FIELD               ipc           Required field absent
8       ERR_THRESHOLD_RANGE             ipc           Threshold not in [0,1]
9       ERR_LOOKUP_FAILED               ipc           Internal lookup error
10      ERR_STORE_FAILED                ipc           Internal store error
11      ERR_WASM_ALLOC                  wasm          Linear memory exhausted
12      ERR_WASM_INVALID_UTF8           wasm          Input not valid UTF-8
13      ERR_CUDA_LAUNCH                 cuda          Kernel launch failed
14      ERR_CUDA_SYNC                   cuda          Device synchronization failed
15      ERR_CUDA_INTERNAL               cuda          Kernel set gate=255
16      ERR_NOT_FOUND                   all           Tile not found (not an error per se)
255     ERR_UNKNOWN                     all           Catch-all
```

---

## 7. Encoding & Floating-Point Rules

1. **Endianness**: All multi-byte values are **little-endian** (network order is NOT used).
2. **Float precision**: Scores are IEEE 754 `binary32` (float32). No extended precision in intermediate calculations for cross-language test vectors.
3. **Hash algorithm**: BLAKE2b with `digest_size=16` (128-bit) for state hashes, `digest_size=32` (256-bit) for checksums.
4. **String encoding**: All strings are UTF-8. No BOM. No null terminators in JSON fields (null terminators only in C-style WASM buffers).
5. **Integer overflow**: `uint32` wrapping is undefined — implementations MUST reject values that would overflow.
6. **Padding bytes**: MUST be zero. Readers SHOULD verify but MAY tolerate non-zero padding.

---

## 8. Versioning Strategy

- **Wire format**: `version` field in header. Readers MUST reject unknown versions. Current: `1`.
- **IPC protocol**: No version field (JSON is self-describing). New fields are additive. Breaking changes use a new socket path.
- **WASM API**: Versioned via WASI feature detection. New functions are added, old signatures are stable.
- **CUDA kernel**: Versioned via `tile_launch_config` struct size. Host passes `struct_size` as first arg (extensible struct pattern).
- **Test vectors**: `version` field in `test-vectors.json`. Readers reject unknown versions.

---

## Changelog

| Date       | Author        | Change                          |
|------------|---------------|---------------------------------|
| 2026-06-04 | SuperInstance  | Migrated from BLAKE3 to BLAKE2b-128 (stdlib, MCU, CUDA support) |
| 2026-06-03 | SuperInstance  | Initial cross-language schemas  |
