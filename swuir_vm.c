#include "swuir_vm.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define INITIAL_STACK_CAP 256
#define INITIAL_GLOBALS_CAP 64

VMContext* vm_create(const uint8_t* bytecode, size_t size) {
    VMContext* vm = calloc(1, sizeof(VMContext));
    if (!vm) return NULL;
    
    vm->bytecode = malloc(size);
    if (!vm->bytecode) { free(vm); return NULL; }
    memcpy(vm->bytecode, bytecode, size);
    vm->bytecode_size = size;
    vm->pc = 0;
    
    vm->stack_capacity = INITIAL_STACK_CAP;
    vm->stack = calloc(vm->stack_capacity, sizeof(VMStackValue));
    if (!vm->stack) { free(vm->bytecode); free(vm); return NULL; }
    vm->stack_size = 0;
    
    vm->globals_capacity = INITIAL_GLOBALS_CAP;
    vm->globals = calloc(vm->globals_capacity, sizeof(VMStackValue));
    if (!vm->globals) { free(vm->stack); free(vm->bytecode); free(vm); return NULL; }
    vm->globals_count = 0;
    
    vm->halted = 0;
    vm->error = 0;
    vm->error_msg[0] = '\0';
    
    return vm;
}

void vm_destroy(VMContext* vm) {
    if (!vm) return;
    free(vm->bytecode);
    free(vm->stack);
    free(vm->globals);
    free(vm);
}

static void vm_set_error(VMContext* vm, const char* msg) {
    vm->error = 1;
    strncpy(vm->error_msg, msg, sizeof(vm->error_msg) - 1);
    vm->halted = 1;
}

static int vm_stack_ensure(VMContext* vm, size_t needed) {
    if (vm->stack_size + needed <= vm->stack_capacity) return 1;
    size_t new_cap = vm->stack_capacity * 2;
    while (vm->stack_size + needed > new_cap) new_cap *= 2;
    VMStackValue* new_stack = realloc(vm->stack, new_cap * sizeof(VMStackValue));
    if (!new_stack) return 0;
    vm->stack = new_stack;
    vm->stack_capacity = new_cap;
    return 1;
}

static int vm_globals_ensure(VMContext* vm, size_t idx) {
    if (idx < vm->globals_capacity) return 1;
    size_t new_cap = vm->globals_capacity * 2;
    while (idx >= new_cap) new_cap *= 2;
    VMStackValue* new_globals = realloc(vm->globals, new_cap * sizeof(VMStackValue));
    if (!new_globals) return 0;
    memset(new_globals + vm->globals_capacity, 0, (new_cap - vm->globals_capacity) * sizeof(VMStackValue));
    vm->globals = new_globals;
    vm->globals_capacity = new_cap;
    return 1;
}

int vm_push_i32(VMContext* vm, int32_t val) {
    if (!vm_stack_ensure(vm, 1)) return 0;
    vm->stack[vm->stack_size].type = VM_VAL_I32;
    vm->stack[vm->stack_size].value.i32 = val;
    vm->stack_size++;
    return 1;
}

int vm_push_i64(VMContext* vm, int64_t val) {
    if (!vm_stack_ensure(vm, 1)) return 0;
    vm->stack[vm->stack_size].type = VM_VAL_I64;
    vm->stack[vm->stack_size].value.i64 = val;
    vm->stack_size++;
    return 1;
}

int vm_push_f32(VMContext* vm, float val) {
    if (!vm_stack_ensure(vm, 1)) return 0;
    vm->stack[vm->stack_size].type = VM_VAL_F32;
    vm->stack[vm->stack_size].value.f32 = val;
    vm->stack_size++;
    return 1;
}

int vm_push_f64(VMContext* vm, double val) {
    if (!vm_stack_ensure(vm, 1)) return 0;
    vm->stack[vm->stack_size].type = VM_VAL_F64;
    vm->stack[vm->stack_size].value.f64 = val;
    vm->stack_size++;
    return 1;
}

VMStackValue vm_pop(VMContext* vm) {
    VMStackValue zero = {0};
    if (vm->stack_size == 0) {
        vm_set_error(vm, "Stack underflow");
        return zero;
    }
    vm->stack_size--;
    return vm->stack[vm->stack_size];
}

VMStackValue vm_peek(VMContext* vm) {
    VMStackValue zero = {0};
    if (vm->stack_size == 0) {
        vm_set_error(vm, "Stack empty");
        return zero;
    }
    return vm->stack[vm->stack_size - 1];
}

