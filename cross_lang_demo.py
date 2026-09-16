#!/usr/bin/env python3
"""
Cross-language S.W.UIR Demo - Pure JSON Interchange
Python generates IL JSON -> C reads JSON and executes warp session
No shared library loading required - uses JSON as the universal interchange format
"""
import json
import struct
import subprocess
import sys
import os
import time

def create_il_json_from_python(output_file: str):
    """Python creates IL module JSON directly (no C library needed)"""
    print("[Python] Creating S.W.UIR IL module (pure JSON)...")
    
    # Create demo state
    state_data = struct.pack('<if32s', 42, 3.14, b'INITIAL_STATE')
    session_id = int.from_bytes(os.urandom(8), 'little')
    
    # Build IL JSON structure
    il_module = {
        "version": 1,
        "magic": "0x53575549",
        "module": "cross_lang_demo",
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
        "sessions": [
            {
                "session_id": f"{session_id:016X}",
                "target": "dormant_block_target",
                "state_type": "DemoState",
                "state_size": 40,
                "status": 0
            }
        ],
        "pool_used": 0
    }
    
    # Save state data to a binary file for C to read
    state_file = output_file.replace('.json', '_state.bin')
    with open(state_file, 'wb') as f:
        f.write(state_data)
    
    # Save JSON
    json_str = json.dumps(il_module, indent=2)
    with open(output_file, 'w') as f:
        f.write(json_str)
    
    print(f"[Python] Saved IL JSON to {output_file}")
    print(f"[Python] Saved state binary to {state_file}")
    print(f"[Python] Session ID: {session_id:016X}")
    print(f"[Python] State data: {state_data.hex()}")
    return json_str, state_file

def run_c_warp_executor(json_file: str, state_file: str):
    """C program reads JSON + state binary and executes warp sessions"""
    print(f"\n[C] Loading IL JSON from {json_file}...")
    print(f"[C] Loading state binary from {state_file}...")
    
    # Compile the C executor if needed
    exe_path = "/root/madel/swuir_il_executor2"
    if not os.path.exists(exe_path):
        print("[C] Compiling executor...")
        result = subprocess.run([
            "gcc", "-std=c99", "-Wall", "-Wextra", "-O2",
            "-I/root/madel", "-o", exe_path,
            "/root/madel/swuir_il_executor2.c", "/root/madel/swuir.c"
        ], capture_output=True, text=True, cwd="/root/madel")
        if result.returncode != 0:
            print(f"[C] Compilation failed: {result.stderr}")
            return False
    
    # Run the executor
    print("[C] Executing warp sessions...")
    result = subprocess.run([exe_path, json_file, state_file], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    
    return result.returncode == 0

def main():
    json_file = "/tmp/swuir_cross_lang.json"
    state_file = "/tmp/swuir_cross_lang_state.bin"
    
    print("=" * 60)
    print("S.W.UIR Cross-Language Demo: Python -> JSON -> C")
    print("=" * 60)
    print("Using JSON as universal Intermediate Language (IL)")
    print("=" * 60)
    
    # Step 1: Python creates IL JSON + state binary
    create_il_json_from_python(json_file)
    
    # Step 2: C reads JSON + state and executes
    success = run_c_warp_executor(json_file, state_file)
    
    print("\n" + "=" * 60)
    if success:
        print("SUCCESS: Cross-language warp execution completed!")
    else:
        print("FAILED: Cross-language warp execution failed!")
    print("=" * 60)

if __name__ == "__main__":
    main()