#include "WingetClient.h"

#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QLocalSocket>
#include <QProcess>
#include <QStandardPaths>
#include <QThread>
#include <QDebug>

QString WingetClient::socketPath()
{
    return QDir::homePath() + QStringLiteral("/.local/state/nt-plasma/winget.sock");
}

bool WingetClient::isProxyAvailable()
{
    if (!QFile::exists(socketPath())) {
        return false;
    }
    QLocalSocket testSocket;
    testSocket.connectToServer(socketPath());
    if (testSocket.waitForConnected(200)) {
        testSocket.disconnectFromServer();
        return true;
    }
    // Stale socket file: clean it up
    QFile::remove(socketPath());
    return false;
}

void WingetClient::ensureProxyRunning()
{
    if (isProxyAvailable()) {
        return;
    }

    // Try starting winget-proxy.py in the background
    QStringList candidates = {
        QStringLiteral("/mnt/d/WinKDE/wsl/winget-proxy.py"),
        QDir::homePath() + QStringLiteral("/.local/bin/winget-proxy.py")
    };

    for (const QString &path : candidates) {
        if (QFile::exists(path)) {
            qDebug() << "[WingetBackend] Starting winget-proxy daemon from:" << path;
            QProcess::startDetached(QStringLiteral("python3"), {path});
            for (int i = 0; i < 20; ++i) {
                QThread::msleep(100);
                if (isProxyAvailable()) {
                    break;
                }
            }
            break;
        }
    }
}

QJsonObject WingetClient::sendRequest(const QJsonObject &req, int timeoutMs)
{
    ensureProxyRunning();

    QLocalSocket socket;
    socket.connectToServer(socketPath());
    if (!socket.waitForConnected(2000)) {
        qWarning() << "[WingetClient] Failed to connect to winget.sock:" << socket.errorString();
        QJsonObject err;
        err[QStringLiteral("ok")] = false;
        err[QStringLiteral("error")] = QStringLiteral("Cannot connect to winget proxy service");
        return err;
    }

    QByteArray requestData = QJsonDocument(req).toJson(QJsonDocument::Compact) + '\n';
    socket.write(requestData);
    if (!socket.waitForBytesWritten(2000)) {
        qWarning() << "[WingetClient] Failed to send request:" << socket.errorString();
        QJsonObject err;
        err[QStringLiteral("ok")] = false;
        err[QStringLiteral("error")] = QStringLiteral("Failed to write to winget proxy");
        return err;
    }

    QByteArray responseData;
    int elapsed = 0;
    while (socket.state() == QLocalSocket::ConnectedState && elapsed < timeoutMs) {
        if (socket.waitForReadyRead(500)) {
            responseData += socket.readAll();
            if (responseData.contains('\n')) {
                break;
            }
        }
        elapsed += 500;
    }

    socket.disconnectFromServer();

    if (responseData.isEmpty()) {
        QJsonObject err;
        err[QStringLiteral("ok")] = false;
        err[QStringLiteral("error")] = QStringLiteral("Empty response or timeout from winget proxy");
        return err;
    }

    QByteArray line = responseData.split('\n').first();
    QJsonParseError parseErr;
    QJsonDocument doc = QJsonDocument::fromJson(line, &parseErr);
    if (parseErr.error != QJsonParseError::NoError || !doc.isObject()) {
        qWarning() << "[WingetClient] JSON parse error:" << parseErr.errorString() << line;
        QJsonObject err;
        err[QStringLiteral("ok")] = false;
        err[QStringLiteral("error")] = parseErr.errorString();
        return err;
    }

    return doc.object();
}

QJsonArray WingetClient::search(const QString &query, int count)
{
    QJsonObject req;
    req[QStringLiteral("op")] = QStringLiteral("search");
    req[QStringLiteral("query")] = query;
    req[QStringLiteral("count")] = count;

    QJsonObject res = sendRequest(req, 30000);
    if (res.value(QStringLiteral("ok")).toBool()) {
        return res.value(QStringLiteral("results")).toArray();
    }
    return {};
}

QJsonObject WingetClient::show(const QString &packageId)
{
    QJsonObject req;
    req[QStringLiteral("op")] = QStringLiteral("show");
    req[QStringLiteral("id")] = packageId;

    QJsonObject res = sendRequest(req, 30000);
    if (res.value(QStringLiteral("ok")).toBool()) {
        return res.value(QStringLiteral("package")).toObject();
    }
    return {};
}

