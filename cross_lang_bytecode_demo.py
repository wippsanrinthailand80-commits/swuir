#!/usr/bin/env python3
"""
S.W.UIR Cross-Language Bytecode Execution Demo (Simplified)

Demonstrates bytecode exchange between C, Python, and Rust VMs.
"""
import json
import subprocess
import sys
import os
import tempfile

sys.path.insert(0, '/root/madel')
from python_vm import VMContext, BytecodeBuilder, VMOpcode, serialize_bytecode, deserialize_bytecode

def build_factorial_bytecode() -> bytes:
    b = BytecodeBuilder()
    b.push_i32(5); b.store_global(0)
    b.push_i32(1); b.store_global(1)
    loop_start = len(b.code)
    b.load_global(0); b.push_i32(1); b.emit(VMOpcode.SUB); b.store_global(0)
    b.load_global(1); b.load_global(0); b.emit(VMOpcode.MUL); b.store_global(1)
    b.load_global(0); b.push_i32(1); b.emit(VMOpcode.GT)
    b.jmp_if(loop_start)
    b.load_global(1); b.println(); b.halt()
    return b.build()

def build_fibonacci_bytecode() -> bytes:
    b = BytecodeBuilder()
    b.push_i32(10); b.store_global(0)
    b.push_i32(0); b.store_global(1)
    b.push_i32(1); b.store_global(2)
    loop_start = len(b.code)
    b.load_global(0); b.push_i32(1); b.emit(VMOpcode.SUB); b.store_global(0)
    b.load_global(1); b.load_global(2); b.emit(VMOpcode.ADD)
    b.load_global(2); b.store_global(1)
    b.store_global(2)
    b.load_global(0); b.push_i32(0); b.emit(VMOpcode.GT)
    b.jmp_if(loop_start)
    b.load_global(2); b.println(); b.halt()
    return b.build()

def write_il_json(bytecode: bytes, module_name: str) -> str:
    il = {
        "version": 1, "magic": "0x53575549", "module": module_name,
        "bytecode": bytecode.hex(), "size": len(bytecode), "entry_point": 0
    }
    return json.dumps(il, indent=2)

def run_c_vm(json_file: str) -> bool:
    exe = "/root/madel/test_c_vm"
    if not os.path.exists(exe):
        print("[C VM] Compiling...")
        code = '''
#include "swuir_vm.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <jansson.h>

int main(int argc, char** argv) {
    if (argc < 2) return 1;
    FILE* f = fopen(argv[1], "r"); if (!f) return 1;
    fseek(f, 0, SEEK_END); long sz = ftell(f); fseek(f, 0, SEEK_SET);
    char* json = malloc(sz + 1); fread(json, 1, sz, f); json[sz] = 0; fclose(f);
    json_error_t err; json_t* root = json_loads(json, 0, &err); free(json);
    if (!root) return 1;
    json_t* bc = json_object_get(root, "bytecode"); json_t* sz = json_object_get(root, "bytecode_size");
    if (!bc || !sz) { json_decref(root); return 1; }
    const char* hex = json_string_value(bc); size_t size = json_integer_value(sz);
    size_t bin = strlen(hex) / 2; uint8_t* code = malloc(bin);
    for (size_t i = 0; i < bin; i++) sscanf(hex + i*2, "%2hhx", &code[i]);
    VMContext* vm = vm_create(code, bin); int r = vm_execute(vm);
    printf("\\n[C VM] %s\\n", r ? "executed successfully" : "error"); if (!r) printf("Error: %s\\n", vm->error_msg);
    vm_destroy(vm); free(code); json_decref(root); return r ? 0 : 1;
}
'''
        with open("/tmp/test_c_vm.c", "w") as f: f.write(code)
        r = subprocess.run(["gcc", "-std=c99", "-Wall", "-Wextra", "-O2", "-I/root/madel",
                           "-o", exe, "/tmp/test_c_vm.c", "/root/madel/swuir_vm.o", "-ljansson"], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"[C VM] Compile failed: {r.stderr}"); return False
    
    r = subprocess.run([exe, json_file], capture_output=True, text=True)
    print(r.stdout); 
    if r.stderr: print(r.stderr, file=sys.stderr)
    return r.returncode == 0

def run_python_vm(json_file: str) -> bool:
    with open(json_file) as f: data = json.load(f)
    bytecode = bytes.fromhex(data["bytecode"])
    print(f"[Python VM] Loaded {len(bytecode)} bytes")
    vm = VMContext(bytecode)
    if vm.execute(): print("[Python VM] Executed successfully"); return True
    else: print(f"[Python VM] Error: {vm.error}"); return False

