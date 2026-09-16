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

void c_final_warp_target(void* state_ptr) {
    DemoState* state = (DemoState*)state_ptr;
    char original_label[32];
    strncpy(original_label, state->label, sizeof(original_label));
    
    printf("[C FINAL] Warp session executing c_final_warp_target\n");
    printf("[C FINAL]   Inherited state: ID=%d, Value=%.2f, Label=%s\n", 
           state->id, state->value, state->label);
    printf("[C FINAL] Modifying state in C final warp...\n");
    state->value += 1.0f;
    snprintf(state->label, sizeof(state->label), "C_FINAL_%s", original_label);
    printf("[C FINAL] State after C final warp: Value=%.2f, Label=%s\n", 
           state->value, state->label);
}

int main(int argc, char** argv) {
    if (argc < 3) {
        fprintf(stderr, "Usage: %s <json_file> <state_file>\n", argv[0]);
        return 1;
    }
    
    void* state_buffer = NULL;
    size_t state_size = read_file(argv[2], &state_buffer);
    if (state_size == 0 || state_size != sizeof(DemoState)) {
        fprintf(stderr, "Failed to read state binary (size=%zu, expected=%zu)\n", state_size, sizeof(DemoState));
        return 1;
    }
    
    printf("[C FINAL] Loaded state binary (%zu bytes)\n", state_size);
    
    DemoState* state = (DemoState*)state_buffer;
    printf("[C FINAL] Parsed state: ID=%d, Value=%.2f, Label=%s\n", 
           state->id, state->value, state->label);
    
    swuir_init();
    
    int result = swuir_warp_split(c_final_warp_target, state, sizeof(DemoState));
    if (result == 0) {
        printf("[C FINAL] Warp session spawned successfully\n");
        printf("[C FINAL] Main thread continuing...\n");
        swuir_wait_all();
        printf("[C FINAL] All warp sessions completed\n");
        printf("[C FINAL] Main thread state unchanged: Value=%.2f, Label=%s\n", 
               state->value, state->label);
    } else {
        printf("[C FINAL] Failed to spawn warp session\n");
    }
    
    swuir_cleanup();
    free(state_buffer);
    
    return 0;
}