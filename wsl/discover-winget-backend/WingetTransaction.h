#pragma once

#include <Transaction/Transaction.h>

class WingetResource;

class WingetTransaction : public Transaction
{
    Q_OBJECT
public:
    WingetTransaction(WingetResource *app, Role role);
    WingetTransaction(WingetResource *app, const AddonList &addons, Role role);

    void cancel() override;
    void proceed() override;

private:
    void execute();

    WingetResource *m_app;
    bool m_cancelled = false;
};
