#include <QApplication>
#include <QSystemTrayIcon>
#include <QMenu>
#include <QAction>
#include <QActionGroup>
#include <QPainter>
#include <QPainterPath>
#include <QRadialGradient>
#include <QScreen>
#include <QTimer>
#include <QDebug>
#include <QProcess>
#include <QFile>
#include <QTextStream>
#include <QDateTime>
#include <QAbstractNativeEventFilter>

#include <windows.h>
#include <commctrl.h>

void messageOutput(QtMsgType type, const QMessageLogContext& context, const QString& msg)
{
    static QFile logFile("kwin_win_debug.log");
    if (!logFile.isOpen()) {
        logFile.open(QIODevice::WriteOnly | QIODevice::Append | QIODevice::Text);
    }
    QTextStream ts(&logFile);
    ts << QDateTime::currentDateTime().toString("yyyy-MM-dd hh:mm:ss.zzz ") << msg << "\n";
    ts.flush();
    OutputDebugStringW(reinterpret_cast<LPCWSTR>(msg.utf16()));
    OutputDebugStringW(L"\n");
}

LONG WINAPI crashFilter(EXCEPTION_POINTERS* ep)
{
    DWORD code = ep && ep->ExceptionRecord ? ep->ExceptionRecord->ExceptionCode : 0;
    PVOID addr = ep && ep->ExceptionRecord ? ep->ExceptionRecord->ExceptionAddress : nullptr;
    qCritical() << "[CRASH] Unhandled Exception 0x" + QString::number(code, 16) + " at address " + QString::number(reinterpret_cast<quintptr>(addr), 16);
    return EXCEPTION_EXECUTE_HANDLER;
}

static void runWslCommandAsync(const QString& bashCmd)
{
    QProcess::startDetached("wsl.exe", QStringList() << "-d" << "Ubuntu" << "-u" << "jace479" << "-e" << "bash" << "-c" << bashCmd);
}

static void launchKdeApp(const QString& appName, const QString& arg = QString())
{
    QString cmd = "/opt/nt-plasma/wsl/launch-app.sh " + appName;
    if (!arg.isEmpty()) {
        cmd += " \"" + arg + "\"";
    }
    runWslCommandAsync(cmd);
}

static QIcon createKdePlasmaIcon()
{
    QPixmap pix(64, 64);
    pix.fill(Qt::transparent);
    QPainter p(&pix);
    p.setRenderHint(QPainter::Antialiasing);

    // Breeze Dark circle with neon cyan accent ring
    p.setBrush(QColor(35, 38, 41)); // #232629
    p.setPen(QPen(QColor(61, 174, 233), 3)); // #3daee9
    p.drawEllipse(3, 3, 58, 58);

    // Radial gradient glow
    QRadialGradient grad(32, 32, 26);
    grad.setColorAt(0.0, QColor(61, 174, 233, 220));
    grad.setColorAt(1.0, QColor(24, 38, 56, 240));
    p.setBrush(grad);
    p.setPen(Qt::NoPen);
    p.drawEllipse(10, 10, 44, 44);

    // KDE Plasma Stylized "K" emblem
    p.setPen(QPen(Qt::white, 4, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin));
    p.drawLine(24, 20, 24, 44);
    p.drawLine(38, 20, 24, 32);
    p.drawLine(24, 32, 39, 44);

    return QIcon(pix);
}

class HotkeyNativeFilter : public QAbstractNativeEventFilter {
public:
    bool nativeEventFilter(const QByteArray& eventType, void* message, qintptr* result) override {
        Q_UNUSED(eventType);
        Q_UNUSED(result);
        MSG* msg = static_cast<MSG*>(message);
        if (msg && msg->message == WM_HOTKEY) {
            if (msg->wParam == 101) {
                launchKdeApp("krunner");
                return true;
            } else if (msg->wParam == 102) {
                launchKdeApp("konsole");
                return true;
            } else if (msg->wParam == 103) {
                launchKdeApp("dolphin");
                return true;
            }
        }
        return false;
    }
};

struct ContainerWindowSearch {
    HWND foundHwnd = nullptr;
    QString targetTitleSubstring;
};

static BOOL CALLBACK EnumWindowsCallback(HWND hwnd, LPARAM lParam)
{
    auto* search = reinterpret_cast<ContainerWindowSearch*>(lParam);
    if (!IsWindowVisible(hwnd)) return TRUE;

    wchar_t titleBuf[512] = {0};
    GetWindowTextW(hwnd, titleBuf, 511);
    QString title = QString::fromWCharArray(titleBuf);

    if (title.contains("Authentic Linux Desktop", Qt::CaseInsensitive) ||
        title.contains("Xephyr on", Qt::CaseInsensitive) ||
        title.startsWith("Xephyr", Qt::CaseInsensitive))
    {
        search->foundHwnd = hwnd;
        return FALSE; // Stop enumeration
    }
    return TRUE;
}

