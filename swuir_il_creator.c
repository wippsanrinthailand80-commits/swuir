#include "swuir.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>

static uint64_t generate_session_id(void) {
    return ((uint64_t)time(NULL) << 32) | (uint64_t)rand();
}

int main(int argc, char** argv) {
    if (argc < 3) {
        fprintf(stderr, "Usage: %s <json_file> <state_file>\n", argv[0]);
        return 1;
    }
    
    DemoState state = { .id = 42, .value = 3.14f, .label = "INITIAL_STATE" };
    uint64_t session_id = generate_session_id();
    
    FILE* json_f = fopen(argv[1], "w");
    if (!json_f) { perror("json"); return 1; }
    
    fprintf(json_f, "{\n");
    fprintf(json_f, "  \"version\": 1,\n");
    fprintf(json_f, "  \"magic\": \"0x53575549\",\n");
    fprintf(json_f, "  \"module\": \"multi_lang_demo\",\n");
    fprintf(json_f, "  \"types\": [\n");
    fprintf(json_f, "    {\n");
    fprintf(json_f, "      \"name\": \"DemoState\",\n");
    fprintf(json_f, "      \"size\": 40,\n");
    fprintf(json_f, "      \"fields\": [\n");
    fprintf(json_f, "        {\"name\": \"id\", \"type\": \"i32\", \"offset\": 0, \"array_len\": 0},\n");
    fprintf(json_f, "        {\"name\": \"value\", \"type\": \"f32\", \"offset\": 4, \"array_len\": 0},\n");
    fprintf(json_f, "        {\"name\": \"label\", \"type\": \"string\", \"offset\": 8, \"array_len\": 32}\n");
    fprintf(json_f, "      ]\n");
    fprintf(json_f, "    }\n");
    fprintf(json_f, "  ],\n");
    fprintf(json_f, "  \"sessions\": [\n");
    fprintf(json_f, "    {\n");
    fprintf(json_f, "      \"session_id\": \"%016lX\",\n", (unsigned long)session_id);
    fprintf(json_f, "      \"target\": \"dormant_block_target\",\n");
    fprintf(json_f, "      \"state_type\": \"DemoState\",\n");
    fprintf(json_f, "      \"state_size\": 40,\n");
    fprintf(json_f, "      \"status\": 0\n");
    fprintf(json_f, "    }\n");
    fprintf(json_f, "  ],\n");
    fprintf(json_f, "  \"pool_used\": 0\n");
    fprintf(json_f, "}\n");
    fclose(json_f);
    
    FILE* state_f = fopen(argv[2], "wb");
    if (!state_f) { perror("state"); return 1; }
    fwrite(&state, sizeof(DemoState), 1, state_f);
    fclose(state_f);
    
    printf("[C CREATOR] Created IL JSON: %s\n", argv[1]);
    printf("[C CREATOR] Created state binary: %s\n", argv[2]);
    printf("[C CREATOR] Initial state: ID=%d, Value=%.2f, Label=%s\n", state.id, state.value, state.label);
    printf("[C CREATOR] Session ID: %016lX\n", (unsigned long)session_id);
    
    return 0;
}