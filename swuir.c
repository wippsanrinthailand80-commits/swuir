#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
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
    pthread_t thread_id;
} WarpSession;

typedef struct {
    uint8_t pool[SWUIR_POOL_SIZE];
    size_t used;
    WarpSession sessions[MAX_SESSIONS];
    size_t session_count;
    pthread_mutex_t mutex;
} SwuirMemoryPool;

static SwuirMemoryPool g_pool = {0};

void swuir_init(void) {
    g_pool.used = 0;
    g_pool.session_count = 0;
    pthread_mutex_init(&g_pool.mutex, NULL);
    memset(g_pool.sessions, 0, sizeof(g_pool.sessions));
}

void* swuir_pin_state(void* data, size_t size) {
    if (g_pool.used + size > SWUIR_POOL_SIZE) {
        return NULL;
    }
    
    void* dest = &g_pool.pool[g_pool.used];
    memcpy(dest, data, size);
    g_pool.used += size;
    
    return dest;
}

static void* warp_session_runner(void* arg) {
    WarpSession* session = (WarpSession*)arg;
    session->status = SWUIR_SESSION_ACTIVE;
    
    if (session->target_func && session->pinned_state) {
        session->target_func(session->pinned_state);
    }
    
    session->status = SWUIR_SESSION_COMPLETED;
    return NULL;
}

int swuir_warp_split(void (*target_func)(void*), void* state, size_t state_size) {
    pthread_mutex_lock(&g_pool.mutex);
    
    if (g_pool.session_count >= MAX_SESSIONS) {
        pthread_mutex_unlock(&g_pool.mutex);
        return -1;
    }
    
    void* pinned = swuir_pin_state(state, state_size);
    if (!pinned) {
        pthread_mutex_unlock(&g_pool.mutex);
        return -1;
    }
    
    WarpSession* session = &g_pool.sessions[g_pool.session_count];
    session->target_func = target_func;
    session->pinned_state = pinned;
    session->state_size = state_size;
    session->status = SWUIR_SESSION_IDLE;
    session->thread_id = 0;
    
    int result = pthread_create(&session->thread_id, NULL, warp_session_runner, session);
    if (result != 0) {
        pthread_mutex_unlock(&g_pool.mutex);
        return -1;
    }
    
    g_pool.session_count++;
    pthread_mutex_unlock(&g_pool.mutex);
    return 0;
}

void swuir_wait_all(void) {
    for (size_t i = 0; i < g_pool.session_count; i++) {
        WarpSession* session = &g_pool.sessions[i];
        if (session->thread_id != 0) {
            pthread_join(session->thread_id, NULL);
            session->thread_id = 0;
        }
    }
}

void swuir_cleanup(void) {
    swuir_wait_all();
    pthread_mutex_destroy(&g_pool.mutex);
}

typedef struct {
    int id;
    float value;
    char label[32];
} DemoState;

void dormant_block_target(void* state_ptr) {
    DemoState* state = (DemoState*)state_ptr;
    char original_label[32];
    strncpy(original_label, state->label, sizeof(original_label));
    
    printf("[WARP SESSION] Executing dormant block with inherited state:\n");
    printf("[WARP SESSION]   ID: %d, Value: %.2f, Label: %s\n", state->id, state->value, state->label);
    printf("[WARP SESSION] Modifying state in warp session...\n");
    state->value *= 2.0f;
    snprintf(state->label, sizeof(state->label), "WARPED_%s", original_label);
    printf("[WARP SESSION] State after modification: Value=%.2f, Label=%s\n", state->value, state->label);
}

#ifndef SWUIR_LIB
int main(void) {
    setbuf(stdout, NULL);
    swuir_init();
    
    DemoState initial_state = {
        .id = 42,
        .value = 3.14f,
        .label = "INITIAL_STATE"
    };
    
    printf("[MAIN] Initial state loaded: ID=%d, Value=%.2f, Label=%s\n", 
           initial_state.id, initial_state.value, initial_state.label);
    
    printf("[MAIN] Calling swuir_warp_split()...\n");
    printf("[MAIN] Main thread continues to next line (N+1)...\n");
    
    int result = swuir_warp_split(dormant_block_target, &initial_state, sizeof(DemoState));
    if (result != 0) {
        fprintf(stderr, "[MAIN] Failed to create warp session\n");
        return 1;
    }
    
    printf("[MAIN] Main flow continuing seamlessly after warp_split()\n");
    printf("[MAIN] Main thread state unchanged: Value=%.2f, Label=%s\n", 
           initial_state.value, initial_state.label);
    
    swuir_wait_all();
    
    printf("[MAIN] All warp sessions completed.\n");
    printf("[MAIN] Final state in main: Value=%.2f, Label=%s\n", 
           initial_state.value, initial_state.label);
    
    swuir_cleanup();
    return 0;
}
#endif