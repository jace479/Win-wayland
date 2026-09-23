import sys
import time
from PyQt5 import QtWidgets, QtCore

app = QtWidgets.QApplication(sys.argv)
w = QtWidgets.QMainWindow()
w.setWindowTitle("WinKDE Probe Window")
w.resize(300, 200)
w.show()
print("WinKDE Probe Window opened, winId:", int(w.winId()), flush=True)

# Run for 2 seconds then exit
QtCore.QTimer.singleShot(2000, app.quit)
sys.exit(app.exec_())
