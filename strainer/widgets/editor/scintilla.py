from PyQt5.Qsci import QsciScintilla
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QColor

from ...actions import UndoEdit, RedoEdit, CutContent, CopyContent, PasteContent, DeleteContent, FindContent, SelectAllContent
from ...controls import EditMenu
from ...types import FindDirection, FindOptions, FindQuery
from ..base import Menu, MenuMixin, Find, FindMixin
from .lexer import SieveLexer
from .styles import TagStyle


class Editor(MenuMixin, FindMixin, QsciScintilla):
    _menu = Menu(
        EditMenu,
        {
            UndoEdit: 'undo', RedoEdit: 'redo',
            CutContent: 'cut', CopyContent: 'copy', PasteContent: 'paste',
            DeleteContent: 'removeSelectedText', SelectAllContent: 'selectAll',
        },
        ('selectionChanged', 'textChanged')
    )
    _find = Find(FindContent, FindOptions(True, True, True, True))
    _pageMap = {'elsif': 'if', 'else': 'if'}

    def __init__(self, parent):
        super().__init__(parent)
        self.close()

        self.setMinimumSize(QSize(300, 200))
        self.setScrollWidth(300)
        self.setScrollWidthTracking(True)

        self.setUtf8(True)
        self.setEolMode(QsciScintilla.EolWindows)

        self.setMarginLineNumbers(0, True)
        self.linesChanged.connect(lambda: self.setMarginWidth(0, f'0{self.lines()}'))

        self.setAutoIndent(True)
        self.setTabWidth(2)
        self.setTabIndents(True)
        self.setBackspaceUnindents(True)
        self.setIndentationsUseTabs(False)
        self.setIndentationGuides(True)

        self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)

        self.setLexer(SieveLexer(self))
        self.SCN_HOTSPOTCLICK.connect(self.onHotspotClicked)
        # QApplication.clipboard().dataChanged.connect(updateMenu)  # doesn't seem to be working...?

        self.indicatorDefine(QsciScintilla.IndicatorStyle.DotsIndicator, 0)
        self.setIndicatorForegroundColor(QColor('red'), 0)
        self.indicatorDefine(QsciScintilla.IndicatorStyle.TriangleCharacterIndicator, 1)
        self.setIndicatorForegroundColor(QColor('red'), 1)

    def onHotspotClicked(self, position, modifiers):
        position = self.SendScintilla(QsciScintilla.SCI_WORDSTARTPOSITION, position, True)
        if self.text(position - 1, position) == ':':
            position -= 1
        for style, value in self.lexer().scan(position):
            category = style.name.lower()
            if isinstance(style, TagStyle):
                page, category = category, 'operators'
            else:
                page = value.decode('ascii').lower()
                page = self._pageMap.get(page, page)
            self.window().reference().browse(category, page)
            break

    def sizeHint(self):
        return QSize(750, 600)

    def open(self, text):
        self.setText(text)
        self.setReadOnly(False)
        self.setFocus(Qt.OtherFocusReason)
        self.setModified(False)
        self.updateMenu()

    def selectAll(self):
        super().selectAll(True)

    def setParseError(self, line, col, length=1):
        self.SendScintilla(QsciScintilla.SCI_SETINDICATORCURRENT, 1)
        self.SendScintilla(QsciScintilla.SCI_INDICATORCLEARRANGE, 0, self.length())
        if line >= 0 and col >= 0:
            # check if max() is still needed after sievelib #92 is merged
            start = max(self.positionFromLineIndex(line, col) - length, 0)
            self.SendScintilla(QsciScintilla.SCI_INDICATORFILLRANGE, start, length)

    def close(self):
        self.setText('')
        self.setReadOnly(True)
        self.setModified(False)
        self.updateMenu()

    def _findFirst(self, query: FindQuery):
        opts = query.options
        args = (query.expression, opts.regularExpression, opts.caseSensitive, opts.wholeWords)
        kwargs = {'forward': query.direction == FindDirection.Forward, 'show': True, 'cxx11': True}
        if opts.inSelection:
            result = QsciScintilla.findFirstInSelection(self, *args, **kwargs)
        else:
            result = QsciScintilla.findFirst(self, *args, True, **kwargs)
        query.callback(result)

    def _findNext(self, query: FindQuery):
        query.callback(QsciScintilla.findNext(self))

    def _cancelFind(self):
        QsciScintilla.cancelFind(self)
