#pragma once

#include <QAbstractListModel>
#include <QRect>
#include <QString>
#include <QVector>
#include <windows.h>
#include "HookEngine.hpp"
#include "AppModel.hpp"

namespace KWinWin::UI {

struct ManagedWindowItem {
    qintptr hwnd{ 0 };
    QString title;
    QRect bounds;
    bool isActive{ false };
    bool isMinimized{ false };
    bool isMaximized{ false };
    bool isVisible{ true };
    QString iconId;
};

class WindowManagerModel : public QAbstractListModel {
    Q_OBJECT

public:
    enum WindowRoles {
        HwndRole = Qt::UserRole + 1,
        TitleRole,
        IsActiveRole,
        IsMinimizedRole,
        IsMaximizedRole,
        IsVisibleRole,
        BoundsRole,
        XRole,
        YRole,
        WidthRole,
        HeightRole,
        IconUrlRole
    };

    explicit WindowManagerModel(Hook::HookEngine* hookEngine, AppIconProvider* iconProvider, QObject* parent = nullptr);

    int rowCount(const QModelIndex& parent = QModelIndex()) const override;
    QVariant data(const QModelIndex& index, int role = Qt::DisplayRole) const override;
    QHash<int, QByteArray> roleNames() const override;

    Q_INVOKABLE void activateWindow(qintptr hwnd);
    Q_INVOKABLE void toggleMinimize(qintptr hwnd);
    Q_INVOKABLE void toggleMaximize(qintptr hwnd);
    Q_INVOKABLE void closeWindow(qintptr hwnd);

private slots:
    void onWindowCreated(qintptr hwnd, const QString& title);
    void onWindowDestroyed(qintptr hwnd);
    void onWindowActivated(qintptr hwnd);
    void onWindowGeometryChanged(qintptr hwnd, const QRect& bounds);
    void onWindowVisibilityChanged(qintptr hwnd, bool visible);

private:
    int findIndexByHwnd(qintptr hwnd) const;
    void extractAndStoreWindowIcon(HWND hwnd, const QString& iconId);

    Hook::HookEngine* m_hookEngine{ nullptr };
    AppIconProvider* m_iconProvider{ nullptr };
    QVector<ManagedWindowItem> m_windows;
};

} // namespace KWinWin::UI
