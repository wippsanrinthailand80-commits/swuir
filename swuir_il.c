#include "swuir_il.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <time.h>
#include <stdatomic.h>

#define SWUIR_IL_MAGIC 0x53575549

static _Atomic(uint64_t) session_counter = 0;

static uint64_t generate_session_id(void) {
    uint64_t base = (uint64_t)time(NULL) << 32;
    return base | atomic_fetch_add(&session_counter, 1);
}

static size_t type_size(SwuirILType type) {
    switch (type) {
        case SWUIR_TYPE_I8: case SWUIR_TYPE_U8: case SWUIR_TYPE_BOOL: return 1;
        case SWUIR_TYPE_I16: case SWUIR_TYPE_U16: return 2;
        case SWUIR_TYPE_I32: case SWUIR_TYPE_U32: case SWUIR_TYPE_F32: return 4;
        case SWUIR_TYPE_I64: case SWUIR_TYPE_U64: case SWUIR_TYPE_F64: return 8;
        case SWUIR_TYPE_POINTER: return sizeof(void*);
        default: return 0;
    }
}

SwuirILModule* swuir_il_module_create(const char* module_name, size_t pool_size) {
    SwuirILModule* module = calloc(1, sizeof(SwuirILModule));
    if (!module) return NULL;
    
    module->version = SWUIR_IL_VERSION;
    module->magic = SWUIR_IL_MAGIC;
    strncpy(module->module_name, module_name, SWUIR_IL_MAX_STRING - 1);
    module->pool_size = pool_size;
    module->memory_pool = calloc(1, pool_size);
    if (!module->memory_pool) {
        free(module);
        return NULL;
    }
    return module;
}

void swuir_il_module_destroy(SwuirILModule* module) {
    if (!module) return;
    free(module->memory_pool);
    for (size_t i = 0; i < module->session_count; i++) {
        free(module->sessions[i].state_data);
    }
    free(module);
}

int swuir_il_register_type(SwuirILModule* module, const char* name, SwuirILField* fields, size_t field_count) {
    if (!module || module->type_count >= SWUIR_IL_MAX_FIELDS) return -1;
    if (field_count > SWUIR_IL_MAX_FIELDS) return -1;
    
    SwuirILTypeDef* td = &module->types[module->type_count];
    strncpy(td->name, name, SWUIR_IL_MAX_STRING - 1);
    td->field_count = field_count;
    td->total_size = 0;
    
    for (size_t i = 0; i < field_count; i++) {
        td->fields[i] = fields[i];
        td->fields[i].offset = td->total_size;
        td->total_size += type_size(fields[i].type) * (fields[i].array_len ? fields[i].array_len : 1);
    }
    
    module->type_count++;
    return 0;
}

int swuir_il_add_session(SwuirILModule* module, const char* target_func, const char* state_type, void* state_data, size_t state_size) {
    if (!module || module->session_count >= SWUIR_IL_MAX_SESSIONS) return -1;
    
    SwuirILSession* s = &module->sessions[module->session_count];
    strncpy(s->target_func, target_func, SWUIR_IL_MAX_STRING - 1);
    strncpy(s->state_type, state_type, SWUIR_IL_MAX_STRING - 1);
    s->state_data = malloc(state_size);
    if (!s->state_data) return -1;
    memcpy(s->state_data, state_data, state_size);
    s->state_size = state_size;
    s->status = SWUIR_SESSION_PENDING;
    s->session_id = generate_session_id();
    
    module->session_count++;
    return 0;
}

static const char* type_to_str(SwuirILType t) {
    switch (t) {
        case SWUIR_TYPE_I8: return "i8";
        case SWUIR_TYPE_I16: return "i16";
        case SWUIR_TYPE_I32: return "i32";
        case SWUIR_TYPE_I64: return "i64";
        case SWUIR_TYPE_U8: return "u8";
        case SWUIR_TYPE_U16: return "u16";
        case SWUIR_TYPE_U32: return "u32";
        case SWUIR_TYPE_U64: return "u64";
        case SWUIR_TYPE_F32: return "f32";
        case SWUIR_TYPE_F64: return "f64";
        case SWUIR_TYPE_BOOL: return "bool";
        case SWUIR_TYPE_STRING: return "string";
        case SWUIR_TYPE_POINTER: return "ptr";
        case SWUIR_TYPE_STRUCT: return "struct";
        case SWUIR_TYPE_ARRAY: return "array";
        default: return "void";
    }
}

