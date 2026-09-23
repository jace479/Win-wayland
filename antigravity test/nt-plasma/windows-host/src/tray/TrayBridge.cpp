#include "TrayBridge.hpp"
#include "AppModel.hpp"
#include "IconUtils.hpp"
#include <QDebug>
#include <QGuiApplication>
#include <QProcess>
#include <QTimer>

namespace KWinWin::Tray {

constexpr int HOTKEY_ID_RUN = 1001;
constexpr int HOTKEY_ID_EXPLORER = 1002;
constexpr int HOTKEY_ID_TERMINAL = 1003;

TrayBridge* TrayBridge::s_instance = nullptr;

// ============================================================================
// TrayModel Implementation
// ============================================================================

TrayModel::TrayModel(UI::AppIconProvider* iconProvider, QObject* parent)
    : QAbstractListModel(parent)
    , m_iconProvider(iconProvider)
{
}

int TrayModel::rowCount(const QModelIndex& parent) const
{
    if (parent.isValid()) return 0;
    return static_cast<int>(m_entries.size());
}

QVariant TrayModel::data(const QModelIndex& index, int role) const
{
    if (!index.isValid() || index.row() < 0 || index.row() >= m_entries.size()) {
        return {};
    }

    const auto& entry = m_entries.at(index.row());
    switch (role) {
    case ClientHwndRole:
        return entry.clientHwnd;
    case IdRole:
        return entry.uId;
    case ToolTipRole:
        return entry.toolTip;
    case IconRole:
        return entry.iconId.isEmpty() ? QString() : QString("image://appicon/%1").arg(entry.iconId);
    case Qt::DisplayRole:
        return entry.toolTip;
    default:
        return {};
    }
}

QHash<int, QByteArray> TrayModel::roleNames() const
{
    return {
        { ClientHwndRole, "clientHwnd" },
        { IdRole, "trayId" },
        { ToolTipRole, "toolTip" },
        { IconRole, "trayIcon" }
    };
}

void TrayModel::addOrUpdateIcon(const TrayIconEntry& entry)
{
    if (m_iconProvider && !entry.iconImage.isNull() && !entry.iconId.isEmpty()) {
        m_iconProvider->addIcon(entry.iconId, entry.iconImage);
    }

    for (int i = 0; i < m_entries.size(); ++i) {
        if (m_entries[i].clientHwnd == entry.clientHwnd && m_entries[i].uId == entry.uId) {
            m_entries[i].uCallbackMessage = entry.uCallbackMessage;
            m_entries[i].iconId = entry.iconId;
            if (!entry.iconImage.isNull()) {
                m_entries[i].iconImage = entry.iconImage;
            }
            if (!entry.toolTip.isEmpty()) {
                m_entries[i].toolTip = entry.toolTip;
            }
            emit dataChanged(index(i), index(i));
            return;
        }
    }

    beginInsertRows(QModelIndex(), m_entries.size(), m_entries.size());
    m_entries.append(entry);
    endInsertRows();
}

void TrayModel::removeIcon(qintptr hwnd, uint32_t uId)
{
    for (int i = 0; i < m_entries.size(); ++i) {
        if (m_entries[i].clientHwnd == hwnd && m_entries[i].uId == uId) {
            beginRemoveRows(QModelIndex(), i, i);
            m_entries.removeAt(i);
            endRemoveRows();
            return;
        }
    }
}

void TrayModel::clear()
{
    beginResetModel();
    m_entries.clear();
    endResetModel();
}

// ============================================================================
// TrayBridge Implementation
// ============================================================================

TrayBridge::TrayBridge(UI::AppIconProvider* iconProvider, QObject* parent)
    : QObject(parent)
    , m_trayModel(new TrayModel(iconProvider, this))
{
    s_instance = this;
}

TrayBridge::~TrayBridge()
{
    shutdown();
    if (s_instance == this) {
        s_instance = nullptr;
    }
}

bool TrayBridge::initialize(int panelHeight)
{
    HINSTANCE hInstance = GetModuleHandleW(nullptr);

    WNDCLASSEXW wc{};
    wc.cbSize = sizeof(wc);
    wc.lpfnWndProc = trayWndProc;
    wc.hInstance = hInstance;
    wc.lpszClassName = L"Shell_TrayWnd";
    wc.style = CS_DBLCLKS;

    RegisterClassExW(&wc);

    m_trayHwnd = CreateWindowExW(
        0,
        L"Shell_TrayWnd",
        L"",
        WS_POPUP,
        0, 0, 0, 0,
        nullptr,
        nullptr,
        hInstance,
        nullptr
    );

    if (!m_trayHwnd) {
        qWarning() << "[TrayBridge] Failed to create dummy Shell_TrayWnd window.";
        return false;
    }

    // Set desktop work area
    setWorkArea(panelHeight);

    // Register TaskbarCreated message and broadcast to OS
    m_uTaskbarCreatedMsg = RegisterWindowMessageW(L"TaskbarCreated");
    broadcastTaskbarCreated();

    // Register global hotkeys
    registerGlobalHotkeys();

    qInfo() << "[TrayBridge] Shell_TrayWnd dummy window active and TaskbarCreated broadcasted.";
    return true;
}

void TrayBridge::shutdown()
{
    unregisterGlobalHotkeys();
    restoreWorkArea();

    if (m_trayHwnd && IsWindow(m_trayHwnd)) {
        DestroyWindow(m_trayHwnd);
        m_trayHwnd = nullptr;
    }

    UnregisterClassW(L"Shell_TrayWnd", GetModuleHandleW(nullptr));
}

void TrayBridge::setWorkArea(int panelHeight)
{
    SystemParametersInfoW(SPI_GETWORKAREA, 0, &m_originalWorkArea, 0);

    int screenW = GetSystemMetrics(SM_CXSCREEN);
    int screenH = GetSystemMetrics(SM_CYSCREEN);

    RECT newWorkArea = { 0, 0, screenW, screenH - panelHeight };
    SystemParametersInfoW(SPI_SETWORKAREA, 0, &newWorkArea, SPIF_SENDCHANGE | SPIF_UPDATEINIFILE);
    m_workAreaModified = true;
    qInfo() << "[TrayBridge] Desktop work area updated to reserve" << panelHeight << "px panel space.";
}

void TrayBridge::restoreWorkArea()
{
    if (m_workAreaModified && (m_originalWorkArea.right > 0 && m_originalWorkArea.bottom > 0)) {
        SystemParametersInfoW(SPI_SETWORKAREA, 0, &m_originalWorkArea, SPIF_SENDCHANGE | SPIF_UPDATEINIFILE);
        m_workAreaModified = false;
        qInfo() << "[TrayBridge] Desktop work area restored to original dimensions.";
    }
}

void TrayBridge::broadcastTaskbarCreated()
{
    if (m_uTaskbarCreatedMsg != 0) {
        PostMessageW(HWND_BROADCAST, m_uTaskbarCreatedMsg, 0, 0);
    }
}

void TrayBridge::registerGlobalHotkeys()
{
    if (!m_trayHwnd) return;

    RegisterHotKey(m_trayHwnd, HOTKEY_ID_RUN, MOD_WIN | MOD_NOREPEAT, 'R');
    RegisterHotKey(m_trayHwnd, HOTKEY_ID_EXPLORER, MOD_WIN | MOD_NOREPEAT, 'E');
    RegisterHotKey(m_trayHwnd, HOTKEY_ID_TERMINAL, MOD_WIN | MOD_NOREPEAT, 'T');
}

void TrayBridge::unregisterGlobalHotkeys()
{
    if (!m_trayHwnd) return;

    UnregisterHotKey(m_trayHwnd, HOTKEY_ID_RUN);
    UnregisterHotKey(m_trayHwnd, HOTKEY_ID_EXPLORER);
    UnregisterHotKey(m_trayHwnd, HOTKEY_ID_TERMINAL);
}

void TrayBridge::sendTrayClick(qintptr clientHwndVal, uint32_t uId, int mouseButton)
{
    HWND clientHwnd = reinterpret_cast<HWND>(clientHwndVal);
    if (!IsWindow(clientHwnd)) return;

    // Find callback message
    uint32_t callbackMsg = 0;
    {
        std::lock_guard<std::mutex> lock(m_trayMutex);
        for (int i = 0; i < m_trayModel->rowCount(); ++i) {
            QModelIndex idx = m_trayModel->index(i);
            if (idx.data(TrayModel::ClientHwndRole).value<qintptr>() == clientHwndVal &&
                idx.data(TrayModel::IdRole).toUInt() == uId) {
                // Found
                break;
            }
        }
    }

    // Prepare mouse click message
    SetForegroundWindow(clientHwnd);

    POINT pt;
    GetCursorPos(&pt);

    switch (mouseButton) {
    case 1: // Left Click
        PostMessageW(clientHwnd, callbackMsg ? callbackMsg : WM_USER + 1, static_cast<WPARAM>(uId), WM_LBUTTONDOWN);
        PostMessageW(clientHwnd, callbackMsg ? callbackMsg : WM_USER + 1, static_cast<WPARAM>(uId), WM_LBUTTONUP);
        break;
    case 2: // Right Click (Context Menu)
        PostMessageW(clientHwnd, callbackMsg ? callbackMsg : WM_USER + 1, static_cast<WPARAM>(uId), WM_RBUTTONDOWN);
        PostMessageW(clientHwnd, callbackMsg ? callbackMsg : WM_USER + 1, static_cast<WPARAM>(uId), WM_RBUTTONUP);
        PostMessageW(clientHwnd, callbackMsg ? callbackMsg : WM_USER + 1, static_cast<WPARAM>(uId), WM_CONTEXTMENU);
        break;
    case 3: // Double Click
        PostMessageW(clientHwnd, callbackMsg ? callbackMsg : WM_USER + 1, static_cast<WPARAM>(uId), WM_LBUTTONDBLCLK);
        break;
    }
}

QImage TrayBridge::hiconToQImage(HICON hIcon)
{
    return UI::hiconToQImage(hIcon);
}

LRESULT CALLBACK TrayBridge::trayWndProc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam)
{
    if (s_instance) {
        return s_instance->handleMessage(hwnd, uMsg, wParam, lParam);
    }
    return DefWindowProcW(hwnd, uMsg, wParam, lParam);
}

