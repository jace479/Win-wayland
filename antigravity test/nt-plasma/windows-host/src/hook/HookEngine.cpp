#include "HookEngine.hpp"
#include <QDebug>
#include <QGuiApplication>
#include <vector>
#include <array>

namespace KWinWin::Hook {

HookEngine* HookEngine::s_instance = nullptr;

HookEngine::HookEngine(QObject* parent)
    : QObject(parent)
{
    s_instance = this;
}

HookEngine::~HookEngine()
{
    stop();
    if (s_instance == this) {
        s_instance = nullptr;
    }
}

bool HookEngine::start()
{
    if (m_isRunning) {
        return true;
    }

    DWORD processId = 0; // Global hook for all processes
    DWORD threadId = 0;
    DWORD flags = WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS;

    m_hookCreateDestroy = SetWinEventHook(
        EVENT_OBJECT_CREATE, EVENT_OBJECT_DESTROY,
        nullptr, winEventProc, processId, threadId, flags
    );

    m_hookShowHide = SetWinEventHook(
        EVENT_OBJECT_SHOW, EVENT_OBJECT_HIDE,
        nullptr, winEventProc, processId, threadId, flags
    );

    m_hookForeground = SetWinEventHook(
        EVENT_SYSTEM_FOREGROUND, EVENT_SYSTEM_FOREGROUND,
        nullptr, winEventProc, processId, threadId, flags
    );

    m_hookMoveSize = SetWinEventHook(
        EVENT_SYSTEM_MOVESIZEEND, EVENT_SYSTEM_MOVESIZEEND,
        nullptr, winEventProc, processId, threadId, flags
    );

    if (!m_hookCreateDestroy || !m_hookForeground || !m_hookMoveSize) {
        qWarning() << "[HookEngine] Failed to install one or more WinEvent hooks.";
        stop();
        return false;
    }

    m_isRunning = true;
    qInfo() << "[HookEngine] WinEvent hooks successfully installed.";

    // Manage existing top-level windows already on the desktop
    EnumWindows([](HWND hwnd, LPARAM lParam) -> BOOL {
        auto* self = reinterpret_cast<HookEngine*>(lParam);
        if (self && HookEngine::isManageable(hwnd)) {
            self->manageWindow(hwnd);
        }
        return TRUE;
    }, reinterpret_cast<LPARAM>(this));

    m_foregroundHwnd = GetForegroundWindow();
    if (m_foregroundHwnd && isManageable(m_foregroundHwnd)) {
        emit windowActivated(reinterpret_cast<qintptr>(m_foregroundHwnd));
    }

    return true;
}

void HookEngine::stop()
{
    if (!m_isRunning) {
        return;
    }

    if (m_hookCreateDestroy) {
        UnhookWinEvent(m_hookCreateDestroy);
        m_hookCreateDestroy = nullptr;
    }
    if (m_hookShowHide) {
        UnhookWinEvent(m_hookShowHide);
        m_hookShowHide = nullptr;
    }
    if (m_hookForeground) {
        UnhookWinEvent(m_hookForeground);
        m_hookForeground = nullptr;
    }
    if (m_hookMoveSize) {
        UnhookWinEvent(m_hookMoveSize);
        m_hookMoveSize = nullptr;
    }

    restoreAllWindowDecorations();
    m_isRunning = false;
    qInfo() << "[HookEngine] WinEvent hooks uninstalled and window decorations restored.";
}

bool HookEngine::isWindowCloaked(HWND hwnd)
{
    int cloaked = 0;
    HRESULT hr = DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, &cloaked, sizeof(cloaked));
    if (SUCCEEDED(hr)) {
        return (cloaked != 0);
    }
    return false;
}

