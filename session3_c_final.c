#include "swuir.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

static size_t read_file(const char* path, void** out) {
    FILE* f = fopen(path, "rb");
    if (!f) return 0;
    fseek(f, 0, SEEK_END);
    size_t sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    *out = malloc(sz);
    fread(*out, 1, sz, f);
    fclose(f);
    return sz;
}

void c_final_warp(void* p) {
    DemoState* s = (DemoState*)p;
    char orig[32];
    strncpy(orig, s->label, sizeof(orig));
    printf("[C Session] Warp executing c_final_warp\n");
    printf("[C Session]   Inherited: ID=%d, Value=%.2f, Label=%s\n", s->id, s->value, s->label);
    s->value += 1.0f;
    snprintf(s->label, sizeof(s->label), "C_FINAL_%s", orig);
    printf("[C Session] After warp: Value=%.2f, Label=%s\n", s->value, s->label);
}

int main(int argc, char** argv) {
    const char* state_file = argc > 1 ? argv[1] : "/tmp/swuir_session_state_rust.bin";
    
    printf("[C Session] Reading state from %s\n", state_file);
    
    void* buf = NULL;
    size_t sz = read_file(state_file, &buf);
    if (sz != sizeof(DemoState)) {
        fprintf(stderr, "[C Session] Invalid state size: %zu\n", sz);
        return 1;
    }
    
    DemoState* state = (DemoState*)buf;
    printf("[C Session] Parsed: ID=%d, Value=%.2f, Label=%s\n", 
           state->id, state->value, state->label);
    
    swuir_init();
    int r = swuir_warp_split(c_final_warp, state, sizeof(DemoState));
    if (r == 0) {
        printf("[C Session] Warp spawned\n");
        swuir_wait_all();
        printf("[C Session] Completed\n");
    }
    swuir_cleanup();
    free(buf);
    return 0;
}