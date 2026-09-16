"""
S.W.UIR Python VM Interpreter
Stack-based VM that can execute bytecode from IL
"""
import struct
import json
import sys
from enum import IntEnum
from typing import List, Optional, Union
from dataclasses import dataclass, field

class VMOpcode(IntEnum):
    NOP = 0x00
    PUSH_I32 = 0x10
    PUSH_I64 = 0x11
    PUSH_F32 = 0x12
    PUSH_F64 = 0x13
    POP = 0x14
    DUP = 0x15
    SWAP = 0x16
    ADD = 0x20
    SUB = 0x21
    MUL = 0x22
    DIV = 0x23
    MOD = 0x24
    NEG = 0x25
    EQ = 0x30
    NE = 0x31
    LT = 0x32
    LE = 0x33
    GT = 0x34
    GE = 0x35
    AND = 0x38
    OR = 0x39
    NOT = 0x3A
    JMP = 0x40
    JMP_IF = 0x41
    JMP_IF_NOT = 0x42
    CALL = 0x43
    RET = 0x44
    LOAD = 0x50
    STORE = 0x51
    LOAD_GLOBAL = 0x52
    STORE_GLOBAL = 0x53
    PRINT = 0x60
    PRINTLN = 0x61
    WARP = 0x70
    JOIN = 0x71
    HALT = 0xFF

class VMValueType(IntEnum):
    I32 = 1
    I64 = 2
    F32 = 3
    F64 = 4
    PTR = 5

@dataclass
class VMStackValue:
    type: VMValueType
    value: Union[int, float, bytes] = 0

class VMError(Exception):
    pass

