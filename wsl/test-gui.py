import sys
from PyQt5 import QtWidgets

app = QtWidgets.QApplication(sys.argv)
btn = QtWidgets.QPushButton("ntKDE Test Window - Click to Close")
btn.resize(500, 250)
btn.clicked.connect(app.quit)
btn.show()
sys.exit(app.exec_())