int main(int argc, char* argv[])
{
    if (AttachConsole(ATTACH_PARENT_PROCESS)) {
        FILE* fp;
        freopen_s(&fp, "CONOUT$", "w", stdout);
        freopen_s(&fp, "CONOUT$", "w", stderr);
        freopen_s(&fp, "CONIN$", "r", stdin);
    }

    SetUnhandledExceptionFilter(crashFilter);
    qInstallMessageHandler(messageOutput);
    qInfo() << "[Main] Starting Authentic Linux Desktop Shell Host (KWin-Win)...";

    // 1. Initialize High-DPI Awareness (Per-Monitor V2)
    SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);

    // 2. Initialize Qt Application
    QApplication app(argc, argv);
    app.setOrganizationName("ProjectKWinWin");
    app.setApplicationName("KWin-Win");
    app.setApplicationVersion("2.0.0");
    app.setQuitOnLastWindowClosed(false);

    // 3. Register Global Hotkeys: Alt+Space (KRunner), Win+T (Konsole), Win+E (Dolphin)
    RegisterHotKey(nullptr, 101, MOD_ALT | MOD_NOREPEAT, VK_SPACE);
    RegisterHotKey(nullptr, 102, MOD_WIN | MOD_NOREPEAT, 'T');
    RegisterHotKey(nullptr, 103, MOD_WIN | MOD_NOREPEAT, 'E');
    app.installNativeEventFilter(new HotkeyNativeFilter());

    // Desktop Session State
    QString sessionType = "plasma";
    int targetWidth = 1920;
    int targetHeight = 1080;
    bool borderlessFullscreen = true;
    HWND hookedContainerHwnd = nullptr;

    auto startSession = [&](const QString& session, int w, int h) {
        qInfo() << "[Main] Launching authentic desktop session:" << session << w << "x" << h;
        QString cmd = QString("nohup /opt/nt-plasma/wsl/start-authentic-desktop.sh %1 %2 %3 </dev/null >/tmp/desktop-session.log 2>&1 &")
                          .arg(session).arg(w).arg(h);
        runWslCommandAsync(cmd);
    };

    auto stopSession = []() {
        qInfo() << "[Main] Stopping desktop session cleanly...";
        QProcess stopProc;
        stopProc.start("wsl.exe", QStringList() << "-d" << "Ubuntu" << "-u" << "jace479" << "-e" << "bash" << "-c" << "/opt/nt-plasma/wsl/stop-authentic-desktop.sh");
        stopProc.waitForFinished(6000);
    };

    // 4. Container Window Framing Hook Timer
    QTimer hookTimer;
    hookTimer.setInterval(800);
    QObject::connect(&hookTimer, &QTimer::timeout, [&]() {
        ContainerWindowSearch search;
        EnumWindows(EnumWindowsCallback, reinterpret_cast<LPARAM>(&search));
        if (search.foundHwnd && search.foundHwnd != hookedContainerHwnd) {
            hookedContainerHwnd = search.foundHwnd;
            qInfo() << "[Main] Detected Authentic Linux Desktop container HWND:" << Qt::hex << reinterpret_cast<quintptr>(hookedContainerHwnd);

            if (borderlessFullscreen) {
                // Strip window decorations
                LONG_PTR style = GetWindowLongPtrW(hookedContainerHwnd, GWL_STYLE);
                style &= ~(WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU);
                SetWindowLongPtrW(hookedContainerHwnd, GWL_STYLE, style);

                QScreen* primary = QGuiApplication::primaryScreen();
                QRect geo = primary ? primary->geometry() : QRect(0, 0, targetWidth, targetHeight);
                if (targetWidth > 1920) {
                    // Spanning canvas
                    geo = QRect(0, 0, targetWidth, targetHeight);
                }

                SetWindowPos(hookedContainerHwnd, HWND_TOP, geo.x(), geo.y(), geo.width(), geo.height(),
                             SWP_FRAMECHANGED | SWP_SHOWWINDOW);
                qInfo() << "[Main] Anchored container window to borderless fullscreen:" << geo.width() << "x" << geo.height();
            }
        }
    });
    hookTimer.start();

    // 5. System Tray Icon Controller
    QSystemTrayIcon trayIcon;
    trayIcon.setIcon(createKdePlasmaIcon());
    trayIcon.setToolTip("Authentic Linux Desktop Shell (WSLg - Zero TCP/IP)");

    QMenu trayMenu;
    QAction* actHeader = trayMenu.addAction("⚡ Authentic Linux Desktop Shell");
    actHeader->setEnabled(false);
    trayMenu.addSeparator();

    // Environment submenu
    QMenu* envMenu = trayMenu.addMenu("🖥 Desktop Environment");
    QActionGroup* envGroup = new QActionGroup(&trayMenu);
    QAction* actKde = envMenu->addAction("KDE Plasma 5.27 LTS");
    QAction* actXfce = envMenu->addAction("XFCE 4.18");
    actKde->setCheckable(true);
    actXfce->setCheckable(true);
    actKde->setChecked(true);
    envGroup->addAction(actKde);
    envGroup->addAction(actXfce);

    // Display Output submenu
    QMenu* dispMenu = trayMenu.addMenu("📐 Display Mode");
    QActionGroup* dispGroup = new QActionGroup(&trayMenu);
    QAction* actPrimary = dispMenu->addAction("Primary Display (1920x1080)");
    QAction* actCanvas = dispMenu->addAction("Multi-Monitor Canvas (6330x2160)");
    actPrimary->setCheckable(true);
    actCanvas->setCheckable(true);
    actPrimary->setChecked(true);
    dispGroup->addAction(actPrimary);
    dispGroup->addAction(actCanvas);

    // Presentation Mode
    QAction* actBorderless = trayMenu.addAction("🔲 Seamless Borderless Fullscreen");
    actBorderless->setCheckable(true);
    actBorderless->setChecked(true);

    trayMenu.addSeparator();
    QAction* actStart = trayMenu.addAction("▶ Start / Resume Desktop Session");
    QAction* actRestart = trayMenu.addAction("🔄 Restart Desktop Session");
    QAction* actStop = trayMenu.addAction("⏹ Stop Desktop Session");

    trayMenu.addSeparator();
    QAction* actDolphin = trayMenu.addAction("📁 Dolphin File Manager (Win+E)");
    QAction* actKonsole = trayMenu.addAction("💻 Konsole Terminal (Win+T)");
    QAction* actKRunner = trayMenu.addAction("🚀 KRunner Quick Launcher (Alt+Space)");
    QAction* actSettings = trayMenu.addAction("⚙ KDE System Settings");

    trayMenu.addSeparator();
    QAction* actExit = trayMenu.addAction("❌ Exit Host Shell");

    // Action Connections
    QObject::connect(actKde, &QAction::triggered, [&]() { sessionType = "plasma"; });
    QObject::connect(actXfce, &QAction::triggered, [&]() { sessionType = "xfce"; });

    QObject::connect(actPrimary, &QAction::triggered, [&]() {
        targetWidth = 1920;
        targetHeight = 1080;
    });
    QObject::connect(actCanvas, &QAction::triggered, [&]() {
        targetWidth = 6330;
        targetHeight = 2160;
    });

    QObject::connect(actBorderless, &QAction::toggled, [&](bool checked) {
        borderlessFullscreen = checked;
        hookedContainerHwnd = nullptr; // trigger re-hook
    });

    QObject::connect(actStart, &QAction::triggered, [&]() {
        startSession(sessionType, targetWidth, targetHeight);
    });

    QObject::connect(actRestart, &QAction::triggered, [&]() {
        stopSession();
        QTimer::singleShot(1500, [&]() {
            hookedContainerHwnd = nullptr;
            startSession(sessionType, targetWidth, targetHeight);
        });
    });

    QObject::connect(actStop, &QAction::triggered, [&]() {
        stopSession();
        hookedContainerHwnd = nullptr;
    });

    QObject::connect(actDolphin, &QAction::triggered, []() { launchKdeApp("dolphin"); });
    QObject::connect(actKonsole, &QAction::triggered, []() { launchKdeApp("konsole"); });
    QObject::connect(actKRunner, &QAction::triggered, []() { launchKdeApp("krunner"); });
    QObject::connect(actSettings, &QAction::triggered, []() { launchKdeApp("systemsettings"); });

    QObject::connect(actExit, &QAction::triggered, [&]() {
        stopSession();
        app.quit();
    });

    trayIcon.setContextMenu(&trayMenu);
    trayIcon.show();

    // Auto-start default session (KDE Plasma) on launch
    startSession(sessionType, targetWidth, targetHeight);

    // Launch notification
    QTimer::singleShot(2000, [&trayIcon]() {
        trayIcon.showMessage(
            "Authentic Linux Desktop Active",
            "Genuine KDE Plasma 5.27 session is running on WSLg over native UNIX domain sockets (Zero TCP/IP).\nRight-click tray icon to switch sessions, change displays, or launch apps.",
            QSystemTrayIcon::Information,
            4000
        );
    });

    QObject::connect(&app, &QGuiApplication::aboutToQuit, [&]() {
        UnregisterHotKey(nullptr, 101);
        UnregisterHotKey(nullptr, 102);
        UnregisterHotKey(nullptr, 103);
        stopSession();
    });

    return app.exec();
}
