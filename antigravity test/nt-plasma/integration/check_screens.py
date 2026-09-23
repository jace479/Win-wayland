from PyQt5.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)
screens = app.screens()
print(f"Total screens detected in Qt/KDE: {len(screens)}")
for i, s in enumerate(screens):
    geo = s.geometry()
    print(f"  Screen #{i}: {geo.width()}x{geo.height()} at +{geo.x()}+{geo.y()}")
