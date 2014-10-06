# copyright: utf-8
#
# Copyright (C) 2013, Niklas Rosenstein
# All rights reserved.

import os
import sys
import c4d
import c4dtools
import functools

from c4d import BIT_ACTIVE, BFM_INPUT_DOUBLECLICK, ID_TREEVIEW_CONTEXT_RESET,\
        EVMSG_CHANGE, BFM_CORE_UPDATECOMMANDS, CallCommand, SpecialEventAdd,\
        BaseContainer, GePluginMessage
from c4d.documents import BaseDocument, GetFirstDocument, GetActiveDocument,\
        SetActiveDocument, InsertBaseDocument
from c4d.plugins import GetWorldPluginData, SetWorldPluginData
from operator import xor
from time import time

res, importer = c4dtools.prepare(__file__, __res__)

ID_DATA = 1030336
ID_WITHMENUBAR = 1000

SPMSG_QUICKDOCS_CLOSE = 1030337
PLMSG_QUICKDOCS_TOGGLEMENUBAR = 1030338

GetPlData = lambda: GetWorldPluginData(ID_DATA) or BaseContainer()
SetPlData = lambda x: SetWorldPluginData(ID_DATA, x, add=True)

class DocumentTreeModel(c4d.gui.TreeViewFunctions):

    def GetFirst(self, r, u):
        return GetFirstDocument()

    def GetNext(self, r, u, c):
        return c.GetNext()

    def GetPred(self, r, u, c):
        return c.GetPred()

    def GetName(self, r, u, c):
        return c.GetDocumentName()

    def IsSelected(self, r, u, c):
        return c == GetActiveDocument()

    def Select(self, r, u, c, m):
        if not self.IsSelected(r, u, c):
            SetActiveDocument(c)

    def MouseDown(self, r, u, c, n, m, b):
        if not c:
            bc = m['inputmsg']
            if bc[BFM_INPUT_DOUBLECLICK]:
                d = BaseDocument()
                CallCommand(12094) # New document.
                return True
        return False

    def DoubleClick(self, r, u, c, n, m):
        return True # Event handled.

    def DeletePressed(self, r, u):
        CallCommand(12664) # Close document.

    def CreateContextMenu(self, r, u, c, n, bc):
        bc.InsData(0, "")
        bc.SetString(*res.string.IDC_CONTEXT_TOGGLEMENUBAR.both)
        bc.SetString(*res.string.IDC_CONTEXT_CLOSEQD.both)

    def ContextMenuCall(self, r, u, c, n, i):
        if i == ID_TREEVIEW_CONTEXT_RESET:
            CallCommand(12390) # Close all documents.
            return True
        elif i == res.IDC_CONTEXT_TOGGLEMENUBAR:
            SpecialEventAdd(PLMSG_QUICKDOCS_TOGGLEMENUBAR)
            return True
        elif i == res.IDC_CONTEXT_CLOSEQD:
            SpecialEventAdd(SPMSG_QUICKDOCS_CLOSE)
        return False

class Dialog(c4d.gui.GeDialog):

    def __init__(self, with_menubar, toggled=None):
        super(Dialog, self).__init__()
        if not with_menubar:
            self.AddGadget(c4d.DIALOG_NOMENUBAR, 0)
        self.toggled = toggled
        self.tree = None

    def CreateLayout(self):
        return self.LoadDialogResource(res.DLG_MAIN)

    def InitValues(self):
        self.tree = self.FindCustomGui(res.ID_DOCTREE, c4d.CUSTOMGUI_TREEVIEW)
        if self.tree:
            self.tree.SetRoot(None, DocumentTreeModel(), None)
        return not not self.tree

    def CoreMessage(self, id, msg):
        if id in [BFM_CORE_UPDATECOMMANDS, EVMSG_CHANGE]:
            if self.tree: # Required for Mac
                self.tree.Refresh()
        elif id == SPMSG_QUICKDOCS_CLOSE:
            self.Close()
        elif id == PLMSG_QUICKDOCS_TOGGLEMENUBAR:
            if not self.toggled or time() - self.toggled > 0.5:
                self.Close()
                command.ToggleDialogMenubar()
            self.toggled = None
        return True

class DialogWrapper(object):

    def __init__(self):
        super(DialogWrapper, self).__init__()
        self._dlg = None
        self._changed = False

    @property
    def with_menubar(self):
        bc = GetPlData()
        return bc.GetBool(ID_WITHMENUBAR, True)

    @with_menubar.setter
    def with_menubar(self, x):
        if xor(self.with_menubar, x):
            self._changed = True
            bc = BaseContainer()
            bc.SetBool(ID_WITHMENUBAR, not not x)
            SetPlData(bc)

    @property
    def dlg(self):
        if not self._dlg or self._changed:
            if self._dlg and self._dlg.IsOpen():
                self._dlg.Close()
            self._dlg = Dialog(self.with_menubar, time() if self._changed else None)
            self._changed = False
        return self._dlg

    def Close(self):
        if self._dlg and self._dlg.IsOpen():
            self._dlg.Close()

    def Open(self, *args, **kwargs):
        return self.dlg.Open(*args, **kwargs)

    def Restore(self, *args, **kwargs):
        return self.dlg.Restore(*args, **kwargs)

class Command(c4dtools.plugins.Command):

    PLUGIN_ID = 1030336
    PLUGIN_NAME = res.string.IDC_QUICKDOCS()
    PLUGIN_HELP = res.string.IDC_QUICKDOCS_HELP()
    PLUGIN_INFO = c4d.PLUGINFLAG_COMMAND_HOTKEY
    PLUGIN_ICON = res.file('icon.png')

    _dlg = None
    execute_called = False

    @property
    def dlg(self):
        if not self._dlg:
            self._dlg = DialogWrapper()
        return self._dlg

    def ToggleDialogMenubar(self):
        self.dlg.with_menubar ^= True
        self.dlg.Open(c4d.DLG_TYPE_ASYNC, self.PLUGIN_ID)

    def Execute(self, doc):
        self.execute_called = True
        return self.dlg.Open(c4d.DLG_TYPE_ASYNC, self.PLUGIN_ID)

    def RestoreLayout(self, secret):
        if not self.execute_called:
            self.dlg.with_menubar = False
            self.execute_called = True
        return self.dlg.Restore(self.PLUGIN_ID, secret)

if __name__ == '__main__':
    command = Command()
    command.register()


