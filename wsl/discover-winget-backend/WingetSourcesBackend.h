#pragma once

#include <resources/AbstractSourcesBackend.h>
#include <QStandardItemModel>

class WingetSourcesBackend : public AbstractSourcesBackend
{
    Q_OBJECT
public:
    explicit WingetSourcesBackend(AbstractResourcesBackend *parent);

    QAbstractItemModel *sources() override;
    bool addSource(const QString &id) override;
    bool removeSource(const QString &id) override;
    QString idDescription() override;
    QVariantList actions() const override;
    bool supportsAdding() const override;
    bool canMoveSources() const override;
    bool moveSource(const QString &sourceId, int delta) override;

private:
    QStandardItemModel *m_sources;
};
