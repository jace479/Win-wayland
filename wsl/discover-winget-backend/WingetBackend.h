#pragma once

#include <resources/AbstractResourcesBackend.h>
#include <QHash>

class StandardBackendUpdater;
class WingetResource;

class WingetBackend : public AbstractResourcesBackend
{
    Q_OBJECT
public:
    explicit WingetBackend(QObject *parent = nullptr);
    ~WingetBackend() override;

    int updatesCount() const override;
    AbstractBackendUpdater *backendUpdater() const override;
    AbstractReviewsBackend *reviewsBackend() const override;
    ResultsStream *search(const AbstractResourcesBackend::Filters &search) override;
    ResultsStream *findResourceByPackageName(const QUrl &search);

    Transaction *installApplication(AbstractResource *app) override;
    Transaction *installApplication(AbstractResource *app, const AddonList &addons) override;
    Transaction *removeApplication(AbstractResource *app) override;

    void checkForUpdates() override;
    QString displayName() const override;
    bool hasApplications() const override;
    bool isValid() const override;
    int fetchingUpdatesProgress() const override;

    WingetResource *resourceForPackage(const QString &id, const QString &name = QString());

private Q_SLOTS:
    void populateInstalled();
    void onUpdatesFound(const QJsonArray &packages);

private:
    StandardBackendUpdater *m_updater;
    QHash<QString, WingetResource *> m_resources;
    bool m_fetchingUpdates = false;
};