bool HookEngine::isManageable(HWND hwnd)
{
    if (!hwnd || !IsWindow(hwnd)) {
        return false;
    }

    // Skip windows belonging to our own shell process
    DWORD processId = 0;
    GetWindowThreadProcessId(hwnd, &processId);
    if (processId == GetCurrentProcessId()) {
        return false;
    }

    // Window must be a root top-level window
    if (GetAncestor(hwnd, GA_ROOT) != hwnd) {
        return false;
    }

    // Must be visible and not cloaked by DWM (e.g. suspended UWP apps or virtual desktops)
    if (!IsWindowVisible(hwnd) || isWindowCloaked(hwnd)) {
        return false;
    }

    // Check window styles
    LONG_PTR style = GetWindowLongPtrW(hwnd, GWL_STYLE);
    LONG_PTR exStyle = GetWindowLongPtrW(hwnd, GWL_EXSTYLE);

    if (style & WS_CHILD) {
        return false;
    }

    // Ignore tool windows unless explicitly marked as app windows
    if ((exStyle & WS_EX_TOOLWINDOW) && !(exStyle & WS_EX_APPWINDOW)) {
        return false;
    }

    // Filter out common system / shell classes
    std::array<wchar_t, 256> className{};
    if (GetClassNameW(hwnd, className.data(), static_cast<int>(className.size())) > 0) {
        std::wstring_view cls(className.data());
        if (cls == L"Progman" ||
            cls == L"WorkerW" ||
            cls == L"Shell_TrayWnd" ||
            cls == L"Shell_SecondaryTrayWnd" ||
            cls == L"#32768" || // Context Menus
            cls == L"tooltips_class32" ||
            cls == L"Internet Explorer_Hidden" ||
            cls == L"ApplicationFrameWindow_Host") {
            return false;
        }
    }

    // Ensure window has a valid non-empty title or standard window rect
    RECT rc;
    if (!GetWindowRect(hwnd, &rc) || (rc.right - rc.left <= 0) || (rc.bottom - rc.top <= 0)) {
        return false;
    }

    return true;
}

QRect HookEngine::getWindowExtendedBounds(HWND hwnd)
{
    if (!hwnd || !IsWindow(hwnd)) {
        return {};
    }

    RECT frameRect{};
    HRESULT hr = DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, &frameRect, sizeof(frameRect));
    if (FAILED(hr)) {
        GetWindowRect(hwnd, &frameRect);
    }

    return QRect(frameRect.left, frameRect.top,
                 frameRect.right - frameRect.left,
                 frameRect.bottom - frameRect.top);
}

QString HookEngine::getWindowTitle(HWND hwnd)
{
    if (!hwnd || !IsWindow(hwnd)) {
        return {};
    }

    int length = GetWindowTextLengthW(hwnd);
    if (length <= 0) {
        return {};
    }

    std::vector<wchar_t> buffer(length + 1);
    GetWindowTextW(hwnd, buffer.data(), length + 1);
    return QString::fromWCharArray(buffer.data());
}

bool HookEngine::manageWindow(HWND hwnd)
{
    if (!isManageable(hwnd)) {
        return false;
    }

    std::lock_guard<std::mutex> lock(m_stateMutex);

    if (m_trackedWindows.find(hwnd) != m_trackedWindows.end()) {
        return true; // Already tracked
    }

    WindowStyleSnapshot snapshot;
    snapshot.style = GetWindowLongPtrW(hwnd, GWL_STYLE);
    snapshot.exStyle = GetWindowLongPtrW(hwnd, GWL_EXSTYLE);
    GetWindowRect(hwnd, &snapshot.rect);
    snapshot.isDecorated = true;

    m_trackedWindows[hwnd] = snapshot;

    // Dynamically strip native OS window borders (WS_CAPTION and WS_THICKFRAME)
    LONG_PTR newStyle = snapshot.style;
    newStyle &= ~WS_CAPTION;
    newStyle &= ~WS_THICKFRAME;

    SetWindowLongPtrW(hwnd, GWL_STYLE, newStyle);

    // Force OS layout recomputation
    SetWindowPos(
        hwnd, nullptr, 0, 0, 0, 0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED
    );

    QString title = getWindowTitle(hwnd);
    QRect bounds = getWindowExtendedBounds(hwnd);

    emit windowCreated(reinterpret_cast<qintptr>(hwnd), title);
    emit windowGeometryChanged(reinterpret_cast<qintptr>(hwnd), bounds);

    return true;
}

bool HookEngine::unmanageWindow(HWND hwnd, bool restoreDecorations)
{
    std::lock_guard<std::mutex> lock(m_stateMutex);

    auto it = m_trackedWindows.find(hwnd);
    if (it == m_trackedWindows.end()) {
        return false;
    }

    if (restoreDecorations && IsWindow(hwnd)) {
        SetWindowLongPtrW(hwnd, GWL_STYLE, it->second.style);
        SetWindowLongPtrW(hwnd, GWL_EXSTYLE, it->second.exStyle);
        SetWindowPos(
            hwnd, nullptr, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED
        );
    }

    m_trackedWindows.erase(it);
    emit windowDestroyed(reinterpret_cast<qintptr>(hwnd));
    return true;
}

