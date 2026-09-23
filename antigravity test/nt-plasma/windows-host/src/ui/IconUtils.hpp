#pragma once

#include <QImage>
#include <QColor>
#include <windows.h>
#include <vector>

namespace KWinWin::UI {

inline QImage hiconToQImage(HICON hIcon)
{
    if (!hIcon) return {};

    ICONINFO info{};
    if (!GetIconInfo(hIcon, &info)) return {};

    BITMAP bmColor{};
    int width = 0;
    int height = 0;
    if (info.hbmColor) {
        GetObjectW(info.hbmColor, sizeof(bmColor), &bmColor);
        width = bmColor.bmWidth;
        height = bmColor.bmHeight;
    } else if (info.hbmMask) {
        BITMAP bmMask{};
        GetObjectW(info.hbmMask, sizeof(bmMask), &bmMask);
        width = bmMask.bmWidth;
        height = bmMask.bmHeight / 2;
    }

    if (width <= 0 || height <= 0 || width > 1024 || height > 1024) {
        if (info.hbmColor) DeleteObject(info.hbmColor);
        if (info.hbmMask) DeleteObject(info.hbmMask);
        return {};
    }

    HDC hdcScreen = GetDC(nullptr);
    HDC hdcMem = CreateCompatibleDC(hdcScreen);

    BITMAPINFO bmi{};
    bmi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    bmi.bmiHeader.biWidth = width;
    bmi.bmiHeader.biHeight = -height; // Top-down
    bmi.bmiHeader.biPlanes = 1;
    bmi.bmiHeader.biBitCount = 32;
    bmi.bmiHeader.biCompression = BI_RGB;

    QImage image(width, height, QImage::Format_ARGB32_Premultiplied);
    image.fill(0);

    if (info.hbmColor) {
        GetDIBits(hdcMem, info.hbmColor, 0, height, image.bits(), &bmi, DIB_RGB_COLORS);
    }

    // Check if the color bitmap contains non-zero alpha values
    bool hasAlpha = false;
    for (int y = 0; y < height; ++y) {
        const QRgb* line = reinterpret_cast<const QRgb*>(image.constScanLine(y));
        for (int x = 0; x < width; ++x) {
            if (qAlpha(line[x]) > 0) {
                hasAlpha = true;
                break;
            }
        }
        if (hasAlpha) break;
    }

    // If color bitmap has no alpha (standard 24-bit Win32 icon), apply the mask bitmap!
    if (!hasAlpha && info.hbmMask) {
        std::vector<uint32_t> maskBits(width * height, 0);
        GetDIBits(hdcMem, info.hbmMask, 0, height, maskBits.data(), &bmi, DIB_RGB_COLORS);

        for (int y = 0; y < height; ++y) {
            QRgb* line = reinterpret_cast<QRgb*>(image.scanLine(y));
            for (int x = 0; x < width; ++x) {
                uint32_t m = maskBits[y * width + x] & 0x00FFFFFF;
                int alpha = (m == 0) ? 255 : 0;
                line[x] = qRgba(qRed(line[x]), qGreen(line[x]), qBlue(line[x]), alpha);
            }
        }
    }

    DeleteDC(hdcMem);
    ReleaseDC(nullptr, hdcScreen);

    if (info.hbmColor) DeleteObject(info.hbmColor);
    if (info.hbmMask) DeleteObject(info.hbmMask);

    return image;
}

} // namespace KWinWin::UI