static void json_escape_string(const char* src, char* dst, size_t dst_size) {
    size_t j = 0;
    for (size_t i = 0; src[i] && j < dst_size - 1; i++) {
        switch (src[i]) {
            case '"': case '\\': dst[j++] = '\\'; dst[j++] = src[i]; break;
            case '\n': dst[j++] = '\\'; dst[j++] = 'n'; break;
            case '\r': dst[j++] = '\\'; dst[j++] = 'r'; break;
            case '\t': dst[j++] = '\\'; dst[j++] = 't'; break;
            default: dst[j++] = src[i];
        }
    }
    dst[j] = '\0';
}

char* swuir_il_serialize_json(SwuirILModule* module) {
    if (!module) return NULL;
    
    size_t estimate = 4096 + module->type_count * 512 + module->session_count * 1024;
    char* json = malloc(estimate);
    if (!json) return NULL;
    
    size_t pos = 0;
    pos += snprintf(json + pos, estimate - pos, 
        "{\n  \"version\": %u,\n  \"magic\": \"0x%08X\",\n  \"module\": \"%s\",\n  \"types\": [\n",
        module->version, module->magic, module->module_name);
    
    for (size_t t = 0; t < module->type_count; t++) {
        SwuirILTypeDef* td = &module->types[t];
        pos += snprintf(json + pos, estimate - pos, "    {\n      \"name\": \"%s\",\n      \"size\": %zu,\n      \"fields\": [\n", td->name, td->total_size);
        
        for (size_t f = 0; f < td->field_count; f++) {
            SwuirILField* field = &td->fields[f];
            char escaped[SWUIR_IL_MAX_STRING];
            json_escape_string(field->name, escaped, sizeof(escaped));
            
            pos += snprintf(json + pos, estimate - pos, 
                "        {\"name\": \"%s\", \"type\": \"%s\", \"offset\": %zu, \"array_len\": %zu}%s\n",
                escaped, type_to_str(field->type), field->offset, field->array_len,
                f + 1 < td->field_count ? "," : "");
        }
        
        pos += snprintf(json + pos, estimate - pos, "      ]\n    }%s\n", t + 1 < module->type_count ? "," : "");
    }
    
    pos += snprintf(json + pos, estimate - pos, "  ],\n  \"sessions\": [\n");
    
    for (size_t s = 0; s < module->session_count; s++) {
        SwuirILSession* sess = &module->sessions[s];
        pos += snprintf(json + pos, estimate - pos,
            "    {\n      \"session_id\": \"%016lX\",\n      \"target\": \"%s\",\n      \"state_type\": \"%s\",\n      \"state_size\": %zu,\n      \"status\": %d\n    }%s\n",
            (unsigned long)sess->session_id, sess->target_func, sess->state_type,
            sess->state_size, sess->status, s + 1 < module->session_count ? "," : "");
    }
    
    pos += snprintf(json + pos, estimate - pos, "  ],\n  \"pool_used\": %zu\n}\n", module->pool_used);
    
    return json;
}

int swuir_il_deserialize_json(SwuirILModule* module, const char* json) {
    (void)module; (void)json;
    return -1;
}

void* swuir_il_get_state_data(SwuirILModule* module, uint64_t session_id, size_t* out_size) {
    if (!module) return NULL;
    for (size_t i = 0; i < module->session_count; i++) {
        if (module->sessions[i].session_id == session_id) {
            if (out_size) *out_size = module->sessions[i].state_size;
            return module->sessions[i].state_data;
        }
    }
    return NULL;
}

int swuir_il_set_session_status(SwuirILModule* module, uint64_t session_id, SwuirILSessionStatus status) {
    if (!module) return -1;
    for (size_t i = 0; i < module->session_count; i++) {
        if (module->sessions[i].session_id == session_id) {
            module->sessions[i].status = status;
            return 0;
        }
    }
    return -1;
}