class VMContext:
    def __init__(self, bytecode: bytes):
        self.bytecode = bytecode
        self.pc = 0
        self.stack: List[VMStackValue] = []
        self.globals: List[VMStackValue] = []
        self.halted = False
        self.error: Optional[str] = None
    
    def push_i32(self, val: int):
        self.stack.append(VMStackValue(VMValueType.I32, val))
    
    def push_i64(self, val: int):
        self.stack.append(VMStackValue(VMValueType.I64, val))
    
    def push_f32(self, val: float):
        self.stack.append(VMStackValue(VMValueType.F32, val))
    
    def push_f64(self, val: float):
        self.stack.append(VMStackValue(VMValueType.F64, val))
    
    def pop(self) -> VMStackValue:
        if not self.stack:
            raise VMError("Stack underflow")
        return self.stack.pop()
    
    def peek(self) -> VMStackValue:
        if not self.stack:
            raise VMError("Stack empty")
        return self.stack[-1]
    
    def ensure_globals(self, idx: int):
        while len(self.globals) <= idx:
            self.globals.append(VMStackValue(VMValueType.I32, 0))
    
    def binary_op(self, opcode: int):
        b = self.pop()
        a = self.pop()
        
        if a.type == VMValueType.I32 and b.type == VMValueType.I32:
            if opcode == VMOpcode.ADD: res = a.value + b.value
            elif opcode == VMOpcode.SUB: res = a.value - b.value
            elif opcode == VMOpcode.MUL: res = a.value * b.value
            elif opcode == VMOpcode.DIV: res = a.value // b.value if b.value else 0
            elif opcode == VMOpcode.MOD: res = a.value % b.value if b.value else 0
            elif opcode == VMOpcode.EQ: res = int(a.value == b.value)
            elif opcode == VMOpcode.NE: res = int(a.value != b.value)
            elif opcode == VMOpcode.LT: res = int(a.value < b.value)
            elif opcode == VMOpcode.LE: res = int(a.value <= b.value)
            elif opcode == VMOpcode.GT: res = int(a.value > b.value)
            elif opcode == VMOpcode.GE: res = int(a.value >= b.value)
            elif opcode == VMOpcode.AND: res = int(a.value and b.value)
            elif opcode == VMOpcode.OR: res = int(a.value or b.value)
            else: raise VMError(f"Unknown binary op: {opcode}")
            self.push_i32(res)
        elif a.type in (VMValueType.F32, VMValueType.F64) and b.type in (VMValueType.F32, VMValueType.F64):
            av = float(a.value)
            bv = float(b.value)
            if opcode == VMOpcode.ADD: res = av + bv
            elif opcode == VMOpcode.SUB: res = av - bv
            elif opcode == VMOpcode.MUL: res = av * bv
            elif opcode == VMOpcode.DIV: res = av / bv if bv else 0
            elif opcode == VMOpcode.EQ: res = int(av == bv)
            elif opcode == VMOpcode.NE: res = int(av != bv)
            elif opcode == VMOpcode.LT: res = int(av < bv)
            elif opcode == VMOpcode.LE: res = int(av <= bv)
            elif opcode == VMOpcode.GT: res = int(av > bv)
            elif opcode == VMOpcode.GE: res = int(av >= bv)
            else: raise VMError(f"Unknown float binary op: {opcode}")
            self.push_f64(res)
        else:
            raise VMError("Type mismatch in binary op")
    
    def unary_op(self, opcode: int):
        a = self.pop()
        if a.type == VMValueType.I32:
            if opcode == VMOpcode.NEG: res = -a.value
            elif opcode == VMOpcode.NOT: res = int(not a.value)
            else: raise VMError(f"Unknown unary op: {opcode}")
            self.push_i32(res)
        elif a.type in (VMValueType.F32, VMValueType.F64):
            if opcode == VMOpcode.NEG: res = -float(a.value)
            else: raise VMError(f"Unknown float unary op: {opcode}")
            self.push_f64(res)
        else:
            raise VMError("Type mismatch in unary op")
    
    def execute_instruction(self) -> bool:
        if self.pc >= len(self.bytecode):
            raise VMError("PC out of bounds")
        
        opcode = self.bytecode[self.pc]
        self.pc += 1
        
        if opcode == VMOpcode.NOP:
            pass
        elif opcode == VMOpcode.PUSH_I32:
            if self.pc + 4 > len(self.bytecode):
                raise VMError("PUSH_I32: truncated")
            val = struct.unpack('<i', self.bytecode[self.pc:self.pc+4])[0]
            self.pc += 4
            self.push_i32(val)
        elif opcode == VMOpcode.PUSH_I64:
            if self.pc + 8 > len(self.bytecode):
                raise VMError("PUSH_I64: truncated")
            val = struct.unpack('<q', self.bytecode[self.pc:self.pc+8])[0]
            self.pc += 8
            self.push_i64(val)
        elif opcode == VMOpcode.PUSH_F32:
            if self.pc + 4 > len(self.bytecode):
                raise VMError("PUSH_F32: truncated")
            val = struct.unpack('<f', self.bytecode[self.pc:self.pc+4])[0]
            self.pc += 4
            self.push_f32(val)
        elif opcode == VMOpcode.PUSH_F64:
            if self.pc + 8 > len(self.bytecode):
                raise VMError("PUSH_F64: truncated")
            val = struct.unpack('<d', self.bytecode[self.pc:self.pc+8])[0]
            self.pc += 8
            self.push_f64(val)
        elif opcode == VMOpcode.POP:
            self.pop()
        elif opcode == VMOpcode.DUP:
            self.stack.append(self.peek())
        elif opcode == VMOpcode.SWAP:
            if len(self.stack) < 2:
                raise VMError("SWAP: need 2 values")
            self.stack[-1], self.stack[-2] = self.stack[-2], self.stack[-1]
        elif opcode in (VMOpcode.ADD, VMOpcode.SUB, VMOpcode.MUL, VMOpcode.DIV, 
                       VMOpcode.MOD, VMOpcode.EQ, VMOpcode.NE, VMOpcode.LT,
                       VMOpcode.LE, VMOpcode.GT, VMOpcode.GE, VMOpcode.AND, VMOpcode.OR):
            self.binary_op(opcode)
        elif opcode in (VMOpcode.NEG, VMOpcode.NOT):
            self.unary_op(opcode)
        elif opcode == VMOpcode.JMP:
            if self.pc + 4 > len(self.bytecode):
                raise VMError("JMP: truncated")
            offset = struct.unpack('<i', self.bytecode[self.pc:self.pc+4])[0]
            self.pc = offset
        elif opcode == VMOpcode.JMP_IF:
            if self.pc + 4 > len(self.bytecode):
                raise VMError("JMP_IF: truncated")
            offset = struct.unpack('<i', self.bytecode[self.pc:self.pc+4])[0]
            self.pc += 4
            cond = self.pop()
            if cond.type == VMValueType.I32 and cond.value:
                self.pc = offset
        elif opcode == VMOpcode.JMP_IF_NOT:
            if self.pc + 4 > len(self.bytecode):
                raise VMError("JMP_IF_NOT: truncated")
            offset = struct.unpack('<i', self.bytecode[self.pc:self.pc+4])[0]
            self.pc += 4
            cond = self.pop()
            if cond.type == VMValueType.I32 and not cond.value:
                self.pc = offset
        elif opcode == VMOpcode.CALL:
            if self.pc + 4 > len(self.bytecode):
                raise VMError("CALL: truncated")
            addr = struct.unpack('<i', self.bytecode[self.pc:self.pc+4])[0]
            self.pc += 4
            self.push_i32(self.pc)
            self.pc = addr
        elif opcode == VMOpcode.RET:
            ret_addr = self.pop()
            if ret_addr.type == VMValueType.I32:
                self.pc = ret_addr.value
            else:
                raise VMError("RET: invalid return address")
        elif opcode == VMOpcode.LOAD:
            idx = self.pop()
            if idx.type == VMValueType.I32 and 0 <= idx.value < len(self.globals):
                self.stack.append(self.globals[idx.value])
            else:
                raise VMError("LOAD: invalid global index")
        elif opcode == VMOpcode.STORE:
            idx = self.pop()
            val = self.pop()
            if idx.type == VMValueType.I32 and idx.value >= 0:
                self.ensure_globals(idx.value)
                self.globals[idx.value] = val
            else:
                raise VMError("STORE: invalid global index")
        elif opcode == VMOpcode.LOAD_GLOBAL:
            if self.pc + 4 > len(self.bytecode):
                raise VMError("LOAD_GLOBAL: truncated")
            idx = struct.unpack('<i', self.bytecode[self.pc:self.pc+4])[0]
            self.pc += 4
            if 0 <= idx < len(self.globals):
                self.stack.append(self.globals[idx])
            else:
                raise VMError("LOAD_GLOBAL: invalid index")
        elif opcode == VMOpcode.STORE_GLOBAL:
            if self.pc + 4 > len(self.bytecode):
                raise VMError("STORE_GLOBAL: truncated")
            idx = struct.unpack('<i', self.bytecode[self.pc:self.pc+4])[0]
            self.pc += 4
            val = self.pop()
            if idx >= 0:
                self.ensure_globals(idx)
                self.globals[idx] = val
            else:
                raise VMError("STORE_GLOBAL: invalid index")
        elif opcode == VMOpcode.PRINT:
            v = self.pop()
            if v.type == VMValueType.I32: print(v.value, end='')
            elif v.type == VMValueType.I64: print(v.value, end='')
            elif v.type in (VMValueType.F32, VMValueType.F64): print(v.value, end='')
        elif opcode == VMOpcode.PRINTLN:
            v = self.pop()
            if v.type == VMValueType.I32: print(v.value)
            elif v.type == VMValueType.I64: print(v.value)
            elif v.type in (VMValueType.F32, VMValueType.F64): print(v.value)
            else: print()
        elif opcode == VMOpcode.HALT:
            self.halted = True
        else:
            raise VMError(f"Unknown opcode: {opcode:#02x}")
        
        return not self.halted
    
    def execute(self) -> bool:
        try:
            while not self.halted and self.pc < len(self.bytecode):
                if not self.execute_instruction():
                    break
            return self.error is None
        except VMError as e:
            self.error = str(e)
            return False

