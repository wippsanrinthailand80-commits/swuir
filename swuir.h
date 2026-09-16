#ifndef SWUIR_H
#define SWUIR_H

#include <stddef.h>
#include <stdint.h>

#define SWUIR_POOL_SIZE (512 * 1024 * 1024)
#define MAX_SESSIONS 64

typedef enum {
    SWUIR_SESSION_IDLE = 0,
    SWUIR_SESSION_ACTIVE,
    SWUIR_SESSION_COMPLETED,
    SWUIR_SESSION_ERROR
} SwuirSessionStatus;

typedef struct {
    void (*target_func)(void*);
    void* pinned_state;
    size_t state_size;
    SwuirSessionStatus status;
    void* thread_id;
} WarpSession;

typedef struct {
    uint8_t pool[SWUIR_POOL_SIZE];
    size_t used;
    WarpSession sessions[MAX_SESSIONS];
    size_t session_count;
    void* mutex;
} SwuirMemoryPool;

void swuir_init(void);
void* swuir_pin_state(void* data, size_t size);
int swuir_warp_split(void (*target_func)(void*), void* state, size_t state_size);
void swuir_wait_all(void);
void swuir_cleanup(void);

typedef struct { int id; float value; char label[32]; } DemoState;
void dormant_block_target(void* state_ptr);

#endif