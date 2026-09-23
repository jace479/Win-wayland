#pragma once

#include <resources/AbstractResource.h>
#include <QJsonObject>
#include <QStringList>

class WingetResource : public AbstractResource
{
    Q_OBJECT
public:
    explicit WingetResource(const QString &id,
                            const QString &name,
                            AbstractResourcesBackend *parent);

    QString packageName() const override;
    QString name() const override;
    QString comment() override;
    QString longDescription() override;
    QVariant icon() const override;
    bool canExecute() const override;
    void invokeApplication() const override;
    AbstractResource::State state() override;
    void setState(AbstractResource::State state);
    bool hasCategory(const QString &category) const override;
    AbstractResource::Type type() const override;
    quint64 size() override;
    QJsonArray licenses() override;
    QString installedVersion() const override;
    QString availableVersion() const override;
    QString origin() const override;
    QString section() override;
    QString author() const override;
    QList<PackageState> addonsInformation() override;
    QString sourceIcon() const override;
    QDate releaseDate() const override;
    void fetchChangelog() override;
    QUrl url() const override;
    QUrl homepage() override;

    void setInstalledVersion(const QString &ver);
    void setAvailableVersion(const QString &ver);
    void setComment(const QString &comment);
    void setIconName(const QString &icon);
    void setAuthor(const QString &author);
    void updateFromDetails(const QJsonObject &details);
    void fetchDetails();

private:
    QString m_id;
    QString m_name;
    QString m_version;
    QString m_installedVersion;
    QString m_comment;
    QString m_description;
    QString m_author;
    QString m_homepage;
    QString m_license;
    QString m_iconName;
    QStringList m_categories;
    quint64 m_size = 0;
    AbstractResource::State m_state = AbstractResource::None;
    bool m_detailsFetched = false;
};
