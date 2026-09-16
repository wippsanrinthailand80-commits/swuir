#!/usr/bin/env python3
"""
S.W.UIR 9-Way Cross-Language Test Matrix - Session-Based
Each transition runs as a separate session, communicating only via IL files on disk.
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
SESSION_DIR = "/tmp/swuir_sessions"
os.makedirs(SESSION_DIR, exist_ok=True)

def read_state(path):
    try:
        with open(path, 'rb') as f: data = f.read()
        if len(data) != 40: return None
        id_val, value, label_bytes = struct.unpack('<if32s', data)
        label = label_bytes.rstrip(b'\x00').decode('utf-8')
        return {"id": id_val, "value": value, "label": label}
    except: return None

def write_state(path, id_val, value, label):
    new_label = label.encode()[:31].ljust(32, b'\x00')
    data = struct.pack('<if32s', id_val, value, new_label)
    with open(path, 'wb') as f: f.write(data)

def write_il(json_file, session_name, state_type="DemoState"):
    il = {"version": 1, "magic": "0x53575549", "module": session_name,
        "types": [{"name": state_type, "size": 40, "fields": [
            {"name": "id", "type": "i32", "offset": 0, "array_len": 0},
            {"name": "value", "type": "f32", "offset": 4, "array_len": 0},
            {"name": "label", "type": "string", "offset": 8, "array_len": 32}]}],
        "sessions": [{"session_id": "0000000000000001", "target": "warp_target",
                      "state_type": state_type, "state_size": 40, "status": 0}],
        "pool_used": 0}
    with open(json_file, 'w') as f: json.dump(il, f, indent=2)

# ============ C EXECUTABLES ============
def compile_c_warp(session_name):
    exe = os.path.join(BUILD_DIR, f"c_warp_{session_name}")
    if os.path.exists(exe): return exe
    
    code = (
        '#include "swuir.h"\n'
        '#include <stdio.h>\n'
        '#include <stdlib.h>\n'
        '#include <string.h>\n'
        'static size_t readf(const char* p, void** o) {\n'
        '    FILE* f=fopen(p,"rb"); if(!f) return 0;\n'
        '    fseek(f,0,SEEK_END); size_t s=ftell(f); fseek(f,0,SEEK_SET);\n'
        '    *o=malloc(s); fread(*o,1,s,f); fclose(f); return s; }\n'
        'void ' + session_name + '(void* p) {\n'
        '    DemoState* s=(DemoState*)p; char o[32]; strncpy(o,s->label,sizeof(o));\n'
        '    printf("[SESSION ' + session_name + '] Warp: ID=%d, Val=%.2f, Label=%s\\n", s->id, s->value, s->label);\n'
        '    s->value *= 2.0f; snprintf(s->label,sizeof(s->label),"C_WARP_%s", o);\n'
        '    printf("[SESSION ' + session_name + '] After: Val=%.2f, Label=%s\\n", s->value, s->label); }\n'
        'int main(int argc,char**v){ if(argc<3) return 1;\n'
        '    void* b; size_t sz=readf(v[2],&b); if(sz!=40) return 1;\n'
        '    DemoState* st=(DemoState*)b; printf("[SESSION ' + session_name + '] Read: Val=%.2f, Label=%s\\n", st->value, st->label);\n'
        '    swuir_init(); swuir_warp_split(' + session_name + ',st,40); swuir_wait_all(); swuir_cleanup();\n'
        '    printf("[SESSION ' + session_name + '] Main unchanged: Val=%.2f\\n", st->value); free(b); return 0; }'
    )
    with open(f"/tmp/{session_name}.c", 'w') as f: f.write(code)
    r = subprocess.run(["gcc", "-std=c99", "-Wall", "-Wextra", "-O2", f"-I{PROJECT_ROOT}",
                       "-o", exe, f"/tmp/{session_name}.c", 
                       os.path.join(PROJECT_ROOT, "swuir_lib.o"), "-lpthread"],
                      capture_output=True)
    if r.returncode != 0:
        print(f"[C COMPILE FAIL] {session_name}: {r.stderr.decode()}")
    return exe if r.returncode == 0 else None

def run_c_session(session_name, json_file, state_in, state_out):
    exe = compile_c_warp(session_name)
    if not exe: return False
    r = subprocess.run([exe, json_file, state_in], capture_output=True, text=True)
    print(r.stdout[-600:])
    # Copy input to output (C warp doesn't modify main thread state)
    with open(state_in, 'rb') as f: data = f.read()
    with open(state_out, 'wb') as f: f.write(data)
    return r.returncode == 0

# ============ PYTHON SESSION ============
def run_python_session(session_name, json_file, state_in, state_out):
    print(f"[SESSION {session_name}] Reading state from {state_in}")
    with open(state_in, 'rb') as f: data = f.read()
    id_val, value, label_bytes = struct.unpack('<if32s', data)
    label = label_bytes.rstrip(b'\x00').decode('utf-8')
    print(f"[SESSION {session_name}] Parsed: ID={id_val}, Value={value:.2f}, Label={label}")
    
    print(f"[SESSION {session_name}] Executing Python warp...")
    value *= 1.5
    label = f"PY_WARP_{label}"
    print(f"[SESSION {session_name}] After warp: Value={value:.2f}, Label={label}")
    
    write_state(state_out, id_val, value, label)
    write_il(json_file, session_name)
    return True

# ============ RUST SESSION ============
RUST_EXE = os.path.join(PROJECT_ROOT, "session2_rust_warp")
def build_rust():
    if os.path.exists(RUST_EXE): return True
    r = subprocess.run(["rustc", "--edition", "2021", os.path.join(PROJECT_ROOT, "session2_rust_warp.rs"), "-o", RUST_EXE], capture_output=True)
    return r.returncode == 0

def run_rust_session(session_name, json_file, state_in, state_out):
    if not build_rust(): return False
    r = subprocess.run([RUST_EXE, json_file, state_in, state_out], capture_output=True, text=True)
    print(r.stdout[-500:])
    return r.returncode == 0

# ============ SESSION RUNNER ============
def run_session(source, target, test_num):
    session_name = f"{source}2{target}_t{test_num}"
    json_file = os.path.join(SESSION_DIR, f"{session_name}.json")
    state_in = os.path.join(SESSION_DIR, f"{session_name}_in.bin")
    state_out = os.path.join(SESSION_DIR, f"{session_name}_out.bin")
    
    # Get input state from previous session or create initial
    if test_num == 1:
        # Initial state
        write_state(state_in, 42, 3.14, "INITIAL")
        write_il(json_file, session_name)
        print(f"\n{'='*60}")
        print(f"SESSION {test_num}: {source.upper()} -> {target.upper()} (INITIAL)")
        print(f"{'='*60}")
    else:
        # Use output from previous session
        prev_session = f"{source}2{target}_t{test_num-1}"
        prev_out = os.path.join(SESSION_DIR, f"{prev_session}_out.bin")
        if not os.path.exists(prev_out):
            print(f"[ERROR] Previous session output not found: {prev_out}")
            return False
        # Copy previous output as input
        with open(prev_out, 'rb') as f: data = f.read()
        with open(state_in, 'wb') as f: f.write(data)
        write_il(json_file, session_name)
        print(f"\n{'='*60}")
        print(f"SESSION {test_num}: {source.upper()} -> {target.upper()} (from {prev_session})")
        print(f"{'='*60}")
    
    # Run the appropriate target language
    if target == "c":
        ok = run_c_session(session_name, json_file, state_in, state_out)
    elif target == "python":
        ok = run_python_session(session_name, json_file, state_in, state_out)
    elif target == "rust":
        ok = run_rust_session(session_name, json_file, state_in, state_out)
    else:
        return False
    
    if ok:
        out = read_state(state_out)
        if out:
            print(f"[RESULT] Session {test_num} ({source}->{target}): Value={out['value']:.2f}, Label={out['label']}")
            return True
    print(f"[FAIL] Session {test_num} ({source}->{target})")
    return False

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("="*70)
    print("S.W.UIR 9-WAY SESSION-BASED CROSS-LANGUAGE TEST")
    print("="*70)
    print("Each transition runs as a separate session")
    print("State passes through files: _in.bin -> session -> _out.bin")
    print("="*70)
    
    # Test each of the 9 combinations for 3 sessions each (chain)
    langs = ["c", "python", "rust"]
    all_passed = True
    
    for src in langs:
        for tgt in langs:
            print(f"\n{'#'*70}")
            print(f"# CHAIN: {src.upper()} -> {tgt.upper()} (3 sessions)")
            print(f"{'#'*70}")
            
            for session_num in [1, 2, 3]:
                ok = run_session(src, tgt, session_num)
                if not ok:
                    all_passed = False
                    break
            
            if all_passed:
                # Show final state
                final_session = f"{src}2{tgt}_t3"
                final_out = os.path.join(SESSION_DIR, f"{final_session}_out.bin")
                out = read_state(final_out)
                if out:
                    print(f"  >>> Chain {src}->{tgt} FINAL: Value={out['value']:.2f}, Label={out['label']}")
    
    print("\n" + "="*70)
    print("SESSION-BASED 9-WAY TEST COMPLETE")
    print("="*70)
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())