QJsonArray WingetClient::list(const QString &query)
{
    QJsonObject req;
    req[QStringLiteral("op")] = QStringLiteral("list");
    if (!query.isEmpty()) {
        req[QStringLiteral("query")] = query;
    }

    QJsonObject res = sendRequest(req, 45000);
    if (res.value(QStringLiteral("ok")).toBool()) {
        return res.value(QStringLiteral("packages")).toArray();
    }
    return {};
}

QJsonArray WingetClient::upgradable()
{
    QJsonObject req;
    req[QStringLiteral("op")] = QStringLiteral("upgradable");

    QJsonObject res = sendRequest(req, 45000);
    if (res.value(QStringLiteral("ok")).toBool()) {
        return res.value(QStringLiteral("packages")).toArray();
    }
    return {};
}

QJsonObject WingetClient::executeWithProgress(const QJsonObject &req, ProgressCallback progressCb, int timeoutMs)
{
    ensureProxyRunning();

    QLocalSocket socket;
    socket.connectToServer(socketPath());
    if (!socket.waitForConnected(3000)) {
        qWarning() << "[WingetClient] Failed to connect to winget.sock:" << socket.errorString();
        QJsonObject err;
        err[QStringLiteral("ok")] = false;
        err[QStringLiteral("error")] = QStringLiteral("Cannot connect to winget proxy service");
        return err;
    }

    QByteArray requestData = QJsonDocument(req).toJson(QJsonDocument::Compact) + '\n';
    socket.write(requestData);
    if (!socket.waitForBytesWritten(3000)) {
        qWarning() << "[WingetClient] Failed to send request:" << socket.errorString();
        QJsonObject err;
        err[QStringLiteral("ok")] = false;
        err[QStringLiteral("error")] = QStringLiteral("Failed to write to winget proxy");
        return err;
    }

    QByteArray buffer;
    QJsonObject finalResult;
    int elapsed = 0;

    while (socket.state() == QLocalSocket::ConnectedState && elapsed < timeoutMs) {
        if (socket.waitForReadyRead(500)) {
            buffer += socket.readAll();
            while (buffer.contains('\n')) {
                int idx = buffer.indexOf('\n');
                QByteArray line = buffer.left(idx).trimmed();
                buffer.remove(0, idx + 1);

                if (line.isEmpty()) continue;

                QJsonDocument doc = QJsonDocument::fromJson(line);
                if (!doc.isObject()) continue;

                QJsonObject obj = doc.object();
                QString type = obj.value(QStringLiteral("type")).toString();

                if (type == QLatin1String("progress")) {
                    if (progressCb) {
                        QString phase = obj.value(QStringLiteral("phase")).toString();
                        int progress = obj.value(QStringLiteral("progress")).toInt();
                        QString message = obj.value(QStringLiteral("message")).toString();
                        progressCb(phase, progress, message);
                    }
                } else if (type == QLatin1String("result") || obj.contains(QStringLiteral("ok"))) {
                    finalResult = obj;
                    socket.disconnectFromServer();
                    return finalResult;
                }
            }
        }
        elapsed += 500;
    }

    socket.disconnectFromServer();

    if (finalResult.isEmpty()) {
        finalResult[QStringLiteral("ok")] = false;
        finalResult[QStringLiteral("error")] = QStringLiteral("Operation timed out");
    }
    return finalResult;
}

QJsonObject WingetClient::install(const QString &packageId, ProgressCallback progressCb, int timeoutMs)
{
    QJsonObject req;
    req[QStringLiteral("op")] = QStringLiteral("install");
    req[QStringLiteral("id")] = packageId;
    if (progressCb) {
        return executeWithProgress(req, progressCb, timeoutMs);
    }
    return sendRequest(req, timeoutMs);
}

QJsonObject WingetClient::upgrade(const QString &packageId, ProgressCallback progressCb, int timeoutMs)
{
    QJsonObject req;
    req[QStringLiteral("op")] = QStringLiteral("upgrade");
    req[QStringLiteral("id")] = packageId;
    if (progressCb) {
        return executeWithProgress(req, progressCb, timeoutMs);
    }
    return sendRequest(req, timeoutMs);
}

QJsonObject WingetClient::uninstall(const QString &packageId, ProgressCallback progressCb, int timeoutMs)
{
    QJsonObject req;
    req[QStringLiteral("op")] = QStringLiteral("uninstall");
    req[QStringLiteral("id")] = packageId;
    if (progressCb) {
        return executeWithProgress(req, progressCb, timeoutMs);
    }
    return sendRequest(req, timeoutMs);
}