def serialize_bytecode(bytecode: bytes) -> str:
    return json.dumps({"bytecode": bytecode.hex(), "size": len(bytecode)})

def deserialize_bytecode(json_str: str) -> bytes:
    data = json.loads(json_str)
    return bytes.fromhex(data["bytecode"])

# Bytecode builder helper
class BytecodeBuilder:
    def __init__(self):
        self.code = bytearray()
    
    def emit(self, opcode: int):
        self.code.append(opcode)
    
    def emit_i32(self, val: int):
        self.code.extend(struct.pack('<i', val))
    
    def emit_i64(self, val: int):
        self.code.extend(struct.pack('<q', val))
    
    def emit_f32(self, val: float):
        self.code.extend(struct.pack('<f', val))
    
    def emit_f64(self, val: float):
        self.code.extend(struct.pack('<d', val))
    
    def push_i32(self, val: int):
        self.emit(VMOpcode.PUSH_I32)
        self.emit_i32(val)
    
    def push_f64(self, val: float):
        self.emit(VMOpcode.PUSH_F64)
        self.emit_f64(val)
    
    def add(self):
        self.emit(VMOpcode.ADD)
    
    def mul(self):
        self.emit(VMOpcode.MUL)
    
    def println(self):
        self.emit(VMOpcode.PRINTLN)
    
    def halt(self):
        self.emit(VMOpcode.HALT)
    
    def jmp_if(self, offset: int):
        self.emit(VMOpcode.JMP_IF)
        self.emit_i32(offset)
    
    def jmp(self, offset: int):
        self.emit(VMOpcode.JMP)
        self.emit_i32(offset)
    
    def store_global(self, idx: int):
        self.emit(VMOpcode.STORE_GLOBAL)
        self.emit_i32(idx)
    
    def load_global(self, idx: int):
        self.emit(VMOpcode.LOAD_GLOBAL)
        self.emit_i32(idx)
    
    def build(self) -> bytes:
        return bytes(self.code)