static void vm_binary_op(VMContext* vm, int opcode) {
    VMStackValue b = vm_pop(vm);
    VMStackValue a = vm_pop(vm);
    if (vm->error) return;
    
    VMStackValue result = {0};
    
    if (a.type == VM_VAL_I32 && b.type == VM_VAL_I32) {
        result.type = VM_VAL_I32;
        switch (opcode) {
            case VM_ADD: result.value.i32 = a.value.i32 + b.value.i32; break;
            case VM_SUB: result.value.i32 = a.value.i32 - b.value.i32; break;
            case VM_MUL: result.value.i32 = a.value.i32 * b.value.i32; break;
            case VM_DIV: result.value.i32 = b.value.i32 ? a.value.i32 / b.value.i32 : 0; break;
            case VM_MOD: result.value.i32 = b.value.i32 ? a.value.i32 % b.value.i32 : 0; break;
            case VM_EQ: result.value.i32 = a.value.i32 == b.value.i32; break;
            case VM_NE: result.value.i32 = a.value.i32 != b.value.i32; break;
            case VM_LT: result.value.i32 = a.value.i32 < b.value.i32; break;
            case VM_LE: result.value.i32 = a.value.i32 <= b.value.i32; break;
            case VM_GT: result.value.i32 = a.value.i32 > b.value.i32; break;
            case VM_GE: result.value.i32 = a.value.i32 >= b.value.i32; break;
            case VM_AND: result.value.i32 = a.value.i32 && b.value.i32; break;
            case VM_OR: result.value.i32 = a.value.i32 || b.value.i32; break;
        }
    } else if (a.type == VM_VAL_F64 && b.type == VM_VAL_F64) {
        result.type = VM_VAL_F64;
        switch (opcode) {
            case VM_ADD: result.value.f64 = a.value.f64 + b.value.f64; break;
            case VM_SUB: result.value.f64 = a.value.f64 - b.value.f64; break;
            case VM_MUL: result.value.f64 = a.value.f64 * b.value.f64; break;
            case VM_DIV: result.value.f64 = b.value.f64 ? a.value.f64 / b.value.f64 : 0; break;
            case VM_EQ: result.value.i32 = a.value.f64 == b.value.f64; result.type = VM_VAL_I32; break;
            case VM_NE: result.value.i32 = a.value.f64 != b.value.f64; result.type = VM_VAL_I32; break;
            case VM_LT: result.value.i32 = a.value.f64 < b.value.f64; result.type = VM_VAL_I32; break;
            case VM_LE: result.value.i32 = a.value.f64 <= b.value.f64; result.type = VM_VAL_I32; break;
            case VM_GT: result.value.i32 = a.value.f64 > b.value.f64; result.type = VM_VAL_I32; break;
            case VM_GE: result.value.i32 = a.value.f64 >= b.value.f64; result.type = VM_VAL_I32; break;
        }
    } else {
        vm_set_error(vm, "Type mismatch in binary op");
        return;
    }
    
    if (!vm_stack_ensure(vm, 1)) return;
    vm->stack[vm->stack_size++] = result;
}

static void vm_unary_op(VMContext* vm, int opcode) {
    VMStackValue a = vm_pop(vm);
    if (vm->error) return;
    
    VMStackValue result = {0};
    
    if (a.type == VM_VAL_I32) {
        result.type = VM_VAL_I32;
        switch (opcode) {
            case VM_NEG: result.value.i32 = -a.value.i32; break;
            case VM_NOT: result.value.i32 = !a.value.i32; break;
        }
    } else if (a.type == VM_VAL_F64) {
        result.type = VM_VAL_F64;
        switch (opcode) {
            case VM_NEG: result.value.f64 = -a.value.f64; break;
        }
    }
    
    if (!vm_stack_ensure(vm, 1)) return;
    vm->stack[vm->stack_size++] = result;
}

