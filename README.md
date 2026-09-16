# S.W.UIR — Stateful Warp Universal IR

[![Build](https://img.shields.io/badge/build-passing-brightgreen)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()
[![Language](https://img.shields.io/badge/C99%20%7C%20Python%20%7C%20Rust-orange)]()

**S.W.UIR** (Stateful Warp Universal Intermediate Representation) is a cross-language runtime architecture inspired by adaptive vehicle suspension physics. It enables dual-path execution where a "warp" splits execution: the main thread continues seamlessly while a new warp session executes a dormant code block with inherited state.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    S.W.UIR Runtime                               │
├─────────────────────────────────────────────────────────────────┤
│  Compression (Pin)    │    Dual-Path Execution                  │
│  ─────────────────────┼───────────────────────────────────────── │
│  • Snapshot memory    │    • Main thread → N+1 (continues)      │
│  • Pin to pool        │    • Warp session → dormant block       │
│  • Zero-copy clone    │    • Both share pinned state            │
└────────────────────────┴─────────────────────────────────────────┘
         │                              │
         ▼                              ▼
    ┌─────────┐                    ┌─────────┐
    │  Main   │                    │  Warp   │
    │ Thread  │                    │ Session │
    └─────────┘                    └─────────┘
```

## Core Components

| Component | Language | Purpose |
|-----------|----------|---------|
| **swuir.c/h** | C99 | Core warp engine, memory pool, pinned state |
| **swuir_il.c/h** | C99 | Intermediate Language (JSON) serialization |
| **swuir_vm.c/h** | C99 | Stack-based bytecode VM |
| **python_vm.py** | Python 3 | Pure Python bytecode VM + builder |
| **rust_vm/** | Rust | Safe Rust bytecode VM with serde |
| **python_bindings/** | Python | ctypes FFI to libswuir_il.so |
| **rust_bindings/** | Rust | FFI bindings via libc |

## Cross-Language Execution Matrix

All 9 combinations verified working:

```
┌──────────────┬──────────┬──────────┬──────────┐
│ SOURCE →     │ C VM     │ Python VM│ Rust VM  │
├──────────────┼──────────┼──────────┼──────────┤
│ C            │ ✓ 3.14   │ ✓ 3.14   │ ✓ 3.14   │
│ Python       │ ✓ 3.14   │ ✓ 3.14   │ ✓ 3.14   │
│ Rust         │ ✓ 3.14   │ ✓ 3.14   │ ✓ 3.14   │
└──────────────┴──────────┴──────────┴──────────┘
```

**Value transformations by target:**
- **C target**: True dual-path (`swuir_warp_split`) — warp modifies copy, main unchanged
- **Python target**: Value ×1.5, prefix `PY_FROM_<SRC>_`
- **Rust target**: Value ×2.0, prefix `RUST_`

## Quick Start

### Prerequisites
- **C**: gcc/clang (C99), make, libjansson-dev
- **Python**: 3.8+
- **Rust**: 1.70+ (stable)

### Build & Run
```bash
# Clone and build
git clone https://github.com/wippsanrinthailand80-commits/swuir.git
cd swuir
make                          # Builds C core + executables
cargo build --release         # Builds Rust VM (in rust_vm/)

# Run demos
./swuir_poc                    # Original C warp PoC
python3 python_vm.py           # Python VM (factorial, fibonacci)
cargo run --manifest-path rust_vm/Cargo.toml  # Rust VM

# Cross-language bytecode execution (9-way matrix)
python3 cross_lang_bytecode_demo.py

# Session-based chain (3 sessions per transition)
python3 test_9way_sessions.py
```

### Expected Output
```
=== C PoC ===
[MAIN] Initial state: ID=42, Value=3.14, Label=INITIAL_STATE
[MAIN] Calling swuir_warp_split()...
[MAIN] Main thread continues to next line (N+1)...
[WARP SESSION] Executing dormant block with inherited state: Value=3.14
[WARP SESSION] After modification: Value=6.28, Label=WARPED_INITIAL_STATE
[MAIN] Main thread state unchanged: Value=3.14
```

## File Structure

```
swuir/
├── Core C99
│   ├── swuir.c/h          # Warp engine, memory pool, pinned state
│   ├── swuir_il.c/h       # IL JSON serialization
│   ├── swuir_vm.c/h       # C bytecode VM
│   └── swuir_lib.o        # Compiled library
│
├── Python VM
│   ├── python_vm.py       # Python bytecode VM + builder
│   └── python_bindings/   # ctypes FFI to libswuir_il.so
│
├── Rust VM
│   ├── Cargo.toml
│   └── src/
│       ├── main.rs        # Rust bytecode VM
│       └── bin/rust_vm_json.rs  # JSON runner
│
├── Bindings
│   ├── python_bindings/
│   └── rust_bindings/
│
├── Demos
│   ├── cross_lang_bytecode_demo.py   # 9-way bytecode matrix
│   ├── cross_lang_all.py             # C→Py→Rust→C chain
│   ├── test_9way.py                  # 9-way state transitions
│   ├── test_9way_sessions.py         # 3-session chains
│   └── run_all_tests.py              # Full test suite
│
└── Build
    ├── Makefile
    └── build/                     # Generated executables
```

## Intermediate Language (IL) Format

```json
{
  "version": 1,
  "magic": "0x53575549",
  "module": "cross_lang_demo",
  "bytecode": "10050000005300000000...",
  "size": 75,
  "entry_point": 0,
  "types": [
    {
      "name": "DemoState",
      "size": 40,
      "fields": [
        {"name": "id", "type": "i32", "offset": 0, "array_len": 0},
        {"name": "value", "type": "f32", "offset": 4, "array_len": 0},
        {"name": "label", "type": "string", "offset": 8, "array_len": 32}
      ]
    }
  ],
  "sessions": [...],
  "pool_used": 0
}
```

## VM Bytecode Instructions

| Category | Opcodes |
|----------|---------|
| Stack | `PUSH_I32/I64/F32/F64`, `POP`, `DUP`, `SWAP` |
| Arithmetic | `ADD`, `SUB`, `MUL`, `DIV`, `MOD`, `NEG` |
| Comparison | `EQ`, `NE`, `LT`, `LE`, `GT`, `GE` |
| Logic | `AND`, `OR`, `NOT` |
| Control | `JMP`, `JMP_IF`, `JMP_IF_NOT`, `CALL`, `RET` |
| Memory | `LOAD`, `STORE`, `LOAD_GLOBAL`, `STORE_GLOBAL` |
| I/O | `PRINT`, `PRINTLN` |
| Warp | `WARP`, `JOIN` |
| End | `HALT` |

## Running Tests

```bash
# Full test suite (all demos)
python3 run_all_tests.py

# Individual tests
python3 test_9way.py           # 9-way state matrix
python3 test_9way_sessions.py  # 3-session chains
python3 cross_lang_bytecode_demo.py  # Bytecode VM matrix
python3 cross_lang_all.py       # C→Py→Rust→C chain
./swuir_poc                     # Original C warp PoC
```

## Design Philosophy

**Shock Absorber Metaphor:**
- **Compression** = `swuir_pin_state()` captures and pins memory state
- **Dual-Path** = `swuir_warp_split()` splits execution like a suspension splitting force
- **Rebound** = Warp session executes dormant code with inherited state, main continues

## License

MIT License — see [LICENSE](LICENSE) for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Ensure all tests pass: `python3 run_all_tests.py`
3. Submit a pull request

---

*S.W.UIR — Where state flows like suspension, and execution splits like a warp drive.*