void HookEngine::restoreAllWindowDecorations()
{
    std::lock_guard<std::mutex> lock(m_stateMutex);

    for (const auto& [hwnd, snapshot] : m_trackedWindows) {
        if (IsWindow(hwnd)) {
            SetWindowLongPtrW(hwnd, GWL_STYLE, snapshot.style);
            SetWindowLongPtrW(hwnd, GWL_EXSTYLE, snapshot.exStyle);
            SetWindowPos(
                hwnd, nullptr, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED
            );
        }
    }
    m_trackedWindows.clear();
}

void HookEngine::activateWindow(qintptr hwndVal)
{
    HWND hwnd = reinterpret_cast<HWND>(hwndVal);
    if (!IsWindow(hwnd)) return;

    if (IsIconic(hwnd)) {
        ShowWindow(hwnd, SW_RESTORE);
    }
    SetForegroundWindow(hwnd);
    BringWindowToTop(hwnd);
}

void HookEngine::minimizeWindow(qintptr hwndVal)
{
    HWND hwnd = reinterpret_cast<HWND>(hwndVal);
    if (IsWindow(hwnd)) {
        ShowWindow(hwnd, SW_MINIMIZE);
    }
}

void HookEngine::maximizeWindow(qintptr hwndVal)
{
    HWND hwnd = reinterpret_cast<HWND>(hwndVal);
    if (IsWindow(hwnd)) {
        WINDOWPLACEMENT wp{};
        wp.length = sizeof(wp);
        GetWindowPlacement(hwnd, &wp);
        if (wp.showCmd == SW_SHOWMAXIMIZED) {
            ShowWindow(hwnd, SW_RESTORE);
        } else {
            ShowWindow(hwnd, SW_MAXIMIZE);
        }
    }
}

void HookEngine::restoreWindow(qintptr hwndVal)
{
    HWND hwnd = reinterpret_cast<HWND>(hwndVal);
    if (IsWindow(hwnd)) {
        ShowWindow(hwnd, SW_RESTORE);
    }
}

void HookEngine::closeWindow(qintptr hwndVal)
{
    HWND hwnd = reinterpret_cast<HWND>(hwndVal);
    if (IsWindow(hwnd)) {
        PostMessageW(hwnd, WM_CLOSE, 0, 0);
    }
}

void CALLBACK HookEngine::winEventProc(
    HWINEVENTHOOK /*hWinEventHook*/,
    DWORD event,
    HWND hwnd,
    LONG idObject,
    LONG idChild,
    DWORD /*idEventThread*/,
    DWORD /*dwmsEventTime*/)
{
    if (s_instance && idObject == OBJID_WINDOW) {
        s_instance->handleWinEvent(event, hwnd, idObject, idChild);
    }
}

void HookEngine::handleWinEvent(DWORD event, HWND hwnd, LONG /*idObject*/, LONG /*idChild*/)
{
    switch (event) {
    case EVENT_OBJECT_CREATE:
    case EVENT_OBJECT_SHOW: {
        QMetaObject::invokeMethod(this, [this, hwnd]() {
            if (isManageable(hwnd)) {
                manageWindow(hwnd);
                emit windowVisibilityChanged(reinterpret_cast<qintptr>(hwnd), true);
            }
        }, Qt::QueuedConnection);
        break;
    }
    case EVENT_OBJECT_DESTROY: {
        QMetaObject::invokeMethod(this, [this, hwnd]() {
            unmanageWindow(hwnd, false);
        }, Qt::QueuedConnection);
        break;
    }
    case EVENT_OBJECT_HIDE: {
        QMetaObject::invokeMethod(this, [this, hwnd]() {
            emit windowVisibilityChanged(reinterpret_cast<qintptr>(hwnd), false);
        }, Qt::QueuedConnection);
        break;
    }
    case EVENT_SYSTEM_FOREGROUND: {
        m_foregroundHwnd = hwnd;
        QMetaObject::invokeMethod(this, [this, hwnd]() {
            if (isManageable(hwnd)) {
                emit windowActivated(reinterpret_cast<qintptr>(hwnd));
            }
        }, Qt::QueuedConnection);
        break;
    }
    case EVENT_SYSTEM_MOVESIZEEND: {
        QMetaObject::invokeMethod(this, [this, hwnd]() {
            if (isManageable(hwnd)) {
                QRect bounds = getWindowExtendedBounds(hwnd);
                emit windowGeometryChanged(reinterpret_cast<qintptr>(hwnd), bounds);
            }
        }, Qt::QueuedConnection);
        break;
    }
    default:
        break;
    }
}

} // namespace KWinWin::Hook
