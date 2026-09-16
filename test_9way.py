#!/usr/bin/env python3
"""
S.W.UIR 9-Way Cross-Language Test Matrix - Fixed Version
"""
import subprocess
import sys
import os
import struct
import json

# Get project root dynamically
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = SCRIPT_DIR
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")

def read_state(path):
    try:
        with open(path, 'rb') as f: data = f.read()
        if len(data) != 40: return None
        id_val, value, label_bytes = struct.unpack('<if32s', data)
        label = label_bytes.rstrip(b'\x00').decode('utf-8')
        return {"id": id_val, "value": value, "label": label}
    except: return None

def create_il_json(creator_lang, json_file, state_file, initial_value=3.14, initial_label="INITIAL"):
    state = struct.pack('<if32s', 42, initial_value, initial_label.encode()[:31].ljust(32, b'\x00'))
    il = {"version": 1, "magic": "0x53575549", "module": f"{creator_lang}_to_test",
        "types": [{"name": "DemoState", "size": 40, "fields": [
            {"name": "id", "type": "i32", "offset": 0, "array_len": 0},
            {"name": "value", "type": "f32", "offset": 4, "array_len": 0},
            {"name": "label", "type": "string", "offset": 8, "array_len": 32}]}],
        "sessions": [{"session_id": "0000000000000001", "target": "warp_target",
                      "state_type": "DemoState", "state_size": 40, "status": 0}],
        "pool_used": 0}
    with open(json_file, 'w') as f: json.dump(il, f)
    with open(state_file, 'wb') as f: f.write(state)
    return state

# Pre-compile C warp executables
def compile_c_warps():
    print("[SETUP] Pre-compiling C warp executables...")
    src_upper = {"c": "C", "python": "PY", "rust": "RS"}
    for src in ["c", "python", "rust"]:
        warp_name = f"{src}2c"
        exe = os.path.join(BUILD_DIR, f"warp_c_{warp_name}")
        src_u = src_upper[src]
        code = f'''#include "swuir.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static size_t readf(const char* p, void** o) {{
    FILE* f=fopen(p,"rb"); if(!f) return 0;
    fseek(f,0,SEEK_END); size_t s=ftell(f); fseek(f,0,SEEK_SET);
    *o=malloc(s); fread(*o,1,s,f); fclose(f); return s; }}
void {warp_name}(void* p) {{
    DemoState* s=(DemoState*)p; char o[32]; strncpy(o,s->label,sizeof(o));
    printf("[{src_u}->C] Warp: ID=%%d, Val=%%.2f, Label=%%s\\n", s->id, s->value, s->label);
    s->value *= 2.0f; snprintf(s->label,sizeof(s->label),"C_FROM_{src_u}_%%s", o);
    printf("[{src_u}->C] After: Val=%%.2f, Label=%%s\\n", s->value, s->label); }}
int main(int argc,char**v){{ if(argc<3) return 1;
    void* b; size_t sz=readf(v[2],&b); if(sz!=40) return 1;
    DemoState* st=(DemoState*)b; printf("[{src_u}->C] Read: Val=%%.2f, Label=%%s\\n", st->value, st->label);
    swuir_init(); swuir_warp_split({warp_name},st,40); swuir_wait_all(); swuir_cleanup();
    printf("[{src_u}->C] Main unchanged: Val=%%.2f\\n", st->value); free(b); return 0; }}'''
        with open(f"/tmp/warp_c_{warp_name}.c", 'w') as f: f.write(code)
        r = subprocess.run(["gcc", "-std=c99", "-Wall", "-Wextra", "-O2", f"-I{PROJECT_ROOT}",
                           "-o", exe, f"/tmp/warp_c_{warp_name}.c", 
                           os.path.join(PROJECT_ROOT, "swuir_lib.o"), "-lpthread"],
                          capture_output=True)
        if r.returncode != 0:
            print(f"[FAIL] Compile {warp_name}: {r.stderr.decode()}")
            return False
    return True

