#include "swuir.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

static size_t read_file(const char* path, void** out_buffer) {
    FILE* f = fopen(path, "rb");
    if (!f) return 0;
    fseek(f, 0, SEEK_END);
    size_t size = ftell(f);
    fseek(f, 0, SEEK_SET);
    *out_buffer = malloc(size);
    fread(*out_buffer, 1, size, f);
    fclose(f);
    return size;
}

static char* extract_json_string(const char* json, const char* key, char* out, size_t out_size) {
    char search_key[128];
    snprintf(search_key, sizeof(search_key), "\"%s\": \"", key);
    
    char* start = strstr(json, search_key);
    if (!start) return NULL;
    start += strlen(search_key);
    char* end = strchr(start, '"');
    if (!end) return NULL;
    
    size_t len = end - start;
    if (len >= out_size) len = out_size - 1;
    memcpy(out, start, len);
    out[len] = '\0';
    return out;
}

int main(int argc, char** argv) {
    if (argc < 3) {
        fprintf(stderr, "Usage: %s <il_json_file> <state_binary_file>\n", argv[0]);
        return 1;
    }
    
    char* json_buffer = NULL;
    size_t json_size = read_file(argv[1], (void**)&json_buffer);
    if (json_size == 0) {
        fprintf(stderr, "Failed to read JSON file\n");
        return 1;
    }
    
    void* state_buffer = NULL;
    size_t state_size = read_file(argv[2], &state_buffer);
    if (state_size == 0 || state_size != sizeof(DemoState)) {
        fprintf(stderr, "Failed to read state binary (size=%zu, expected=%zu)\n", state_size, sizeof(DemoState));
        free(json_buffer);
        return 1;
    }
    
    printf("[C EXECUTOR] Loaded JSON (%zu bytes)\n", json_size);
    printf("[C EXECUTOR] Loaded state binary (%zu bytes)\n", state_size);
    
    char target_func[64];
    if (!extract_json_string(json_buffer, "target", target_func, sizeof(target_func))) {
        fprintf(stderr, "Failed to extract target function from JSON\n");
        free(json_buffer);
        free(state_buffer);
        return 1;
    }
    
    printf("[C EXECUTOR] Target function: %s\n", target_func);
    printf("[C EXECUTOR] State data: ");
    uint8_t* bytes = (uint8_t*)state_buffer;
    for (size_t i = 0; i < state_size; i++) printf("%02x", bytes[i]);
    printf("\n");
    
    swuir_init();
    
    DemoState* state = (DemoState*)state_buffer;
    printf("[C EXECUTOR] Parsed state: ID=%d, Value=%.2f, Label=%s\n", 
           state->id, state->value, state->label);
    
    int result = swuir_warp_split(dormant_block_target, state, sizeof(DemoState));
    if (result == 0) {
        printf("[C EXECUTOR] Warp session spawned successfully\n");
        printf("[C EXECUTOR] Main thread continuing...\n");
        swuir_wait_all();
        printf("[C EXECUTOR] All warp sessions completed\n");
        printf("[C EXECUTOR] Main thread state unchanged: Value=%.2f, Label=%s\n", 
               state->value, state->label);
    } else {
        printf("[C EXECUTOR] Failed to spawn warp session\n");
    }
    
    swuir_cleanup();
    free(json_buffer);
    free(state_buffer);
    
    return 0;
}