int vm_execute_instruction(VMContext* vm) {
    if (vm->pc >= vm->bytecode_size) {
        vm_set_error(vm, "PC out of bounds");
        return 0;
    }
    
    uint8_t opcode = vm->bytecode[vm->pc++];
    
    switch (opcode) {
        case VM_NOP:
            break;
            
        case VM_PUSH_I32: {
            if (vm->pc + 4 > vm->bytecode_size) { vm_set_error(vm, "PUSH_I32: truncated"); return 0; }
            int32_t val = *(int32_t*)(vm->bytecode + vm->pc);
            vm->pc += 4;
            vm_push_i32(vm, val);
            break;
        }
        case VM_PUSH_I64: {
            if (vm->pc + 8 > vm->bytecode_size) { vm_set_error(vm, "PUSH_I64: truncated"); return 0; }
            int64_t val = *(int64_t*)(vm->bytecode + vm->pc);
            vm->pc += 8;
            vm_push_i64(vm, val);
            break;
        }
        case VM_PUSH_F32: {
            if (vm->pc + 4 > vm->bytecode_size) { vm_set_error(vm, "PUSH_F32: truncated"); return 0; }
            float val = *(float*)(vm->bytecode + vm->pc);
            vm->pc += 4;
            vm_push_f32(vm, val);
            break;
        }
        case VM_PUSH_F64: {
            if (vm->pc + 8 > vm->bytecode_size) { vm_set_error(vm, "PUSH_F64: truncated"); return 0; }
            double val = *(double*)(vm->bytecode + vm->pc);
            vm->pc += 8;
            vm_push_f64(vm, val);
            break;
        }
        case VM_POP:
            vm_pop(vm);
            break;
        case VM_DUP: {
            VMStackValue v = vm_peek(vm);
            if (!vm_stack_ensure(vm, 1)) return 0;
            vm->stack[vm->stack_size++] = v;
            break;
        }
        case VM_SWAP: {
            if (vm->stack_size < 2) { vm_set_error(vm, "SWAP: need 2 values"); return 0; }
            VMStackValue tmp = vm->stack[vm->stack_size - 1];
            vm->stack[vm->stack_size - 1] = vm->stack[vm->stack_size - 2];
            vm->stack[vm->stack_size - 2] = tmp;
            break;
        }
        
        case VM_ADD: case VM_SUB: case VM_MUL: case VM_DIV: case VM_MOD:
        case VM_EQ: case VM_NE: case VM_LT: case VM_LE: case VM_GT: case VM_GE:
        case VM_AND: case VM_OR:
            vm_binary_op(vm, opcode);
            break;
            
        case VM_NEG: case VM_NOT:
            vm_unary_op(vm, opcode);
            break;
            
        case VM_JMP: {
            if (vm->pc + 4 > vm->bytecode_size) { vm_set_error(vm, "JMP: truncated"); return 0; }
            int32_t offset = *(int32_t*)(vm->bytecode + vm->pc);
            vm->pc = offset;
            break;
        }
        case VM_JMP_IF: {
            if (vm->pc + 4 > vm->bytecode_size) { vm_set_error(vm, "JMP_IF: truncated"); return 0; }
            int32_t offset = *(int32_t*)(vm->bytecode + vm->pc);
            vm->pc += 4;
            VMStackValue cond = vm_pop(vm);
            if (cond.type == VM_VAL_I32 && cond.value.i32) vm->pc = offset;
            break;
        }
        case VM_JMP_IF_NOT: {
            if (vm->pc + 4 > vm->bytecode_size) { vm_set_error(vm, "JMP_IF_NOT: truncated"); return 0; }
            int32_t offset = *(int32_t*)(vm->bytecode + vm->pc);
            vm->pc += 4;
            VMStackValue cond = vm_pop(vm);
            if (cond.type == VM_VAL_I32 && !cond.value.i32) vm->pc = offset;
            break;
        }
        case VM_CALL: {
            if (vm->pc + 4 > vm->bytecode_size) { vm_set_error(vm, "CALL: truncated"); return 0; }
            int32_t addr = *(int32_t*)(vm->bytecode + vm->pc);
            vm->pc += 4;
            if (!vm_stack_ensure(vm, 1)) return 0;
            vm->stack[vm->stack_size].type = VM_VAL_I32;
            vm->stack[vm->stack_size].value.i32 = vm->pc;
            vm->stack_size++;
            vm->pc = addr;
            break;
        }
        case VM_RET: {
            if (vm->stack_size == 0) { vm_set_error(vm, "RET: empty stack"); return 0; }
            VMStackValue ret_addr = vm_pop(vm);
            if (ret_addr.type == VM_VAL_I32) vm->pc = ret_addr.value.i32;
            else vm_set_error(vm, "RET: invalid return address");
            break;
        }
            
        case VM_LOAD: {
            VMStackValue idx = vm_pop(vm);
            if (idx.type == VM_VAL_I32 && idx.value.i32 >= 0 && (size_t)idx.value.i32 < vm->globals_count) {
                if (!vm_stack_ensure(vm, 1)) return 0;
                vm->stack[vm->stack_size++] = vm->globals[idx.value.i32];
            } else {
                vm_set_error(vm, "LOAD: invalid global index");
            }
            break;
        }
        case VM_STORE: {
            VMStackValue idx = vm_pop(vm);
            VMStackValue val = vm_pop(vm);
            if (idx.type == VM_VAL_I32 && idx.value.i32 >= 0) {
                if (vm_globals_ensure(vm, idx.value.i32 + 1)) {
                    vm->globals[idx.value.i32] = val;
                    if ((size_t)idx.value.i32 >= vm->globals_count) vm->globals_count = idx.value.i32 + 1;
                }
            } else {
                vm_set_error(vm, "STORE: invalid global index");
            }
            break;
        }
        case VM_LOAD_GLOBAL: {
            if (vm->pc + 4 > vm->bytecode_size) { vm_set_error(vm, "LOAD_GLOBAL: truncated"); return 0; }
            int32_t idx = *(int32_t*)(vm->bytecode + vm->pc);
            vm->pc += 4;
            if (idx >= 0 && (size_t)idx < vm->globals_count) {
                if (!vm_stack_ensure(vm, 1)) return 0;
                vm->stack[vm->stack_size++] = vm->globals[idx];
            } else {
                vm_set_error(vm, "LOAD_GLOBAL: invalid index");
            }
            break;
        }
        case VM_STORE_GLOBAL: {
            if (vm->pc + 4 > vm->bytecode_size) { vm_set_error(vm, "STORE_GLOBAL: truncated"); return 0; }
            int32_t idx = *(int32_t*)(vm->bytecode + vm->pc);
            vm->pc += 4;
            VMStackValue val = vm_pop(vm);
            if (idx >= 0) {
                if (vm_globals_ensure(vm, idx + 1)) {
                    vm->globals[idx] = val;
                    if ((size_t)idx >= vm->globals_count) vm->globals_count = idx + 1;
                }
            } else {
                vm_set_error(vm, "STORE_GLOBAL: invalid index");
            }
            break;
        }
            
        case VM_PRINT: {
            VMStackValue v = vm_pop(vm);
            if (v.type == VM_VAL_I32) printf("%d", v.value.i32);
            else if (v.type == VM_VAL_I64) printf("%ld", v.value.i64);
            else if (v.type == VM_VAL_F32) printf("%f", v.value.f32);
            else if (v.type == VM_VAL_F64) printf("%f", v.value.f64);
            break;
        }
        case VM_PRINTLN: {
            VMStackValue v = vm_pop(vm);
            if (v.type == VM_VAL_I32) printf("%d\n", v.value.i32);
            else if (v.type == VM_VAL_I64) printf("%ld\n", v.value.i64);
            else if (v.type == VM_VAL_F32) printf("%f\n", v.value.f32);
            else if (v.type == VM_VAL_F64) printf("%f\n", v.value.f64);
            else printf("\n");
            break;
        }
            
        case VM_HALT:
            vm->halted = 1;
            break;
            
        default:
            vm_set_error(vm, "Unknown opcode");
            return 0;
    }
    
    return !vm->error;
}