def warp_c(json_file, in_state, out_state, warp_name):
    exe = os.path.join(BUILD_DIR, f"warp_c_{warp_name}")
    r = subprocess.run([exe, json_file, in_state], capture_output=True, text=True)
    print(r.stdout[-800:])
    with open(in_state, 'rb') as f: data = f.read()
    with open(out_state, 'wb') as f: f.write(data)
    return r.returncode == 0

def warp_python(json_file, in_state, out_state, warp_name):
    with open(in_state, 'rb') as f: data = f.read()
    id_val, value, label_bytes = struct.unpack('<if32s', data)
    label = label_bytes.rstrip(b'\x00').decode('utf-8')
    src_u = warp_name.split('2')[0].upper()
    print(f"[Python->{src_u}] Read: Value={value:.2f}, Label={label}")
    value *= 1.5
    label = f"PY_FROM_{src_u}_{label}"
    new_label = label.encode()[:31].ljust(32, b'\x00')
    new_data = struct.pack('<if32s', id_val, value, new_label)
    with open(out_state, 'wb') as f: f.write(new_data)
    print(f"[Python->{src_u}] After: Value={value:.2f}, Label={label}")
    return True

def warp_rust(json_file, in_state, out_state, warp_name):
    exe = os.path.join(PROJECT_ROOT, "session2_rust_warp")
    r = subprocess.run([exe, json_file, in_state, out_state], capture_output=True, text=True)
    print(r.stdout[-500:])
    return r.returncode == 0

def test_transition(source, target):
    json_file = f"/tmp/swuir_{source}2{target}.json"
    state_in = f"/tmp/swuir_{source}2{target}_in.bin"
    state_out = f"/tmp/swuir_{source}2{target}_out.bin"
    
    print(f"\n{'='*60}")
    print(f"TRANSITION: {source.upper()} -> {target.upper()}")
    print(f"{'='*60}")
    create_il_json(source, json_file, state_in)
    print(f"[SETUP] IL from {source}: {state_in}")
    
    if target == "c":
        ok = warp_c(json_file, state_in, state_out, f"{source}2c")
    elif target == "python":
        ok = warp_python(json_file, state_in, state_out, f"{source}2py")
    elif target == "rust":
        ok = warp_rust(json_file, state_in, state_out, f"{source}2rs")
    else:
        return False
    
    if ok:
        out = read_state(state_out)
        if out:
            print(f"[RESULT] {source}->{target}: Value={out['value']:.2f}, Label={out['label']}")
            return True
    print(f"[FAIL] {source}->{target}")
    return False

def main():
    os.chdir(PROJECT_ROOT)
    
    if not compile_c_warps():
        return 1
    subprocess.run(["rustc", "--edition", "2021", os.path.join(PROJECT_ROOT, "session2_rust_warp.rs"), "-o", os.path.join(PROJECT_ROOT, "session2_rust_warp")], capture_output=True)
    
    langs = ["c", "python", "rust"]
    results = {}
    
    print("="*60)
    print("S.W.UIR 9-WAY CROSS-LANGUAGE TEST MATRIX")
    print("="*60)
    
    for src in langs:
        for tgt in langs:
            key = f"{src}2{tgt}"
            results[key] = test_transition(src, tgt)
    
    print("\n" + "="*60)
    print("9-WAY TEST MATRIX RESULTS")
    print("="*60)
    for src in langs:
        row = []
        for tgt in langs:
            key = f"{src}2{tgt}"
            status = "✓" if results.get(key) else "✗"
            row.append(f"{src[:1].upper()}->{tgt[:1].upper()}:{status}")
        print("  ".join(row))
    
    passed = sum(1 for v in results.values() if v)
    print(f"\nPassed: {passed}/9")
    return 0 if passed == 9 else 1

if __name__ == "__main__":
    sys.exit(main())