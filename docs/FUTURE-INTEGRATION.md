# Future Integration: superinstance-ecosystem

## Current State
The fleet's architectural overview and documentation hub. Shows the full SuperInstance stack: lever-runner (Python) → Rust Carapace → tile-cuda/opencl/neon (GPU acceleration). Documents the ecosystem's structure and connections.

## Integration Opportunities

### With fleet catalog
superinstance-ecosystem IS the fleet catalog — the high-level map of how everything connects. When a new agent joins the fleet, it reads superinstance-ecosystem to understand the architecture. The catalog stays current as the fleet evolves.

### With oracle1-index
The ecosystem catalog provides the high-level structure; oracle1-index provides the detailed per-repo data. Together they give a complete picture: ecosystem catalog for architecture, oracle1-index for specifics.

### With room-as-codespace documentation
The ecosystem catalog becomes the room-as-codespace documentation. Every room is documented in the catalog: its purpose, its ensign, its skills, its hardware tier. The catalog IS the fleet's documentation.

## Potential in Mature Systems
superinstance-ecosystem is the fleet's README — the first document anyone reads to understand the architecture. It's maintained by Oracle1, updated with every fleet change, and always current.

## Cross-Pollination Ideas
- **oracle1-index**: Detailed data to supplement the catalog
- **oracle1-vessel**: Oracle1 maintains the catalog
- **capitaine-1**: Capitaine's fleet/ directory references the ecosystem

## Dependencies for Next Steps
- Auto-update from fleet activity (new repos, new crates)
- Room-specific sections in the catalog
- Integration with oracle1-index for real-time data