def run_rust_vm(json_file: str) -> bool:
    # Use pre-built rust_vm binary with JSON input
    exe = "/root/madel/rust_vm/target/debug/rust_vm_json"
    if not os.path.exists(exe):
        print("[Rust VM] Building JSON runner...")
        runner = '''
use std::fs;
use rust_vm::{VMContext, deserialize_bytecode};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 { return Err("Usage: <json_file>".into()); }
    let json = fs::read_to_string(&args[1])?;
    let bytecode = deserialize_bytecode(&json)?;
    println!("[Rust VM] Loaded {} bytes", bytecode.len());
    let mut vm = VMContext::new(bytecode);
    match vm.execute() { Ok(_) => println!("[Rust VM] Executed successfully"), Err(e) => { println!("[Rust VM] Error: {}", e); return Err(e.into()); } }
    Ok(())
}
'''
        os.makedirs("/root/madel/rust_vm/src/bin", exist_ok=True)
        with open("/root/madel/rust_vm/src/bin/rust_vm_json.rs", "w") as f: f.write(runner)
        r = subprocess.run(["cargo", "build", "--bin", "rust_vm_json"], cwd="/root/madel/rust_vm", capture_output=True, text=True)
        if r.returncode != 0:
            print(f"[Rust VM] Build failed: {r.stderr}"); return False
    
    r = subprocess.run([exe, json_file], capture_output=True, text=True)
    print(r.stdout); 
    if r.stderr: print(r.stderr, file=sys.stderr)
    return r.returncode == 0

def main():
    print("=" * 70)
    print("S.W.UIR Cross-Language Bytecode Execution Demo")
    print("=" * 70)
    
    # Build bytecode
    fact_bc = build_factorial_bytecode()
    fib_bc = build_fibonacci_bytecode()
    
    # Test matrix
    tests = [
        ("Python->C", build_factorial_bytecode(), run_c_vm),
        ("Python->Python", build_factorial_bytecode(), run_python_vm),
        ("Python->Rust", build_factorial_bytecode(), run_rust_vm),
        ("Rust->Python", build_fibonacci_bytecode(), run_python_vm),
        ("Rust->C", build_fibonacci_bytecode(), run_c_vm),
        ("Rust->Rust", build_fibonacci_bytecode(), run_rust_vm),
        ("C->Python", bytes.fromhex("1005000000530000000010010000005301000000520000000010010000002153000000005201000000520000000022530100000052000000001001000000344114000000520100000061ff"), run_python_vm),
        ("C->Rust", bytes.fromhex("1005000000530000000010010000005301000000520000000010010000002153000000005201000000520000000022530100000052000000001001000000344114000000520100000061ff"), run_rust_vm),
        ("C->C", bytes.fromhex("1005000000530000000010010000005301000000520000000010010000002153000000005201000000520000000022530100000052000000001001000000344114000000520100000061ff"), run_c_vm),
    ]
    
    print("=" * 70)
    print("S.W.UIR Cross-Language Bytecode Execution Matrix")
    print("=" * 70)
    
    results = {}
    for name, bytecode, runner in tests:
        print(f"\n>>> {name} <<<")
        il = write_il_json(bytecode, name.replace("->", "_"))
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(il); jf = f.name
        try:
            ok = runner(jf)
            results[name] = ok
            print(f"Result: {'PASS' if ok else 'FAIL'}")
        except Exception as e:
            print(f"Error: {e}")
            results[name] = False
        finally:
            os.unlink(jf)
    
    print("\n" + "=" * 70)
    print("CROSS-LANGUAGE BYTECODE EXECUTION RESULTS")
    print("=" * 70)
    for name, ok in results.items():
        print(f"  {name:15} : {'PASS' if ok else 'FAIL'}")
    print(f"\nPassed: {sum(results.values())}/{len(results)}")
    print("=" * 70)

def run_python_vm(json_file: str) -> bool:
    with open(json_file) as f: data = json.load(f)
    bytecode = bytes.fromhex(data["bytecode"])
    print(f"[Python VM] Loaded {len(bytecode)} bytes")
    vm = VMContext(bytecode)
    if vm.execute(): print("[Python VM] Executed successfully"); return True
    else: print(f"[Python VM] Error: {vm.error}"); return False

if __name__ == "__main__":
    main()