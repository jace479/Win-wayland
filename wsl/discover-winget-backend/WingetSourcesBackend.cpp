#include "WingetSourcesBackend.h"
#include <QStandardItem>

WingetSourcesBackend::WingetSourcesBackend(AbstractResourcesBackend *parent)
    : AbstractSourcesBackend(parent)
    , m_sources(new QStandardItemModel(this))
{
    QStandardItem *it = new QStandardItem(QStringLiteral("Windows Package Manager (winget)"));
    it->setData(QStringLiteral("winget"), AbstractSourcesBackend::IdRole);
    it->setData(QStringLiteral("Windows application repository managed via winget.exe"), Qt::ToolTipRole);
    it->setCheckable(true);
    it->setCheckState(Qt::Checked);
    m_sources->appendRow(it);
}

QAbstractItemModel *WingetSourcesBackend::sources()
{
    return m_sources;
}

bool WingetSourcesBackend::addSource(const QString &id)
{
    Q_UNUSED(id);
    return false;
}

bool WingetSourcesBackend::removeSource(const QString &id)
{
    Q_UNUSED(id);
    return false;
}

QString WingetSourcesBackend::idDescription()
{
    return QStringLiteral("winget");
}

QVariantList WingetSourcesBackend::actions() const
{
    return {};
}

bool WingetSourcesBackend::supportsAdding() const
{
    return false;
}

bool WingetSourcesBackend::canMoveSources() const
{
    return false;
}

bool WingetSourcesBackend::moveSource(const QString &sourceId, int delta)
{
    Q_UNUSED(sourceId);
    Q_UNUSED(delta);
    return false;
}

#include "moc_WingetSourcesBackend.cpp"
