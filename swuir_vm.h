#ifndef SWUIR_VM_H
#define SWUIR_VM_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

// VM Bytecode Instructions
typedef enum {
    VM_NOP = 0x00,
    
    // Stack manipulation
    VM_PUSH_I32 = 0x10,
    VM_PUSH_I64 = 0x11,
    VM_PUSH_F32 = 0x12,
    VM_PUSH_F64 = 0x13,
    VM_POP = 0x14,
    VM_DUP = 0x15,
    VM_SWAP = 0x16,
    
    // Arithmetic
    VM_ADD = 0x20,
    VM_SUB = 0x21,
    VM_MUL = 0x22,
    VM_DIV = 0x23,
    VM_MOD = 0x24,
    VM_NEG = 0x25,
    
    // Comparison
    VM_EQ = 0x30,
    VM_NE = 0x31,
    VM_LT = 0x32,
    VM_LE = 0x33,
    VM_GT = 0x34,
    VM_GE = 0x35,
    
    // Logic
    VM_AND = 0x38,
    VM_OR = 0x39,
    VM_NOT = 0x3A,
    
    // Control flow
    VM_JMP = 0x40,
    VM_JMP_IF = 0x41,
    VM_JMP_IF_NOT = 0x42,
    VM_CALL = 0x43,
    VM_RET = 0x44,
    
    // Memory
    VM_LOAD = 0x50,
    VM_STORE = 0x51,
    VM_LOAD_GLOBAL = 0x52,
    VM_STORE_GLOBAL = 0x53,
    
    // I/O
    VM_PRINT = 0x60,
    VM_PRINTLN = 0x61,
    
    // Warp/Concurrency
    VM_WARP = 0x70,
    VM_JOIN = 0x71,
    
    // End
    VM_HALT = 0xFF
} VMOpcode;

// Value types
typedef enum {
    VM_VAL_I32 = 1,
    VM_VAL_I64 = 2,
    VM_VAL_F32 = 3,
    VM_VAL_F64 = 4,
    VM_VAL_PTR = 5
} VMValueType;

typedef union {
    int32_t i32;
    int64_t i64;
    float f32;
    double f64;
    void* ptr;
} VMValue;

typedef struct {
    VMValueType type;
    VMValue value;
} VMStackValue;

// VM State
typedef struct {
    uint8_t* bytecode;
    size_t bytecode_size;
    size_t pc;
    
    VMStackValue* stack;
    size_t stack_size;
    size_t stack_capacity;
    
    VMStackValue* globals;
    size_t globals_count;
    size_t globals_capacity;
    
    int halted;
    int error;
    char error_msg[256];
} VMContext;

// VM API
VMContext* vm_create(const uint8_t* bytecode, size_t size);
void vm_destroy(VMContext* vm);
int vm_execute(VMContext* vm);
int vm_execute_instruction(VMContext* vm);

// Stack ops
int vm_push_i32(VMContext* vm, int32_t val);
int vm_push_i64(VMContext* vm, int64_t val);
int vm_push_f32(VMContext* vm, float val);
int vm_push_f64(VMContext* vm, double val);
VMStackValue vm_pop(VMContext* vm);
VMStackValue vm_peek(VMContext* vm);

// Serialization
char* vm_serialize_bytecode(const uint8_t* bytecode, size_t size);
uint8_t* vm_deserialize_bytecode(const char* json, size_t* out_size);

// Warp support
int vm_warp_spawn(VMContext* vm, const uint8_t* warp_bytecode, size_t warp_size);

#ifdef __cplusplus
}
#endif

#endif