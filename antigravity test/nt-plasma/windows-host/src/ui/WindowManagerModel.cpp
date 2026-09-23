#include "WindowManagerModel.hpp"
#include "IconUtils.hpp"
#include <shellapi.h>
#include <QDebug>

namespace KWinWin::UI {

WindowManagerModel::WindowManagerModel(Hook::HookEngine* hookEngine, AppIconProvider* iconProvider, QObject* parent)
    : QAbstractListModel(parent)
    , m_hookEngine(hookEngine)
    , m_iconProvider(iconProvider)
{
    if (m_hookEngine) {
        connect(m_hookEngine, &Hook::HookEngine::windowCreated, this, &WindowManagerModel::onWindowCreated);
        connect(m_hookEngine, &Hook::HookEngine::windowDestroyed, this, &WindowManagerModel::onWindowDestroyed);
        connect(m_hookEngine, &Hook::HookEngine::windowActivated, this, &WindowManagerModel::onWindowActivated);
        connect(m_hookEngine, &Hook::HookEngine::windowGeometryChanged, this, &WindowManagerModel::onWindowGeometryChanged);
        connect(m_hookEngine, &Hook::HookEngine::windowVisibilityChanged, this, &WindowManagerModel::onWindowVisibilityChanged);
    }
}

int WindowManagerModel::rowCount(const QModelIndex& parent) const
{
    if (parent.isValid()) return 0;
    return static_cast<int>(m_windows.size());
}

QVariant WindowManagerModel::data(const QModelIndex& index, int role) const
{
    if (!index.isValid() || index.row() < 0 || index.row() >= m_windows.size()) {
        return {};
    }

    const auto& item = m_windows.at(index.row());
    switch (role) {
    case HwndRole:
        return item.hwnd;
    case TitleRole:
    case Qt::DisplayRole:
        return item.title;
    case IsActiveRole:
        return item.isActive;
    case IsMinimizedRole:
        return item.isMinimized;
    case IsMaximizedRole:
        return item.isMaximized;
    case IsVisibleRole:
        return item.isVisible;
    case BoundsRole:
        return item.bounds;
    case XRole:
        return item.bounds.x();
    case YRole:
        return item.bounds.y();
    case WidthRole:
        return item.bounds.width();
    case HeightRole:
        return item.bounds.height();
    case IconUrlRole:
        return QString("image://appicon/%1").arg(item.iconId);
    default:
        return {};
    }
}

QHash<int, QByteArray> WindowManagerModel::roleNames() const
{
    return {
        { HwndRole, "hwnd" },
        { TitleRole, "windowTitle" },
        { IsActiveRole, "isActive" },
        { IsMinimizedRole, "isMinimized" },
        { IsMaximizedRole, "isMaximized" },
        { IsVisibleRole, "isVisible" },
        { BoundsRole, "bounds" },
        { XRole, "windowX" },
        { YRole, "windowY" },
        { WidthRole, "windowWidth" },
        { HeightRole, "windowHeight" },
        { IconUrlRole, "iconUrl" }
    };
}

int WindowManagerModel::findIndexByHwnd(qintptr hwnd) const
{
    for (int i = 0; i < m_windows.size(); ++i) {
        if (m_windows[i].hwnd == hwnd) {
            return i;
        }
    }
    return -1;
}

void WindowManagerModel::extractAndStoreWindowIcon(HWND hwnd, const QString& iconId)
{
    if (!m_iconProvider || !IsWindow(hwnd)) return;

    HICON hIcon = nullptr;
    DWORD_PTR dwResult = 0;

    // 1. Send WM_GETICON with timeout to avoid deadlocks
    if (SendMessageTimeoutW(hwnd, WM_GETICON, ICON_BIG, 0, SMTO_ABORTIFHUNG | SMTO_BLOCK, 80, &dwResult) && dwResult) {
        hIcon = reinterpret_cast<HICON>(dwResult);
    }
    if (!hIcon && SendMessageTimeoutW(hwnd, WM_GETICON, ICON_SMALL2, 0, SMTO_ABORTIFHUNG | SMTO_BLOCK, 80, &dwResult) && dwResult) {
        hIcon = reinterpret_cast<HICON>(dwResult);
    }
    if (!hIcon && SendMessageTimeoutW(hwnd, WM_GETICON, ICON_SMALL, 0, SMTO_ABORTIFHUNG | SMTO_BLOCK, 80, &dwResult) && dwResult) {
        hIcon = reinterpret_cast<HICON>(dwResult);
    }

    // 2. Class icon fallback
    if (!hIcon) {
        hIcon = reinterpret_cast<HICON>(GetClassLongPtrW(hwnd, GCLP_HICON));
    }
    if (!hIcon) {
        hIcon = reinterpret_cast<HICON>(GetClassLongPtrW(hwnd, GCLP_HICONSM));
    }

    QImage image;
    if (hIcon) {
        image = hiconToQImage(hIcon);
    }

    // 3. Process image fallback if window doesn't report an icon
    if (image.isNull()) {
        DWORD pid = 0;
        GetWindowThreadProcessId(hwnd, &pid);
        if (pid > 0) {
            HANDLE hProc = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
            if (hProc) {
                wchar_t exePath[MAX_PATH]{};
                DWORD size = MAX_PATH;
                if (QueryFullProcessImageNameW(hProc, 0, exePath, &size)) {
                    SHFILEINFO sfi{};
                    if (SHGetFileInfoW(exePath, 0, &sfi, sizeof(sfi), SHGFI_ICON | SHGFI_LARGEICON) && sfi.hIcon) {
                        image = hiconToQImage(sfi.hIcon);
                        DestroyIcon(sfi.hIcon);
                    }
                }
                CloseHandle(hProc);
            }
        }
    }

    if (!image.isNull()) {
        m_iconProvider->addIcon(iconId, image);
    }
}

void WindowManagerModel::onWindowCreated(qintptr hwndVal, const QString& title)
{
    if (findIndexByHwnd(hwndVal) >= 0) return;

    HWND hwnd = reinterpret_cast<HWND>(hwndVal);
    ManagedWindowItem item;
    item.hwnd = hwndVal;
    item.title = title;
    item.bounds = Hook::HookEngine::getWindowExtendedBounds(hwnd);
    item.iconId = QString("win_%1").arg(hwndVal);
    item.isVisible = IsWindowVisible(hwnd);
    item.isMinimized = IsIconic(hwnd);

    WINDOWPLACEMENT wp{};
    wp.length = sizeof(wp);
    GetWindowPlacement(hwnd, &wp);
    item.isMaximized = (wp.showCmd == SW_SHOWMAXIMIZED);

    extractAndStoreWindowIcon(hwnd, item.iconId);

    beginInsertRows(QModelIndex(), m_windows.size(), m_windows.size());
    m_windows.append(item);
    endInsertRows();
}

void WindowManagerModel::onWindowDestroyed(qintptr hwndVal)
{
    int index = findIndexByHwnd(hwndVal);
    if (index >= 0) {
        beginRemoveRows(QModelIndex(), index, index);
        m_windows.removeAt(index);
        endRemoveRows();
    }
}

void WindowManagerModel::onWindowActivated(qintptr hwndVal)
{
    for (int i = 0; i < m_windows.size(); ++i) {
        bool wasActive = m_windows[i].isActive;
        bool shouldBeActive = (m_windows[i].hwnd == hwndVal);
        if (wasActive != shouldBeActive) {
            m_windows[i].isActive = shouldBeActive;
            emit dataChanged(index(i), index(i), { IsActiveRole });
        }
    }
}

void WindowManagerModel::onWindowGeometryChanged(qintptr hwndVal, const QRect& bounds)
{
    int idx = findIndexByHwnd(hwndVal);
    if (idx >= 0) {
        HWND hwnd = reinterpret_cast<HWND>(hwndVal);
        m_windows[idx].bounds = bounds;
        m_windows[idx].isMinimized = IsIconic(hwnd);

        WINDOWPLACEMENT wp{};
        wp.length = sizeof(wp);
        GetWindowPlacement(hwnd, &wp);
        m_windows[idx].isMaximized = (wp.showCmd == SW_SHOWMAXIMIZED);

        emit dataChanged(index(idx), index(idx), { BoundsRole, XRole, YRole, WidthRole, HeightRole, IsMinimizedRole, IsMaximizedRole });
    }
}

void WindowManagerModel::onWindowVisibilityChanged(qintptr hwndVal, bool visible)
{
    int idx = findIndexByHwnd(hwndVal);
    if (idx >= 0) {
        m_windows[idx].isVisible = visible;
        emit dataChanged(index(idx), index(idx), { IsVisibleRole });
    }
}

void WindowManagerModel::activateWindow(qintptr hwndVal)
{
    if (m_hookEngine) {
        m_hookEngine->activateWindow(hwndVal);
    }
}

void WindowManagerModel::toggleMinimize(qintptr hwndVal)
{
    HWND hwnd = reinterpret_cast<HWND>(hwndVal);
    if (!IsWindow(hwnd)) return;

    if (IsIconic(hwnd)) {
        if (m_hookEngine) m_hookEngine->restoreWindow(hwndVal);
    } else {
        if (GetForegroundWindow() == hwnd) {
            if (m_hookEngine) m_hookEngine->minimizeWindow(hwndVal);
        } else {
            if (m_hookEngine) m_hookEngine->activateWindow(hwndVal);
        }
    }
}

void WindowManagerModel::toggleMaximize(qintptr hwndVal)
{
    if (m_hookEngine) {
        m_hookEngine->maximizeWindow(hwndVal);
    }
}

void WindowManagerModel::closeWindow(qintptr hwndVal)
{
    if (m_hookEngine) {
        m_hookEngine->closeWindow(hwndVal);
    }
}

} // namespace KWinWin::UI
