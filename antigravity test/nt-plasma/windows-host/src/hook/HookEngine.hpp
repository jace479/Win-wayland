#pragma once

#include <QObject>
#include <QRect>
#include <QString>
#include <QHash>
#include <windows.h>
#include <dwmapi.h>
#include <unordered_map>
#include <mutex>

namespace KWinWin::Hook {

struct WindowStyleSnapshot {
    LONG_PTR style{ 0 };
    LONG_PTR exStyle{ 0 };
    RECT rect{ 0, 0, 0, 0 };
    bool isDecorated{ false };
};

class HookEngine : public QObject {
    Q_OBJECT

public:
    explicit HookEngine(QObject* parent = nullptr);
    ~HookEngine() override;

    bool start();
    void stop();
    bool isRunning() const { return m_isRunning; }

    // Window Management Actions
    bool manageWindow(HWND hwnd);
    bool unmanageWindow(HWND hwnd, bool restoreDecorations = true);
    void restoreAllWindowDecorations();

    // Geometric Tracking & Query
    static QRect getWindowExtendedBounds(HWND hwnd);
    static QString getWindowTitle(HWND hwnd);
    static bool isManageable(HWND hwnd);
    static bool isWindowCloaked(HWND hwnd);

    HWND foregroundWindow() const { return m_foregroundHwnd; }

signals:
    void windowCreated(qintptr hwnd, const QString& title);
    void windowDestroyed(qintptr hwnd);
    void windowActivated(qintptr hwnd);
    void windowGeometryChanged(qintptr hwnd, const QRect& bounds);
    void windowVisibilityChanged(qintptr hwnd, bool visible);

public slots:
    void activateWindow(qintptr hwnd);
    void minimizeWindow(qintptr hwnd);
    void maximizeWindow(qintptr hwnd);
    void restoreWindow(qintptr hwnd);
    void closeWindow(qintptr hwnd);

private:
    static void CALLBACK winEventProc(
        HWINEVENTHOOK hWinEventHook,
        DWORD event,
        HWND hwnd,
        LONG idObject,
        LONG idChild,
        DWORD idEventThread,
        DWORD dwmsEventTime
    );

    void handleWinEvent(DWORD event, HWND hwnd, LONG idObject, LONG idChild);

    HWINEVENTHOOK m_hookCreateDestroy{ nullptr };
    HWINEVENTHOOK m_hookForeground{ nullptr };
    HWINEVENTHOOK m_hookMoveSize{ nullptr };
    HWINEVENTHOOK m_hookShowHide{ nullptr };

    bool m_isRunning{ false };
    HWND m_foregroundHwnd{ nullptr };

    std::unordered_map<HWND, WindowStyleSnapshot> m_trackedWindows;
    mutable std::mutex m_stateMutex;

    static HookEngine* s_instance;
};

} // namespace KWinWin::Hook
