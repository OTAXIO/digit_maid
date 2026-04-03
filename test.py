import sys
from PyQt6.QtWidgets import QApplication, QLabel
from PyQt6.QtGui import QMovie, QPixmap, QTransform
from PyQt6.QtCore import QObject
app=QApplication(sys.argv)
movie = QMovie('resource/wisdel/可用素材/move.gif')
lbl = QLabel()
lbl.show()

def f(n=0):
    pix = movie.currentPixmap()
    transform = QTransform().scale(-1, 1)
    lbl.setPixmap(pix.transformed(transform))

movie.frameChanged.connect(f)

movie.start()
f(0)
app.exec()
