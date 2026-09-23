#pragma once

#include <QAbstractListModel>
#include <QImage>
#include <QString>
#include <QStringList>
#include <QVector>
#include <QQuickImageProvider>
#include <windows.h>
#include <shlobj.h>
#include <unordered_map>
#include <vector>
#include <mutex>

namespace KWinWin::UI {

struct AppEntry {
    QString id;
    QString name;
    QString execOrAumid;
    QString arguments;
    QString workingDir;
    QString category;
    bool isUwp{ false };
    bool isLinux{ false };
    QImage icon;
};

class AppIconProvider : public QQuickImageProvider {
public:
    AppIconProvider();
    QImage requestImage(const QString& id, QSize* size, const QSize& requestedSize) override;
    void addIcon(const QString& id, const QImage& image);
    void clear();

private:
    std::unordered_map<std::string, QImage> m_icons;
    mutable std::mutex m_mutex;
};

class AppModel : public QAbstractListModel {
    Q_OBJECT
    Q_PROPERTY(QStringList categories READ categories NOTIFY categoriesChanged)
    Q_PROPERTY(QString categoryFilter READ categoryFilter WRITE setCategoryFilter NOTIFY categoryFilterChanged)
    Q_PROPERTY(QString searchFilter READ searchFilter WRITE setSearchFilter NOTIFY searchFilterChanged)
    Q_PROPERTY(int count READ count NOTIFY countChanged)

public:
    enum AppRoles {
        IdRole = Qt::UserRole + 1,
        NameRole,
        ExecRole,
        CategoryRole,
        IsUwpRole,
        IconUrlRole,
        SearchRole
    };

    explicit AppModel(AppIconProvider* iconProvider, QObject* parent = nullptr);

    int rowCount(const QModelIndex& parent = QModelIndex()) const override;
    QVariant data(const QModelIndex& index, int role = Qt::DisplayRole) const override;
    QHash<int, QByteArray> roleNames() const override;

    QStringList categories() const { return m_categories; }

    QString categoryFilter() const { return m_categoryFilter; }
    void setCategoryFilter(const QString& filter);

    QString searchFilter() const { return m_searchFilter; }
    void setSearchFilter(const QString& filter);

    int count() const { return static_cast<int>(m_filteredIndices.size()); }

    Q_INVOKABLE void reloadApplications();
    Q_INVOKABLE void launch(int index);
    Q_INVOKABLE void launchById(const QString& id);

signals:
    void categoriesChanged();
    void categoryFilterChanged();
    void searchFilterChanged();
    void countChanged();
    void scanFinished();

private:
    void updateFilter();
    void registerLinuxApps();
    void registerLinuxApp(const QString& id, const QString& name, const QString& exec, const QString& category, const QString& iconResource);
    void crawlStartMenuDirectory(const QString& dirPath, const QString& parentCategory, int depth = 0);
    bool resolveShellLink(const QString& lnkPath, AppEntry& outEntry);
    QImage extractBinaryIcon(const QString& filePath, int iconIndex);

    QVector<AppEntry> m_apps;
    std::vector<int> m_filteredIndices;
    QString m_categoryFilter{ "All Applications" };
    QString m_searchFilter;
    QStringList m_categories;
    AppIconProvider* m_iconProvider{ nullptr };
};

} // namespace KWinWin::UI
