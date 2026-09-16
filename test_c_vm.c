#include "swuir_vm.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <jansson.h>

int main(int argc, char** argv) {
    if (argc < 2) { fprintf(stderr, "Usage: %s <json_file>\n", argv[0]); return 1; }
    FILE* f = fopen(argv[1], "r"); if (!f) { perror("fopen"); return 1; }
    fseek(f, 0, SEEK_END); long sz = ftell(f); fseek(f, 0, SEEK_SET);
    char* json = malloc(sz + 1); fread(json, 1, sz, f); json[sz] = 0; fclose(f);
    fprintf(stderr, "[DEBUG] JSON loaded, size=%ld\n", sz);
    json_error_t err; json_t* root = json_loads(json, 0, &err); free(json);
    if (!root) { fprintf(stderr, "JSON parse error: %s\n", err.text); return 1; }
    fprintf(stderr, "[DEBUG] JSON parsed\n");
    json_t* bc = json_object_get(root, "bytecode"); json_t* sz_j = json_object_get(root, "size");
    if (!bc) { fprintf(stderr, "Missing bytecode field\n"); json_decref(root); return 1; }
    if (!sz_j) { fprintf(stderr, "Missing size field\n"); json_decref(root); return 1; }
    const char* hex = json_string_value(bc); size_t size = json_integer_value(sz_j);
    fprintf(stderr, "[DEBUG] bytecode hex len=%zu, size=%zu\n", strlen(hex), size);
    size_t bin = strlen(hex) / 2; uint8_t* code = malloc(bin);
    for (size_t i = 0; i < bin; i++) sscanf(hex + i*2, "%2hhx", &code[i]);
    fprintf(stderr, "[DEBUG] bytecode decoded, bin_size=%zu\n", bin);
    VMContext* vm = vm_create(code, bin); 
    if (!vm) { fprintf(stderr, "vm_create failed\n"); free(code); json_decref(root); return 1; }
    int r = vm_execute(vm);
    printf("\n[C VM] %s\n", r ? "executed successfully" : "error");
    if (!r) printf("[C VM] Error: %s\n", vm->error_msg);
    vm_destroy(vm); free(code); json_decref(root); return r ? 0 : 1;
}
