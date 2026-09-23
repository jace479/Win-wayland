#define _GNU_SOURCE
#include <dlfcn.h>
#include <xcb/xcb.h>
#include <X11/Xlib.h>
#include <X11/Xatom.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>

static pthread_mutex_t g_lock = PTHREAD_MUTEX_INITIALIZER;

/* Function pointers for XCB */
static xcb_void_cookie_t (*real_xcb_change_property)(
    xcb_connection_t *c, uint8_t mode, xcb_window_t window,
    xcb_atom_t property, xcb_atom_t type, uint8_t format,
    uint32_t data_len, const void *data) = NULL;

static xcb_void_cookie_t (*real_xcb_change_property_checked)(
    xcb_connection_t *c, uint8_t mode, xcb_window_t window,
    xcb_atom_t property, xcb_atom_t type, uint8_t format,
    uint32_t data_len, const void *data) = NULL;

static xcb_void_cookie_t (*real_xcb_change_window_attributes)(
    xcb_connection_t *c, xcb_window_t window,
    uint32_t value_mask, const void *value_list) = NULL;

/* Function pointers for Xlib */
static int (*real_XChangeProperty)(
    Display *display, Window w, Atom property, Atom type,
    int format, int mode, const unsigned char *data, int nelements) = NULL;

/* Known atoms */
static xcb_atom_t atom_net_wm_window_type = 0;
static xcb_atom_t atom_kde_applet_popup = 0;
static xcb_atom_t atom_kde_override = 0;
static xcb_atom_t atom_dock = 0;
static xcb_atom_t atom_popup_menu = 0;
static int g_atoms_init = 0;

static xcb_atom_t get_atom(xcb_connection_t *c, const char *name) {
    xcb_intern_atom_cookie_t cookie = xcb_intern_atom(c, 0, (uint16_t)strlen(name), name);
    xcb_intern_atom_reply_t *reply = xcb_intern_atom_reply(c, cookie, NULL);
    xcb_atom_t a = reply ? reply->atom : 0;
    free(reply);
    return a;
}

static void init_xcb_atoms(xcb_connection_t *c) {
    if (g_atoms_init || !c) return;
    g_atoms_init = 1;
    atom_net_wm_window_type = get_atom(c, "_NET_WM_WINDOW_TYPE");
    atom_kde_applet_popup = get_atom(c, "_KDE_NET_WM_WINDOW_TYPE_APPLET_POPUP");
    atom_kde_override = get_atom(c, "_KDE_NET_WM_WINDOW_TYPE_OVERRIDE");
    atom_dock = get_atom(c, "_NET_WM_WINDOW_TYPE_DOCK");
    atom_popup_menu = get_atom(c, "_NET_WM_WINDOW_TYPE_POPUP_MENU");
}

static void handle_window_type_xcb(xcb_connection_t *c, xcb_window_t window,
                                   xcb_atom_t property, uint32_t data_len,
                                   const void *data) {
    if (!c || !data || data_len == 0) return;

    if (!real_xcb_change_window_attributes) {
        real_xcb_change_window_attributes = dlsym(RTLD_NEXT, "xcb_change_window_attributes");
    }

    init_xcb_atoms(c);

    if (property != atom_net_wm_window_type) return;

    const xcb_atom_t *atoms = (const xcb_atom_t *)data;
    int is_popup = 0;

    for (uint32_t i = 0; i < data_len; i++) {
        if (atoms[i] == atom_kde_applet_popup || atoms[i] == atom_kde_override) {
            is_popup = 1;
            break;
        }
    }

    if (is_popup) {
        if (real_xcb_change_window_attributes) {
            uint32_t val[1] = { 1 };
            real_xcb_change_window_attributes(c, window, XCB_CW_OVERRIDE_REDIRECT, val);
            fprintf(stderr, "[ntkde-popup-fix] Enforced override_redirect=1 on applet popup window 0x%x\n",
                    (unsigned int)window);
        }
    }
}

/* Intercept xcb_change_property */
xcb_void_cookie_t xcb_change_property(
    xcb_connection_t *c, uint8_t mode, xcb_window_t window,
    xcb_atom_t property, xcb_atom_t type, uint8_t format,
    uint32_t data_len, const void *data)
{
    if (!real_xcb_change_property) {
        pthread_mutex_lock(&g_lock);
        if (!real_xcb_change_property) {
            real_xcb_change_property = dlsym(RTLD_NEXT, "xcb_change_property");
        }
        pthread_mutex_unlock(&g_lock);
    }

    handle_window_type_xcb(c, window, property, data_len, data);

    return real_xcb_change_property(c, mode, window, property, type, format, data_len, data);
}

/* Intercept xcb_change_property_checked */
xcb_void_cookie_t xcb_change_property_checked(
    xcb_connection_t *c, uint8_t mode, xcb_window_t window,
    xcb_atom_t property, xcb_atom_t type, uint8_t format,
    uint32_t data_len, const void *data)
{
    if (!real_xcb_change_property_checked) {
        pthread_mutex_lock(&g_lock);
        if (!real_xcb_change_property_checked) {
            real_xcb_change_property_checked = dlsym(RTLD_NEXT, "xcb_change_property_checked");
        }
        pthread_mutex_unlock(&g_lock);
    }

    handle_window_type_xcb(c, window, property, data_len, data);

    return real_xcb_change_property_checked(c, mode, window, property, type, format, data_len, data);
}

/* Intercept Xlib XChangeProperty */
int XChangeProperty(Display *display, Window w, Atom property, Atom type,
                    int format, int mode, const unsigned char *data, int nelements)
{
    if (!real_XChangeProperty) {
        pthread_mutex_lock(&g_lock);
        if (!real_XChangeProperty) {
            real_XChangeProperty = dlsym(RTLD_NEXT, "XChangeProperty");
        }
        pthread_mutex_unlock(&g_lock);
    }

    if (display && data && nelements > 0 && format == 32) {
        Atom a_type = XInternAtom(display, "_NET_WM_WINDOW_TYPE", False);
        if (property == a_type) {
            Atom a_popup = XInternAtom(display, "_KDE_NET_WM_WINDOW_TYPE_APPLET_POPUP", False);
            Atom a_override = XInternAtom(display, "_KDE_NET_WM_WINDOW_TYPE_OVERRIDE", False);
            const Atom *atoms = (const Atom *)data;
            for (int i = 0; i < nelements; i++) {
                if (atoms[i] == a_popup || atoms[i] == a_override) {
                    XSetWindowAttributes attrs;
                    attrs.override_redirect = True;
                    XChangeWindowAttributes(display, w, CWOverrideRedirect, &attrs);
                    fprintf(stderr, "[ntkde-popup-fix] (Xlib) Enforced override_redirect=True on applet popup window 0x%lx\n", (unsigned long)w);
                    break;
                }
            }
        }
    }

    return real_XChangeProperty(display, w, property, type, format, mode, data, nelements);
}
