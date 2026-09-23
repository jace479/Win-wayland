#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <unistd.h>

#include <wayland-server-core.h>
#include <wayland-client-core.h>
#include <wayland-client-protocol.h>

#include "build/generated/nt-plasma-foreign-surface-client-protocol.h"
#include "build/generated/nt-plasma-foreign-surface-server-protocol.h"

struct smoke_state {
    int metadata_seen;
    int frame_seen;
};

static void surface_set_metadata(struct wl_client *client,
                                 struct wl_resource *resource,
                                 const char *application_id,
                                 const char *title,
                                 uint32_t width,
                                 uint32_t height,
                                 uint32_t monitor)
{
    struct smoke_state *state = wl_resource_get_user_data(resource);
    (void)client;
    (void)application_id;
    (void)title;
    (void)width;
    (void)height;
    (void)monitor;
    state->metadata_seen = 1;
}

static void surface_attach_frame(struct wl_client *client,
                                 struct wl_resource *resource,
                                 struct wl_resource *buffer,
                                 uint32_t width,
                                 uint32_t height,
                                 uint32_t sequence)
{
    (void)client;
    (void)resource;
    struct smoke_state *state = wl_resource_get_user_data(resource);
    if (buffer != NULL && width == 2 && height == 2 && sequence == 1) {
        state->frame_seen = 1;
        wl_display_terminate(wl_client_get_display(client));
        wl_display_terminate(wl_client_get_display(client));
    }
}

static void surface_set_state(struct wl_client *client,
                              struct wl_resource *resource,
                              uint32_t state)
{
    (void)client;
    (void)resource;
    (void)state;
}

static const struct nt_plasma_foreign_surface_v1_interface surface_impl = {
    .set_metadata = surface_set_metadata,
    .attach_frame = surface_attach_frame,
    .set_state = surface_set_state,
};

static void manager_create_surface(struct wl_client *client,
                                   struct wl_resource *resource,
                                   uint32_t id,
                                   const char *window_id)
{
    struct smoke_state *state = wl_resource_get_user_data(resource);
    struct wl_resource *surface;
    (void)window_id;
    surface = wl_resource_create(client,
                                 &nt_plasma_foreign_surface_v1_interface,
                                 1,
                                 id);
    if (surface == NULL) {
        wl_client_post_no_memory(client);
        return;
    }
    wl_resource_set_implementation(surface, &surface_impl, state, NULL);
}

static const struct nt_plasma_foreign_surface_manager_v1_interface manager_impl = {
    .create_surface = manager_create_surface,
};

static void bind_manager(struct wl_client *client,
                         void *data,
                         uint32_t version,
                         uint32_t id)
{
    struct wl_resource *resource;
    (void)version;
    resource = wl_resource_create(client,
                                  &nt_plasma_foreign_surface_manager_v1_interface,
                                  1,
                                  id);
    if (resource == NULL) {
        wl_client_post_no_memory(client);
        return;
    }
    wl_resource_set_implementation(resource, &manager_impl, data, NULL);
}

struct client_state {
    struct nt_plasma_foreign_surface_manager_v1 *manager;
    struct wl_shm *shm;
};

static void registry_global(void *data,
                            struct wl_registry *registry,
                            uint32_t name,
                            const char *interface,
                            uint32_t version)
{
    struct client_state *state = data;
    if (strcmp(interface, "nt_plasma_foreign_surface_manager_v1") == 0) {
        state->manager = wl_registry_bind(registry,
                                          name,
                                          &nt_plasma_foreign_surface_manager_v1_interface,
                                          version < 1 ? version : 1);
    } else if (strcmp(interface, "wl_shm") == 0) {
        state->shm = wl_registry_bind(registry, name, &wl_shm_interface, 1);
    }
}

static void registry_global_remove(void *data,
                                   struct wl_registry *registry,
                                   uint32_t name)
{
    (void)data;
    (void)registry;
    (void)name;
}

static const struct wl_registry_listener registry_listener = {
    .global = registry_global,
    .global_remove = registry_global_remove,
};

