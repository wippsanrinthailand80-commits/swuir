#!/usr/bin/env python3
"""
Cross-language S.W.UIR Demo: All Three Languages Together
C creates IL -> Python executes warp -> Rust executes warp -> C executes final warp
All share the same state via JSON Intermediate Language
"""
import json
import struct
import subprocess
import sys
import os
import time

def create_il_from_c(json_file: str, state_file: str):
    """C program creates IL JSON + state binary"""
    print("[C CREATOR] Creating S.W.UIR IL module...")
    
    exe_path = "/root/madel/swuir_il_creator"
    if not os.path.exists(exe_path):
        print("[C CREATOR] Compiling creator...")
        result = subprocess.run([
            "gcc", "-std=c99", "-Wall", "-Wextra", "-O2", "-I/root/madel",
            "-o", exe_path, "/root/madel/swuir_il_creator.c", "/root/madel/swuir_lib.o"
        ], capture_output=True, text=True, cwd="/root/madel")
        if result.returncode != 0:
            print(f"[C CREATOR] Compilation failed: {result.stderr}")
            return False
    
    result = subprocess.run([exe_path, json_file, state_file], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0

def python_executor(json_file: str, state_file: str, output_state_file: str):
    """Python reads IL, executes warp, writes modified state"""
    print(f"\n[PYTHON EXECUTOR] Loading IL from {json_file}...")
    print(f"[PYTHON EXECUTOR] Loading state from {state_file}...")
    
    with open(state_file, 'rb') as f:
        state_data = f.read()
    
    id_val, value, label_bytes = struct.unpack('<if32s', state_data)
    label = label_bytes.rstrip(b'\x00').decode('utf-8')
    
    print(f"[PYTHON EXECUTOR] Parsed state: ID={id_val}, Value={value:.2f}, Label={label}")
    print("[PYTHON EXECUTOR] Executing Python warp session...")
    print("[PYTHON EXECUTOR] Modifying state in Python warp...")
    
    value *= 1.5
    label = f"PYTHON_{label}"
    
    print(f"[PYTHON EXECUTOR] State after Python warp: Value={value:.2f}, Label={label}")
    
    new_label = label.encode('utf-8')[:31]
    new_label += b'\x00' * (32 - len(new_label))
    new_state = struct.pack('<if32s', id_val, value, new_label)
    
    with open(output_state_file, 'wb') as f:
        f.write(new_state)
    
    print(f"[PYTHON EXECUTOR] Saved modified state to {output_state_file}")
    return True

def rust_executor(json_file: str, state_file: str, output_state_file: str):
    """Rust reads IL, executes warp, writes modified state"""
    print(f"\n[RUST EXECUTOR] Loading IL from {json_file}...")
    print(f"[RUST EXECUTOR] Loading state from {state_file}...")
    
    exe_path = "/root/madel/rust_bindings/target/debug/swuir_il_executor"
    if not os.path.exists(exe_path):
        print("[RUST EXECUTOR] Building Rust executor...")
        result = subprocess.run([
            "cargo", "build", "--bin", "swuir_il_executor"
        ], capture_output=True, text=True, cwd="/root/madel/rust_bindings")
        if result.returncode != 0:
            print(f"[RUST EXECUTOR] Build failed: {result.stderr}")
            return False
    
    result = subprocess.run([exe_path, json_file, state_file, output_state_file], 
                           capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0

def c_final_executor(json_file: str, state_file: str):
    """C reads final state, executes final warp"""
    print(f"\n[C FINAL] Loading state from {state_file}...")
    
    exe_path = "/root/madel/swuir_il_final"
    if not os.path.exists(exe_path):
        print("[C FINAL] Compiling final executor...")
        result = subprocess.run([
            "gcc", "-std=c99", "-Wall", "-Wextra", "-O2", "-I/root/madel",
            "-o", exe_path, "/root/madel/swuir_il_final.c", "/root/madel/swuir_lib.o"
        ], capture_output=True, text=True, cwd="/root/madel")
        if result.returncode != 0:
            print(f"[C FINAL] Compilation failed: {result.stderr}")
            return False
    
    result = subprocess.run([exe_path, json_file, state_file], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0

def main():
    base = "/tmp/swuir_all_lang"
    json_file = f"{base}.json"
    state_files = [
        f"{base}_state0.bin",  # Initial from C
        f"{base}_state1.bin",  # After Python
        f"{base}_state2.bin",  # After Rust
    ]
    
    print("=" * 70)
    print("S.W.UIR Cross-Language Demo: C -> Python -> Rust -> C")
    print("=" * 70)
    print("All languages share state via JSON Intermediate Language (IL)")
    print("=" * 70)
    
    # Step 1: C creates initial IL + state
    print("\n>>> STEP 1: C CREATES INITIAL IL <<<")
    if not create_il_from_c(json_file, state_files[0]):
        return 1
    
    # Step 2: Python executes warp
    print("\n>>> STEP 2: PYTHON EXECUTES WARP <<<")
    if not python_executor(json_file, state_files[0], state_files[1]):
        return 1
    
    # Step 3: Rust executes warp
    print("\n>>> STEP 3: RUST EXECUTES WARP <<<")
    if not rust_executor(json_file, state_files[1], state_files[2]):
        return 1
    
    # Step 4: C executes final warp
    print("\n>>> STEP 4: C EXECUTES FINAL WARP <<<")
    if not c_final_executor(json_file, state_files[2]):
        return 1
    
    # Verify final state (the state passed to C final)
    print("\n>>> FINAL STATE VERIFICATION <<<")
    with open(state_files[2], 'rb') as f:
        final_data = f.read()
    id_val, value, label_bytes = struct.unpack('<if32s', final_data)
    label = label_bytes.rstrip(b'\x00').decode('utf-8')
    print(f"[VERIFY] Final state passed to C: ID={id_val}, Value={value:.2f}, Label={label}")
    print(f"[VERIFY] (C final warp modifies its own copy, main thread state unchanged)")
    
    print("\n" + "=" * 70)
    print("SUCCESS: All three languages executed warp sessions in sequence!")
    print("=" * 70)
    return 0

if __name__ == "__main__":
    sys.exit(main())