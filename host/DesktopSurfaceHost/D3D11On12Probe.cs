using System.Runtime.InteropServices;

namespace NtPlasma.DesktopSurfaceHost;

internal static class D3D11On12Probe
{
    public static string Describe()
    {
        if (!OperatingSystem.IsWindows())
        {
            return "D3D11On12: Windows unavailable";
        }

        var library = LoadLibrary("d3d11.dll");
        if (library == nint.Zero)
        {
            return "D3D11On12: d3d11 runtime unavailable";
        }

        try
        {
            var entryPoint = GetProcAddress(library, "D3D11On12CreateDevice");
            return entryPoint == nint.Zero
                ? "D3D11On12: entry point unavailable"
                : "D3D11On12: device bridge available; texture wrapping pending";
        }
        finally
        {
            FreeLibrary(library);
        }
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern nint LoadLibrary(string fileName);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool FreeLibrary(nint module);

    [DllImport("kernel32.dll", CharSet = CharSet.Ansi, SetLastError = true)]
    private static extern nint GetProcAddress(nint module, string procedureName);
}