"""
S.W.UIR Python Bindings - Simplified Version
Pure Python ctypes wrapper for the S.W.UIR Intermediate Language C library.
"""
import ctypes
import json
import os
import sys
from enum import IntEnum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path

class SwuirILType(IntEnum):
    VOID = 0; I8 = 1; I16 = 2; I32 = 3; I64 = 4
    U8 = 5; U16 = 6; U32 = 7; U64 = 8
    F32 = 9; F64 = 10
    BOOL = 11; STRING = 12; POINTER = 13; STRUCT = 14; ARRAY = 15

class SwuirILSessionStatus(IntEnum):
    PENDING = 0; RUNNING = 1; COMPLETED = 2; FAILED = 3

@dataclass
class SwuirILField:
    name: str
    type: SwuirILType
    value: Any = None
    array_len: int = 0

@dataclass
class SwuirILTypeDef:
    name: str
    fields: List[SwuirILField] = field(default_factory=list)

@dataclass
class SwuirILSession:
    session_id: int
    target_func: str
    state_type: str
    state_data: bytes
    status: SwuirILSessionStatus

class SwuirILLibrary:
    _instance = None
    _lib = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_library()
        return cls._instance
    
    def _load_library(self):
        search_paths = [
            Path('/root/madel'),
            Path('/usr/local/lib'),
            Path('/usr/lib'),
            Path(__file__).parent.parent,
            Path.cwd(),
        ]
        
        for path in search_paths:
            lib_path = path / 'libswuir_il.so'
            if lib_path.exists():
                try:
                    self._lib = ctypes.CDLL(str(lib_path))
                    self._setup_functions()
                    print(f"[Python] Loaded library from {lib_path}")
                    return
                except OSError as e:
                    print(f"[Python] Failed to load {lib_path}: {e}")
        
        raise RuntimeError("Could not load S.W.UIR IL library")
    
    def _setup_functions(self):
        lib = self._lib
        
        lib.swuir_il_module_create.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
        lib.swuir_il_module_create.restype = ctypes.c_void_p
        
        lib.swuir_il_module_destroy.argtypes = [ctypes.c_void_p]
        lib.swuir_il_module_destroy.restype = None
        
        lib.swuir_il_add_session.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t]
        lib.swuir_il_add_session.restype = ctypes.c_int
        
        lib.swuir_il_serialize_json.argtypes = [ctypes.c_void_p]
        lib.swuir_il_serialize_json.restype = ctypes.c_char_p
        
        lib.swuir_il_get_state_data.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.POINTER(ctypes.c_size_t)]
        lib.swuir_il_get_state_data.restype = ctypes.c_void_p
        
        lib.swuir_il_set_session_status.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_int]
        lib.swuir_il_set_session_status.restype = ctypes.c_int

class SwuirILContext:
    def __init__(self, module_name: str = "swuir_module", pool_size: int = 1024*1024):
        self._lib_wrapper = SwuirILLibrary()
        self._module = self._lib_wrapper._lib.swuir_il_module_create(
            module_name.encode('utf-8'), pool_size
        )
        if not self._module:
            raise RuntimeError("Failed to create IL module")
        self._sessions = {}
        self._next_session_id = 1
    
    def __del__(self):
        if hasattr(self, '_module') and self._module:
            self._lib_wrapper._lib.swuir_il_module_destroy(self._module)
    
    def add_session(self, target_func: str, state_type: str, state_data: bytes) -> int:
        session_id = self._next_session_id
        self._next_session_id += 1
        
        buf = ctypes.create_string_buffer(state_data)
        result = self._lib_wrapper._lib.swuir_il_add_session(
            self._module,
            target_func.encode('utf-8'),
            state_type.encode('utf-8'),
            buf,
            len(state_data)
        )
        if result == 0:
            self._sessions[session_id] = SwuirILSession(
                session_id=session_id,
                target_func=target_func,
                state_type=state_type,
                state_data=state_data,
                status=SwuirILSessionStatus.PENDING
            )
        return session_id if result == 0 else -1
    
    def serialize_json(self) -> str:
        json_ptr = self._lib_wrapper._lib.swuir_il_serialize_json(self._module)
        if not json_ptr:
            return "{}"
        result = ctypes.string_at(json_ptr).decode('utf-8')
        return result
    
    def get_state_data(self, session_id: int) -> Optional[bytes]:
        size = ctypes.c_size_t(0)
        ptr = self._lib_wrapper._lib.swuir_il_get_state_data(self._module, session_id, ctypes.byref(size))
        if not ptr or size.value == 0:
            return None
        return ctypes.string_at(ptr, size.value)
    
    def set_session_status(self, session_id: int, status: SwuirILSessionStatus) -> bool:
        result = self._lib_wrapper._lib.swuir_il_set_session_status(self._module, session_id, int(status))
        return result == 0

def create_demo_state():
    import struct
    data = struct.pack('<if32s', 42, 3.14, b'INITIAL_STATE')
    return data

def main():
    print("[Python] Creating S.W.UIR IL context...")
    ctx = SwuirILContext("python_demo", 1024*1024)
    
    print("[Python] Creating initial state...")
    state_data = create_demo_state()
    print(f"[Python] State data: {state_data.hex()}")
    
    print("[Python] Adding warp session targeting 'dormant_block_target'...")
    session_id = ctx.add_session("dormant_block_target", "DemoState", state_data)
    if session_id < 0:
        print("[Python] Failed to add session")
        return 1
    
    print(f"[Python] Session created with ID: {session_id}")
    
    print("[Python] Serializing to JSON...")
    json_output = ctx.serialize_json()
    print(json_output)
    
    print("[Python] Demo complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())