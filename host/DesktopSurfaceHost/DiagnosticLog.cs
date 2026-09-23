using System;
using System.IO;
using System.Threading;

namespace NtPlasma.DesktopSurfaceHost;

/// <summary>
/// Centralized diagnostic logging for ntKDE.
/// Writes structured timestamped log entries to %TEMP%/ntkde/ with automatic file rotation.
/// Thread-safe. FATAL entries are also persisted to a dedicated error log.
/// </summary>
internal static class DiagnosticLog
{
    private static readonly string LogDirectory;
    private static readonly string SessionLogPath;
    private static readonly string ErrorLogPath;
    private static readonly object WriteLock = new();
    private static readonly DateTime SessionStart = DateTime.UtcNow;
    private const int MaxSessionFiles = 5;

    static DiagnosticLog()
    {
        LogDirectory = Path.Combine(Path.GetTempPath(), "ntkde");
        Directory.CreateDirectory(LogDirectory);

        var dateTag = DateTime.Now.ToString("yyyy-MM-dd_HHmmss");
        SessionLogPath = Path.Combine(LogDirectory, $"ntkde-{dateTag}.log");
        ErrorLogPath = Path.Combine(LogDirectory, "ntkde-error.log");

        RotateOldLogs();

        WriteRaw($"=== ntKDE Session Started at {DateTime.Now:O} ===");
        WriteRaw($"    OS: {Environment.OSVersion}");
        WriteRaw($"    CLR: {Environment.Version}");
        WriteRaw($"    PID: {Environment.ProcessId}");
        WriteRaw($"    User: {Environment.UserName}");
        WriteRaw($"    LogFile: {SessionLogPath}");
        WriteRaw("===");
    }

    /// <summary>Path to the current session log file.</summary>
    public static string CurrentLogPath => SessionLogPath;

    /// <summary>Path to the log directory.</summary>
    public static string LogDir => LogDirectory;

    public static void Info(string message)
    {
        Write("INFO", message);
    }

    public static void Info(string component, string message)
    {
        Write("INFO", $"[{component}] {message}");
    }

    public static void Warn(string message)
    {
        Write("WARN", message);
    }

    public static void Warn(string component, string message)
    {
        Write("WARN", $"[{component}] {message}");
    }

    public static void Error(string message)
    {
        Write("ERROR", message);
    }

    public static void Error(string component, string message)
    {
        Write("ERROR", $"[{component}] {message}");
    }

    public static void Error(string component, string message, Exception ex)
    {
        Write("ERROR", $"[{component}] {message}: {ex.Message}");
    }

    public static void Fatal(string message)
    {
        Write("FATAL", message);
        WriteFatalLog(message);
    }

    public static void Fatal(string message, Exception ex)
    {
        var full = $"{message}\n{ex}";
        Write("FATAL", full);
        WriteFatalLog(full);
    }

    /// <summary>
    /// Records a lifecycle state transition for diagnostic tracing.
    /// </summary>
    public static void Transition(string component, string from, string to, string reason)
    {
        Write("INFO", $"[{component}] {from} -> {to} ({reason})");
    }

    private static void Write(string level, string message)
    {
        var timestamp = DateTime.Now.ToString("HH:mm:ss.fff");
        var line = $"{timestamp} [{level,-5}] {message}";

        // Always echo to console for development convenience
        Console.WriteLine($"[ntKDE] {message}");

        lock (WriteLock)
        {
            try
            {
                File.AppendAllText(SessionLogPath, line + Environment.NewLine);
            }
            catch
            {
                // Cannot lose the process over a logging failure
            }
        }
    }

    private static void WriteRaw(string line)
    {
        lock (WriteLock)
        {
            try
            {
                File.AppendAllText(SessionLogPath, line + Environment.NewLine);
            }
            catch { }
        }
    }

    private static void WriteFatalLog(string message)
    {
        try
        {
            var entry = $"[{DateTime.Now:O}] {message}{Environment.NewLine}";
            File.AppendAllText(ErrorLogPath, entry);
        }
        catch { }
    }

    private static void RotateOldLogs()
    {
        try
        {
            var files = Directory.GetFiles(LogDirectory, "ntkde-*.log");
            if (files.Length <= MaxSessionFiles) return;

            Array.Sort(files);
            var toDelete = files.Length - MaxSessionFiles;
            for (var i = 0; i < toDelete; i++)
            {
                // Don't delete the error log
                if (Path.GetFileName(files[i]) == "ntkde-error.log") continue;
                try { File.Delete(files[i]); } catch { }
            }
        }
        catch { }
    }
}
