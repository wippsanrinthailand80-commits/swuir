#include "swuir_il.h"
#include "swuir.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static size_t read_file(const char* path, char** out_buffer) {
    FILE* f = fopen(path, "rb");
    if (!f) return 0;
    fseek(f, 0, SEEK_END);
    size_t size = ftell(f);
    fseek(f, 0, SEEK_SET);
    *out_buffer = malloc(size + 1);
    fread(*out_buffer, 1, size, f);
    (*out_buffer)[size] = '\0';
    fclose(f);
    return size;
}

void dormant_block_target(void* state_ptr) {
    typedef struct { int id; float value; char label[32]; } DemoState;
    DemoState* state = (DemoState*)state_ptr;
    char original_label[32];
    strncpy(original_label, state->label, sizeof(original_label));
    
    printf("[C EXECUTOR] Warp session executing dormant_block_target\n");
    printf("[C EXECUTOR]   Inherited state: ID=%d, Value=%.2f, Label=%s\n", 
           state->id, state->value, state->label);
    printf("[C EXECUTOR] Modifying state in warp session...\n");
    state->value *= 2.0f;
    snprintf(state->label, sizeof(state->label), "WARPED_%s", original_label);
    printf("[C EXECUTOR] State after modification: Value=%.2f, Label=%s\n", 
           state->value, state->label);
}

int main(int argc, char** argv) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <il_json_file>\n", argv[0]);
        return 1;
    }
    
    char* json_buffer = NULL;
    size_t json_size = read_file(argv[1], &json_buffer);
    if (json_size == 0) {
        fprintf(stderr, "Failed to read JSON file\n");
        return 1;
    }
    
    printf("[C EXECUTOR] Loaded JSON (%zu bytes)\n", json_size);
    printf("[C EXECUTOR] JSON content:\n%s\n", json_buffer);
    
    swuir_init();
    
    SwuirILModule* module = swuir_il_module_create("c_executor", 1024*1024);
    if (!module) {
        fprintf(stderr, "Failed to create IL module\n");
        free(json_buffer);
        return 1;
    }
    
    printf("[C EXECUTOR] Parsing JSON... (using simple parsing for demo)\n");
    
    const char* target_str = "\"target\": \"";
    char* target_start = strstr(json_buffer, target_str);
    if (target_start) {
        target_start += strlen(target_str);
        char* target_end = strchr(target_start, '"');
        if (target_end) {
            *target_end = '\0';
            printf("[C EXECUTOR] Found target function: %s\n", target_start);
            
            const char* state_data_str = "\"state_size\": ";
            char* size_start = strstr(json_buffer, state_data_str);
            if (size_start) {
                size_start += strlen(state_data_str);
                size_t state_size = strtoul(size_start, NULL, 10);
                printf("[C EXECUTOR] State size: %zu\n", state_size);
                
                typedef struct { int id; float value; char label[32]; } DemoState;
                DemoState state = { .id = 42, .value = 3.14f, .label = "INITIAL_STATE" };
                
                int result = swuir_warp_split(dormant_block_target, &state, sizeof(DemoState));
                if (result == 0) {
                    printf("[C EXECUTOR] Warp session spawned successfully\n");
                    printf("[C EXECUTOR] Main thread continuing...\n");
                    swuir_wait_all();
                    printf("[C EXECUTOR] All warp sessions completed\n");
                    printf("[C EXECUTOR] Main thread state: Value=%.2f, Label=%s\n", state.value, state.label);
                } else {
                    printf("[C EXECUTOR] Failed to spawn warp session\n");
                }
            }
        }
    }
    
    swuir_cleanup();
    free(json_buffer);
    swuir_il_module_destroy(module);
    
    return 0;
}