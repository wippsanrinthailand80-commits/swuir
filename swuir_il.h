#ifndef SWUIR_IL_H
#define SWUIR_IL_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define SWUIR_IL_VERSION 1
#define SWUIR_IL_MAX_STRING 256
#define SWUIR_IL_MAX_FIELDS 32
#define SWUIR_IL_MAX_SESSIONS 64

typedef enum {
    SWUIR_TYPE_VOID = 0,
    SWUIR_TYPE_I8 = 1,
    SWUIR_TYPE_I16 = 2,
    SWUIR_TYPE_I32 = 3,
    SWUIR_TYPE_I64 = 4,
    SWUIR_TYPE_U8 = 5,
    SWUIR_TYPE_U16 = 6,
    SWUIR_TYPE_U32 = 7,
    SWUIR_TYPE_U64 = 8,
    SWUIR_TYPE_F32 = 9,
    SWUIR_TYPE_F64 = 10,
    SWUIR_TYPE_BOOL = 11,
    SWUIR_TYPE_STRING = 12,
    SWUIR_TYPE_POINTER = 13,
    SWUIR_TYPE_STRUCT = 14,
    SWUIR_TYPE_ARRAY = 15
} SwuirILType;

typedef enum {
    SWUIR_SESSION_PENDING = 0,
    SWUIR_SESSION_RUNNING = 1,
    SWUIR_SESSION_COMPLETED = 2,
    SWUIR_SESSION_FAILED = 3
} SwuirILSessionStatus;

typedef struct {
    char name[SWUIR_IL_MAX_STRING];
    SwuirILType type;
    uint64_t value_u64;
    int64_t value_i64;
    double value_f64;
    char value_str[SWUIR_IL_MAX_STRING];
    size_t array_len;
    size_t struct_field_count;
    size_t offset;
} SwuirILField;

typedef struct {
    char name[SWUIR_IL_MAX_STRING];
    SwuirILField fields[SWUIR_IL_MAX_FIELDS];
    size_t field_count;
    size_t total_size;
} SwuirILTypeDef;

typedef struct {
    char target_func[SWUIR_IL_MAX_STRING];
    char state_type[SWUIR_IL_MAX_STRING];
    uint8_t* state_data;
    size_t state_size;
    SwuirILSessionStatus status;
    uint64_t session_id;
} SwuirILSession;

typedef struct {
    uint32_t version;
    uint32_t magic;
    char module_name[SWUIR_IL_MAX_STRING];
    SwuirILTypeDef types[SWUIR_IL_MAX_FIELDS];
    size_t type_count;
    SwuirILSession sessions[SWUIR_IL_MAX_SESSIONS];
    size_t session_count;
    uint8_t* memory_pool;
    size_t pool_size;
    size_t pool_used;
} SwuirILModule;

SwuirILModule* swuir_il_module_create(const char* module_name, size_t pool_size);
void swuir_il_module_destroy(SwuirILModule* module);

int swuir_il_register_type(SwuirILModule* module, const char* name, SwuirILField* fields, size_t field_count);
int swuir_il_add_session(SwuirILModule* module, const char* target_func, const char* state_type, void* state_data, size_t state_size);

char* swuir_il_serialize_json(SwuirILModule* module);
int swuir_il_deserialize_json(SwuirILModule* module, const char* json);

void* swuir_il_get_state_data(SwuirILModule* module, uint64_t session_id, size_t* out_size);
int swuir_il_set_session_status(SwuirILModule* module, uint64_t session_id, SwuirILSessionStatus status);

#ifdef __cplusplus
}
#endif

#endif