int vm_execute(VMContext* vm) {
    while (!vm->halted && !vm->error && vm->pc < vm->bytecode_size) {
        if (!vm_execute_instruction(vm)) break;
    }
    return !vm->error;
}

// Simple bytecode serialization to JSON (hex string)
char* vm_serialize_bytecode(const uint8_t* bytecode, size_t size) {
    size_t json_size = size * 3 + 32;
    char* json = malloc(json_size);
    if (!json) return NULL;
    
    size_t pos = 0;
    pos += snprintf(json + pos, json_size - pos, "{\"bytecode\": \"");
    for (size_t i = 0; i < size; i++) {
        pos += snprintf(json + pos, json_size - pos, "%02X", bytecode[i]);
    }
    pos += snprintf(json + pos, json_size - pos, "\", \"size\": %zu}", size);
    return json;
}

uint8_t* vm_deserialize_bytecode(const char* json, size_t* out_size) {
    // Find the hex string between quotes after "bytecode":
    const char* start = strstr(json, "\"bytecode\": \"");
    if (!start) return NULL;
    start += 13;
    const char* end = strchr(start, '"');
    if (!end) return NULL;
    
    size_t hex_len = end - start;
    if (hex_len % 2 != 0) return NULL;
    size_t bin_size = hex_len / 2;
    
    uint8_t* bytecode = malloc(bin_size);
    if (!bytecode) return NULL;
    
    for (size_t i = 0; i < bin_size; i++) {
        char hex[3] = {start[i*2], start[i*2+1], 0};
        bytecode[i] = (uint8_t)strtol(hex, NULL, 16);
    }
    
    if (out_size) *out_size = bin_size;
    return bytecode;
}

// Warp: spawn new VM with given bytecode
int vm_warp_spawn(VMContext* vm, const uint8_t* warp_bytecode, size_t warp_size) {
    (void)vm;
    // In a real implementation, this would spawn a thread with new VM
    // For now, just execute inline
    VMContext* warp_vm = vm_create(warp_bytecode, warp_size);
    if (!warp_vm) return 0;
    int result = vm_execute(warp_vm);
    vm_destroy(warp_vm);
    return result;
}