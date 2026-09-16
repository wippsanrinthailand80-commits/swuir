#!/usr/bin/env python3
"""
Session 1: Python Creates IL
Creates IL JSON + state binary that other languages can consume
"""
import json
import struct
import os

def create_il():
    base = "/tmp/swuir_session"
    json_file = f"{base}.json"
    state_file = f"{base}_state.bin"
    
    # Initial state
    state = struct.pack('<if32s', 42, 3.14, b'INITIAL_STATE')
    
    # IL JSON
    il = {
        "version": 1,
        "magic": "0x53575549",
        "module": "session_demo",
        "types": [{
            "name": "DemoState",
            "size": 40,
            "fields": [
                {"name": "id", "type": "i32", "offset": 0, "array_len": 0},
                {"name": "value", "type": "f32", "offset": 4, "array_len": 0},
                {"name": "label", "type": "string", "offset": 8, "array_len": 32}
            ]
        }],
        "sessions": [{
            "session_id": "0000000000000001",
            "target": "warp_target",
            "state_type": "DemoState",
            "state_size": 40,
            "status": 0
        }],
        "pool_used": 0
    }
    
    with open(json_file, 'w') as f:
        json.dump(il, f, indent=2)
    with open(state_file, 'wb') as f:
        f.write(state)
    
    print(f"[Python Session] Created {json_file}")
    print(f"[Python Session] Created {state_file}")
    print(f"[Python Session] Initial state: ID=42, Value=3.14, Label=INITIAL_STATE")
    print(f"[Python Session] Run next session to consume this IL")

if __name__ == "__main__":
    create_il()