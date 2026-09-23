#pragma once

#include <QObject>
#include <QAbstractListModel>
#include <QImage>
#include <QString>
#include <QVector>
#include <windows.h>
#include <shellapi.h>
#include <mutex>

namespace KWinWin::UI {
    class AppIconProvider;
}

namespace KWinWin::Tray {

struct TrayIconEntry {
    qintptr clientHwnd{ 0 };
    uint32_t uId{ 0 };
    uint32_t uCallbackMessage{ 0 };
    QString iconId;
    QImage iconImage;
    QString toolTip;
};

class TrayModel : public QAbstractListModel {
    Q_OBJECT

public:
    enum TrayRoles {
        ClientHwndRole = Qt::UserRole + 1,
        IdRole,
        ToolTipRole,
        IconRole
    };

    explicit TrayModel(UI::AppIconProvider* iconProvider = nullptr, QObject* parent = nullptr);

    int rowCount(const QModelIndex& parent = QModelIndex()) const override;
    QVariant data(const QModelIndex& index, int role = Qt::DisplayRole) const override;
    QHash<int, QByteArray> roleNames() const override;

    void addOrUpdateIcon(const TrayIconEntry& entry);
    void removeIcon(qintptr hwnd, uint32_t uId);
    void clear();

private:
    QVector<TrayIconEntry> m_entries;
    UI::AppIconProvider* m_iconProvider{ nullptr };
};

class TrayBridge : public QObject {
    Q_OBJECT

public:
    explicit TrayBridge(UI::AppIconProvider* iconProvider = nullptr, QObject* parent = nullptr);
    ~TrayBridge() override;

    bool initialize(int panelHeight = 48);
    void shutdown();

    TrayModel* model() const { return m_trayModel; }

    // Interactivity: forward mouse events from QML to Win32 client tray apps
    Q_INVOKABLE void sendTrayClick(qintptr clientHwnd, uint32_t uId, int mouseButton);

    // Work area management
    void setWorkArea(int panelHeight);
    void restoreWorkArea();

signals:
    void hotkeyRunRequested();
    void hotkeyExplorerRequested();
    void hotkeyTerminalRequested();

private:
    static LRESULT CALLBACK trayWndProc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam);
    LRESULT handleMessage(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam);

    void broadcastTaskbarCreated();
    void registerGlobalHotkeys();
    void unregisterGlobalHotkeys();

    // HICON to QImage converter with alpha transparency support
    static QImage hiconToQImage(HICON hIcon);

    HWND m_trayHwnd{ nullptr };
    UINT m_uTaskbarCreatedMsg{ 0 };
    RECT m_originalWorkArea{ 0, 0, 0, 0 };
    bool m_workAreaModified{ false };

    TrayModel* m_trayModel{ nullptr };
    mutable std::mutex m_trayMutex;

    static TrayBridge* s_instance;
};

} // namespace KWinWin::Tray
