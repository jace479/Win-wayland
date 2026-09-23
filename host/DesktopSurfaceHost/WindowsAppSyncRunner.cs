using System;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using System.Threading.Tasks;

namespace NtPlasma.DesktopSurfaceHost;

/// <summary>
/// Watches Windows Start Menu program folders for changes (e.g. after setup.exe installs an app)
/// and automatically synchronizes application shortcuts into the KDE Plasma launcher catalog.
/// </summary>
internal sealed class WindowsAppSyncRunner : IDisposable
{
    private readonly List<FileSystemWatcher> _watchers = new();
    private readonly System.Threading.Timer _debounceTimer;
    private readonly System.Threading.Timer _periodicTimer;
    private int _isSyncing = 0;

    public WindowsAppSyncRunner()
    {
        _debounceTimer = new System.Threading.Timer(_ => TriggerSync(), null, Timeout.Infinite, Timeout.Infinite);

        // Periodic background sync every 60 minutes
        _periodicTimer = new System.Threading.Timer(_ => TriggerSync(), null, TimeSpan.FromMinutes(60), TimeSpan.FromMinutes(60));

        var paths = new[]
        {
            Environment.GetFolderPath(Environment.SpecialFolder.CommonPrograms),
            Environment.GetFolderPath(Environment.SpecialFolder.Programs)
        };

        foreach (var path in paths)
        {
            if (Directory.Exists(path))
            {
                try
                {
                    var watcher = new FileSystemWatcher(path)
                    {
                        IncludeSubdirectories = true,
                        NotifyFilter = NotifyFilters.FileName | NotifyFilters.LastWrite,
                        Filter = "*.lnk"
                    };
                    watcher.Created += (_, _) => OnChanged();
                    watcher.Deleted += (_, _) => OnChanged();
                    watcher.Changed += (_, _) => OnChanged();
                    watcher.EnableRaisingEvents = true;
                    _watchers.Add(watcher);
                }
                catch { }
            }
        }
    }

    private void OnChanged()
    {
        // Debounce by 4 seconds so multi-file installer writes coalesce into a single sync run
        _debounceTimer.Change(4000, Timeout.Infinite);
    }

    public void TriggerSync()
    {
        if (Interlocked.CompareExchange(ref _isSyncing, 1, 0) != 0)
        {
            return;
        }

        Task.Run(() =>
        {
            try
            {
                Program.HandleSync();
            }
            catch { }
            finally
            {
                Interlocked.Exchange(ref _isSyncing, 0);
            }
        });
    }

    public void Dispose()
    {
        _debounceTimer.Dispose();
        _periodicTimer.Dispose();
        foreach (var w in _watchers)
        {
            w.Dispose();
        }
        _watchers.Clear();
    }
}
