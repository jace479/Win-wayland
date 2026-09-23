using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Windows.UI.Notifications;
using Windows.UI.Notifications.Management;

namespace NtPlasma.DesktopSurfaceHost;

/// <summary>
/// Bridges notifications from the Windows host to KDE Plasma's notification daemon (via kde-task-bridge.py).
/// Listens to real-time Windows toast notifications via UserNotificationListener.
/// </summary>
internal sealed class NotificationBridge : IDisposable
{
    private readonly WindowsTaskTracker? _taskTracker;
    private readonly HashSet<uint> _seenNotificationIds = new();
    private CancellationTokenSource? _cts;

    public static NotificationBridge? Instance { get; private set; }

    public NotificationBridge(WindowsTaskTracker? taskTracker)
    {
        _taskTracker = taskTracker;
        Instance = this;
        StartListening();
    }

    private void StartListening()
    {
        _cts = new CancellationTokenSource();
        Task.Run(() => ListenWorkerAsync(_cts.Token));
    }

    private async Task ListenWorkerAsync(CancellationToken ct)
    {
        try
        {
            var listener = UserNotificationListener.Current;
            var access = await listener.RequestAccessAsync();
            if (access != UserNotificationListenerAccessStatus.Allowed)
            {
                DiagnosticLog.Warn("NotificationBridge", $"UserNotificationListener access not allowed: {access}");
                return;
            }

            // Populate initial existing notifications so we don't replay old ones
            var initial = await listener.GetNotificationsAsync(NotificationKinds.Toast);
            foreach (var notif in initial)
            {
                _seenNotificationIds.Add(notif.Id);
            }
            DiagnosticLog.Info("NotificationBridge", $"UserNotificationListener active. Initialized with {initial.Count} existing toasts.");

            // Poll every 1.5s for newly arriving toast notifications
            while (!ct.IsCancellationRequested)
            {
                await Task.Delay(1500, ct);

                var toasts = await listener.GetNotificationsAsync(NotificationKinds.Toast);
                foreach (var notif in toasts)
                {
                    if (_seenNotificationIds.Add(notif.Id))
                    {
                        ProcessNotification(notif);
                    }
                }
            }
        }
        catch (OperationCanceledException) { }
        catch (Exception ex)
        {
            DiagnosticLog.Warn("NotificationBridge", $"Toast listener error: {ex.Message}");
        }
    }

    private void ProcessNotification(UserNotification notif)
    {
        try
        {
            var appName = notif.AppInfo?.DisplayInfo?.DisplayName ?? "Windows";
            var binding = notif.Notification?.Visual?.GetBinding(KnownNotificationBindings.ToastGeneric);
            if (binding == null) return;

            var texts = binding.GetTextElements().Select(t => t.Text).ToList();
            if (texts.Count == 0) return;

            var title = texts[0];
            var body = texts.Count > 1 ? string.Join("\n", texts.Skip(1)) : "";

            if (string.IsNullOrWhiteSpace(title) && string.IsNullOrWhiteSpace(body)) return;

            Notify(title, body, appName);
        }
        catch (Exception ex)
        {
            DiagnosticLog.Warn("NotificationBridge", $"Error extracting toast text: {ex.Message}");
        }
    }

    /// <summary>
    /// Dispatches a notification to KDE Plasma.
    /// </summary>
    public void Notify(string title, string body, string appName = "Windows", string urgency = "normal", string icon = "preferences-desktop-notification")
    {
        if (_taskTracker != null)
        {
            _taskTracker.SendNotification(title, body, appName, urgency, icon);
        }
    }

    public static void Send(string title, string body, string appName = "Windows", string urgency = "normal", string icon = "preferences-desktop-notification")
    {
        Instance?.Notify(title, body, appName, urgency, icon);
    }

    public void Dispose()
    {
        _cts?.Cancel();
        _cts?.Dispose();
        _cts = null;
    }
}
