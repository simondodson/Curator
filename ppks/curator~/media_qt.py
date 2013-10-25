import sys

import ppk

from PySide import QtGui, QtCore

class Menu(QtGui.QWidget):
    def __init__(self):
        super().__init__()
        self.setup()

    def setup(self):
        self.pool = pool = ppk.Pool()
        pool.include()

        self.tree = tree = QtGui.QTreeWidget()
        tree.setAnimated(True)
        tree.setHeaderHidden(True)

        side = QtGui.QVBoxLayout()
        #side.addStretch(1)
        #side.setStretch(1)
        def button(icon, hint):
            but = QtGui.QToolButton()
            if icon:
                but.setIcon(icon)
                but.setIconSize(QtCore.QSize(500, 500))
            but.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Expanding)
            side.addWidget(but)

        button(None, None)
        button(pool['qicon:media/spin.png'], 'lol')

        grid = QtGui.QGridLayout()
        grid.setSpacing(3)
        grid.addWidget(tree, 0, 0)
        grid.addLayout(side, 0, 1)

        self.setLayout(grid)
        self.setWindowTitle('Media')
        self.show()

def main():
    app = QtGui.QApplication(sys.argv)
    menu = Menu()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()