static int run_client(const char *socket_name)
{
    struct wl_display *display = wl_display_connect(socket_name);
    struct wl_registry *registry;
    struct client_state state = {0};
    struct nt_plasma_foreign_surface_v1 *surface;
    struct wl_shm_pool *pool;
    struct wl_buffer *buffer;
    int shm_fd;
    void *pixels;
    const int width = 2;
    const int height = 2;
    const int stride = width * 4;
    const int size = stride * height;
    char shm_name[64];

    if (display == NULL) {
        perror("wl_display_connect");
        return EXIT_FAILURE;
    }
    registry = wl_display_get_registry(display);
    wl_registry_add_listener(registry, &registry_listener, &state);
    if (wl_display_roundtrip(display) < 0) {
        fputs("registry roundtrip failed\n", stderr);
        wl_display_disconnect(display);
        return EXIT_FAILURE;
    }
    if (state.manager == NULL) {
        fputs("foreign-surface manager was not advertised\n", stderr);
        wl_display_disconnect(display);
        return EXIT_FAILURE;
    }
    if (state.shm == NULL) {
        fputs("wl_shm was not advertised\n", stderr);
        wl_display_disconnect(display);
        return EXIT_FAILURE;
    }
    surface = nt_plasma_foreign_surface_manager_v1_create_surface(state.manager, "synthetic-window");
    nt_plasma_foreign_surface_v1_set_metadata(surface, "windows:smoke", "Synthetic Window", 320, 200, 1);
    if (wl_display_roundtrip(display) < 0) {
        fputs("metadata request failed\n", stderr);
        wl_display_disconnect(display);
        return EXIT_FAILURE;
    }
    snprintf(shm_name, sizeof(shm_name), "/ntkde-smoke-%ld", (long)getpid());
    shm_fd = shm_open(shm_name, O_CREAT | O_EXCL | O_RDWR, 0600);
    if (shm_fd < 0 || ftruncate(shm_fd, size) != 0) {
        perror("create shm buffer");
        return EXIT_FAILURE;
    }
    shm_unlink(shm_name);
    pixels = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_SHARED, shm_fd, 0);
    if (pixels == MAP_FAILED) {
        perror("map shm buffer");
        close(shm_fd);
        return EXIT_FAILURE;
    }
    memset(pixels, 0x7f, size);
    pool = wl_shm_create_pool(state.shm, shm_fd, size);
    buffer = wl_shm_pool_create_buffer(pool, 0, width, height, stride, WL_SHM_FORMAT_XRGB8888);
    nt_plasma_foreign_surface_v1_attach_frame(surface, buffer, width, height, 1);
    if (wl_display_flush(display) < 0) {
        fputs("frame request flush failed\n", stderr);
        return EXIT_FAILURE;
    }
    sleep(1);
    wl_buffer_destroy(buffer);
    wl_shm_pool_destroy(pool);
    munmap(pixels, size);
    close(shm_fd);
    wl_display_disconnect(display);
    return EXIT_SUCCESS;
}

int main(void)
{
    struct smoke_state state = {0};
    struct wl_display *display;
    const char *socket_name;
    char runtime_dir[64];
    pid_t child;
    int status;

    snprintf(runtime_dir, sizeof(runtime_dir), "/tmp/nt-plasma-runtime-%ld", (long)getpid());
    if (mkdir(runtime_dir, 0700) != 0 || setenv("XDG_RUNTIME_DIR", runtime_dir, 1) != 0) {
        perror("create smoke runtime directory");
        return EXIT_FAILURE;
    }
    display = wl_display_create();
    if (display == NULL) {
        fputs("wl_display_create failed\n", stderr);
        return EXIT_FAILURE;
    }
    if (wl_display_init_shm(display) != 0) {
        fputs("wl_display_init_shm failed\n", stderr);
        wl_display_destroy(display);
        return EXIT_FAILURE;
    }
    socket_name = wl_display_add_socket_auto(display);
    if (socket_name == NULL) {
        fputs("wl_display_add_socket_auto failed\n", stderr);
        wl_display_destroy(display);
        return EXIT_FAILURE;
    }
    if (wl_global_create(display,
                         &nt_plasma_foreign_surface_manager_v1_interface,
                         1,
                         &state,
                         bind_manager) == NULL) {
        fputs("wl_global_create failed\n", stderr);
        wl_display_destroy(display);
        return EXIT_FAILURE;
    }
    if (setenv("WAYLAND_DISPLAY", socket_name, 1) != 0) {
        perror("setenv");
        wl_display_destroy(display);
        return EXIT_FAILURE;
    }

    child = fork();
    if (child == 0) {
        _exit(run_client(socket_name));
    }
    if (child < 0) {
        perror("fork");
        wl_display_destroy(display);
        return EXIT_FAILURE;
    }
    sleep(1);
    wl_display_run(display);
    waitpid(child, &status, 0);
    wl_display_destroy_clients(display);
    wl_display_destroy(display);
    if (!state.metadata_seen || !state.frame_seen || !WIFEXITED(status) || WEXITSTATUS(status) != 0) {
        fputs("native protocol smoke test failed\n", stderr);
        return EXIT_FAILURE;
    }
    puts("native protocol smoke test passed");
    return EXIT_SUCCESS;
}