# Demo: Simple factorial bytecode
def create_factorial_bytecode() -> bytes:
    b = BytecodeBuilder()
    b.push_i32(5); b.store_global(0)
    b.push_i32(1); b.store_global(1)
    loop_start = len(b.code)
    b.load_global(0); b.push_i32(1); b.emit(VMOpcode.SUB); b.store_global(0)
    b.load_global(1); b.load_global(0); b.emit(VMOpcode.MUL); b.store_global(1)
    b.load_global(0); b.push_i32(1); b.emit(VMOpcode.GT)
    b.jmp_if(loop_start)  # absolute address
    b.load_global(1); b.println(); b.halt()
    return b.build()

def create_fibonacci_bytecode() -> bytes:
    b = BytecodeBuilder()
    # Compute fibonacci(10) = 55
    # n=10 in global 0
    b.push_i32(10)
    b.store_global(0)
    # a=0 in global 1
    b.push_i32(0)
    b.store_global(1)
    # b=1 in global 2
    b.push_i32(1)
    b.store_global(2)
    # Loop
    loop_start = len(b.code)
    # Load n
    b.load_global(0)
    # Push 1
    b.push_i32(1)
    b.emit(VMOpcode.SUB)  # n = n - 1
    b.store_global(0)
    # t = a + b
    b.load_global(1)
    b.load_global(2)
    b.emit(VMOpcode.ADD)
    # a = b
    b.load_global(2)
    b.store_global(1)
    # b = t
    b.store_global(2)
    b.load_global(0); b.push_i32(0); b.emit(VMOpcode.GT)
    b.jmp_if(loop_start)
    b.load_global(2); b.println(); b.halt()
    return b.build()

if __name__ == "__main__":
    print("Testing Python VM...")
    
    # Test factorial
    bc = create_factorial_bytecode()
    print(f"Factorial bytecode: {bc.hex()}")
    vm = VMContext(bc)
    if vm.execute():
        print("Factorial VM executed successfully")
    else:
        print(f"Factorial VM error: {vm.error}")
    
    # Test fibonacci
    bc2 = create_fibonacci_bytecode()
    print(f"\nFibonacci bytecode: {bc2.hex()}")
    vm2 = VMContext(bc2)
    if vm2.execute():
        print("Fibonacci VM executed successfully")
    else:
        print(f"Fibonacci VM error: {vm2.error}")
    
    # Test serialization
    json_str = serialize_bytecode(bc)
    print(f"\nSerialized: {json_str}")
    bc_restored = deserialize_bytecode(json_str)
    print(f"Restored bytecode matches: {bc == bc_restored}")