LRESULT TrayBridge::handleMessage(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam)
{
    switch (uMsg) {
    case WM_HOTKEY: {
        int hotkeyId = static_cast<int>(wParam);
        if (hotkeyId == HOTKEY_ID_RUN) {
            emit hotkeyRunRequested();
            QProcess::startDetached("explorer.exe", QStringList() << "shell:::{2559a1f3-21d7-11d4-bdaf-00c04f60b9f0}");
        } else if (hotkeyId == HOTKEY_ID_EXPLORER) {
            emit hotkeyExplorerRequested();
            QProcess::startDetached("explorer.exe", QStringList());
        } else if (hotkeyId == HOTKEY_ID_TERMINAL) {
            emit hotkeyTerminalRequested();
            if (!QProcess::startDetached("wt.exe", QStringList())) {
                QProcess::startDetached("powershell.exe", QStringList());
            }
        }
        return 0;
    }
    case WM_COPYDATA: {
        auto* pcds = reinterpret_cast<COPYDATASTRUCT*>(lParam);
        if (!pcds || !pcds->lpData || pcds->cbData < sizeof(DWORD)) {
            return FALSE;
        }

        DWORD dwMessage = 0;
        NOTIFYICONDATAW nid{};

        if (pcds->cbData >= sizeof(DWORD) + sizeof(NOTIFYICONDATAW)) {
            dwMessage = *reinterpret_cast<DWORD*>(pcds->lpData);
            auto* pNid = reinterpret_cast<NOTIFYICONDATAW*>(static_cast<char*>(pcds->lpData) + sizeof(DWORD));
            memcpy(&nid, pNid, std::min<size_t>(sizeof(NOTIFYICONDATAW), pcds->cbData - sizeof(DWORD)));
        } else if (pcds->cbData >= sizeof(NOTIFYICONDATAW)) {
            memcpy(&nid, pcds->lpData, sizeof(NOTIFYICONDATAW));
            dwMessage = NIM_ADD;
        }

        if (nid.hWnd && IsWindow(nid.hWnd)) {
            TrayIconEntry entry;
            entry.clientHwnd = reinterpret_cast<qintptr>(nid.hWnd);
            entry.uId = nid.uID;
            entry.uCallbackMessage = nid.uCallbackMessage;
            entry.iconId = QString("tray_%1_%2").arg(entry.clientHwnd).arg(entry.uId);
            entry.toolTip = QString::fromWCharArray(nid.szTip);
            if (nid.hIcon) {
                entry.iconImage = hiconToQImage(nid.hIcon);
            }

            QMetaObject::invokeMethod(this, [this, dwMessage, entry]() {
                std::lock_guard<std::mutex> lock(m_trayMutex);
                if (dwMessage == NIM_DELETE) {
                    m_trayModel->removeIcon(entry.clientHwnd, entry.uId);
                } else {
                    m_trayModel->addOrUpdateIcon(entry);
                }
            }, Qt::QueuedConnection);
        }

        return TRUE;
    }
    default:
        break;
    }

    return DefWindowProcW(hwnd, uMsg, wParam, lParam);
}

} // namespace KWinWin::Tray
