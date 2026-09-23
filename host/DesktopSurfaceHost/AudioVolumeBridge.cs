using System;
using System.Diagnostics;
using System.Runtime.InteropServices;

namespace NtPlasma.DesktopSurfaceHost;

/// <summary>
/// Controls Windows Core Audio master volume, mute state, and media key playback.
/// Uses standard Core Audio COM interfaces (IMMDeviceEnumerator, IAudioEndpointVolume).
/// </summary>
public sealed class AudioVolumeBridge : IDisposable
{
    private const int eRender = 0;
    private const int eMultimedia = 1;
    private const int CLSCTX_ALL = 23;

    private const byte VK_VOLUME_MUTE = 0xAD;
    private const byte VK_VOLUME_DOWN = 0xAE;
    private const byte VK_VOLUME_UP = 0xAF;
    private const byte VK_MEDIA_NEXT_TRACK = 0xB0;
    private const byte VK_MEDIA_PREV_TRACK = 0xB1;
    private const byte VK_MEDIA_STOP = 0xB2;
    private const byte VK_MEDIA_PLAY_PAUSE = 0xB3;
    private const uint KEYEVENTF_KEYUP = 0x0002;

    [DllImport("user32.dll")]
    private static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, nint dwExtraInfo);

    [ComImport]
    [Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
    private class MMDeviceEnumeratorComObject { }

    [Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IMMDeviceEnumerator
    {
        int EnumAudioEndpoints(int dataFlow, int stateMask, out nint devices);
        int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice endpoint);
        int GetDevice(string pwstrId, out IMMDevice endpoint);
        int RegisterEndpointNotificationCallback(nint pClient);
        int UnregisterEndpointNotificationCallback(nint pClient);
    }

    [Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IMMDevice
    {
        int Activate(ref Guid iid, int dwClsCtx, nint pActivationParams, [MarshalAs(UnmanagedType.IUnknown)] out object ppInterface);
    }

    [Guid("657804FA-D6AD-4496-8560-E5D526D0C185"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IAudioEndpointVolumeCallback
    {
        int OnNotify(nint pNotify);
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct AUDIO_VOLUME_NOTIFICATION_DATA
    {
        public Guid guidEventContext;
        public int bMuted;
        public float fMasterVolume;
        public uint nChannels;
    }

    [Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IAudioEndpointVolume
    {
        int RegisterControlChangeNotify(IAudioEndpointVolumeCallback pNotify);
        int UnregisterControlChangeNotify(IAudioEndpointVolumeCallback pNotify);
        int GetChannelCount(out uint pnChannelCount);
        int SetMasterVolumeLevel(float fLevelDB, ref Guid pguidEventContext);
        int SetMasterVolumeLevelScalar(float fLevel, ref Guid pguidEventContext);
        int GetMasterVolumeLevel(out float pfLevelDB);
        int GetMasterVolumeLevelScalar(out float pfLevel);
        int SetChannelVolumeLevel(uint nChannel, float fLevelDB, ref Guid pguidEventContext);
        int SetChannelVolumeLevelScalar(uint nChannel, float fLevel, ref Guid pguidEventContext);
        int GetChannelVolumeLevel(uint nChannel, out float pfLevelDB);
        int GetChannelVolumeLevelScalar(uint nChannel, out float pfLevel);
        int SetMute(int bMute, ref Guid pguidEventContext);
        int GetMute(out int pbMute);
        int GetVolumeStepInfo(out uint pnStep, out uint pnStepCount);
        int VolumeStepUp(ref Guid pguidEventContext);
        int VolumeStepDown(ref Guid pguidEventContext);
        int QueryHardwareSupport(out uint pdwHardwareSupportMask);
        int GetVolumeRange(out float pflVolumeMindB, out float pflVolumeMaxdB, out float pflVolumeIncrementdB);
    }

    private static readonly Guid IID_IAudioEndpointVolume = new("5CDF2C82-841E-4546-9722-0CF74078229A");

    public event Action<float, bool>? VolumeChanged;

    private sealed class VolumeCallbackHandler : IAudioEndpointVolumeCallback
    {
        private readonly AudioVolumeBridge _bridge;
        public VolumeCallbackHandler(AudioVolumeBridge bridge) => _bridge = bridge;

        public int OnNotify(nint pNotify)
        {
            if (pNotify != nint.Zero)
            {
                try
                {
                    var data = Marshal.PtrToStructure<AUDIO_VOLUME_NOTIFICATION_DATA>(pNotify);
                    _bridge.VolumeChanged?.Invoke(data.fMasterVolume, data.bMuted != 0);
                }
                catch { }
            }
            return 0;
        }
    }

    private IAudioEndpointVolume? _monitorEndpoint;
    private VolumeCallbackHandler? _callbackHandler;

    public void StartMonitoring()
    {
        if (_monitorEndpoint == null)
        {
            _monitorEndpoint = GetVolumeInterface();
            if (_monitorEndpoint != null)
            {
                _callbackHandler = new VolumeCallbackHandler(this);
                _monitorEndpoint.RegisterControlChangeNotify(_callbackHandler);
                DiagnosticLog.Info("AudioBridge", "Audio volume change monitor registered.");
            }
        }
    }

    private IAudioEndpointVolume? GetVolumeInterface()
    {
        try
        {
            var enumerator = (IMMDeviceEnumerator)new MMDeviceEnumeratorComObject();
            int hr = enumerator.GetDefaultAudioEndpoint(eRender, eMultimedia, out var device);
            if (hr != 0 || device == null) return null;

            var iid = IID_IAudioEndpointVolume;
            hr = device.Activate(ref iid, CLSCTX_ALL, nint.Zero, out var iface);
            if (hr != 0 || iface == null) return null;

            return (IAudioEndpointVolume)iface;
        }
        catch (Exception ex)
        {
            DiagnosticLog.Warn("AudioBridge", $"Failed to obtain IAudioEndpointVolume: {ex.Message}");
            return null;
        }
    }

    public float GetMasterVolume()
    {
        var vol = GetVolumeInterface();
        if (vol != null)
        {
            try
            {
                vol.GetMasterVolumeLevelScalar(out var level);
                return level;
            }
            finally
            {
                Marshal.ReleaseComObject(vol);
            }
        }
        return 0.5f;
    }

    public void SetMasterVolume(float level)
    {
        level = Math.Clamp(level, 0.0f, 1.0f);
        var vol = GetVolumeInterface();
        if (vol != null)
        {
            try
            {
                var guid = Guid.Empty;
                vol.SetMasterVolumeLevelScalar(level, ref guid);
            }
            finally
            {
                Marshal.ReleaseComObject(vol);
            }
        }
    }

    public bool IsMuted()
    {
        var vol = GetVolumeInterface();
        if (vol != null)
        {
            try
            {
                vol.GetMute(out var muted);
                return muted != 0;
            }
            finally
            {
                Marshal.ReleaseComObject(vol);
            }
        }
        return false;
    }

    public void SetMute(bool mute)
    {
        var vol = GetVolumeInterface();
        if (vol != null)
        {
            try
            {
                var guid = Guid.Empty;
                vol.SetMute(mute ? 1 : 0, ref guid);
            }
            finally
            {
                Marshal.ReleaseComObject(vol);
            }
        }
    }

    public void ToggleMute()
    {
        var muted = IsMuted();
        SetMute(!muted);
    }

    public void VolumeUp(float step = 0.04f)
    {
        var cur = GetMasterVolume();
        SetMasterVolume(cur + step);
    }

    public void VolumeDown(float step = 0.04f)
    {
        var cur = GetMasterVolume();
        SetMasterVolume(cur - step);
    }

    public static void SendMediaKey(byte vk)
    {
        keybd_event(vk, 0, 0, nint.Zero);
        keybd_event(vk, 0, KEYEVENTF_KEYUP, nint.Zero);
    }

    public static void PlayPause() => SendMediaKey(VK_MEDIA_PLAY_PAUSE);
    public static void NextTrack() => SendMediaKey(VK_MEDIA_NEXT_TRACK);
    public static void PreviousTrack() => SendMediaKey(VK_MEDIA_PREV_TRACK);

    public void Dispose()
    {
        if (_monitorEndpoint != null)
        {
            if (_callbackHandler != null)
            {
                try
                {
                    _monitorEndpoint.UnregisterControlChangeNotify(_callbackHandler);
                }
                catch { }
                _callbackHandler = null;
            }
            Marshal.ReleaseComObject(_monitorEndpoint);
            _monitorEndpoint = null;
        }
    }
}
