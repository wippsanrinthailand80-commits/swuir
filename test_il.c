#include "swuir_il.h"
#include <stdio.h>
#include <stdlib.h>

int main() {
    SwuirILModule* module = swuir_il_module_create("test", 1024);
    if (!module) {
        printf("Failed to create module\n");
        return 1;
    }
    
    printf("Module created\n");
    
    char* json = swuir_il_serialize_json(module);
    if (json) {
        printf("JSON:\n%s\n", json);
        free(json);
    } else {
        printf("Failed to serialize\n");
    }
    
    swuir_il_module_destroy(module);
    return 0;
}