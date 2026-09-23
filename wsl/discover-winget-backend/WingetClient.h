#pragma once

#include <QJsonObject>
#include <QJsonArray>
#include <QString>
#include <functional>

class WingetClient
{
public:
    using ProgressCallback = std::function<void(const QString &phase, int progress, const QString &message)>;

    static QString socketPath();
    static bool isProxyAvailable();
    static void ensureProxyRunning();

    static QJsonObject sendRequest(const QJsonObject &req, int timeoutMs = 30000);
    static QJsonObject executeWithProgress(const QJsonObject &req, ProgressCallback progressCb, int timeoutMs = 600000);

    static QJsonArray search(const QString &query, int count = 30);
    static QJsonObject show(const QString &packageId);
    static QJsonArray list(const QString &query = QString());
    static QJsonArray upgradable();
    static QJsonObject install(const QString &packageId, ProgressCallback progressCb = nullptr, int timeoutMs = 600000);
    static QJsonObject upgrade(const QString &packageId, ProgressCallback progressCb = nullptr, int timeoutMs = 600000);
    static QJsonObject uninstall(const QString &packageId, ProgressCallback progressCb = nullptr, int timeoutMs = 300000);
};
