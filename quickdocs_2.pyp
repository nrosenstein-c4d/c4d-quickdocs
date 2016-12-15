# -*- coding: utf8 -*-
#
# Copyright (C) 2013-2015  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

__author__ = 'Niklas Rosenstein <rosensteinniklas (at) gmail.com>'
__version__ = '2.3.0'

import os, sys
import c4d
import operator
import functools

singleton = lambda x: x()

@singleton
class res:
    def __getitem__(self, name):
        value = getattr(self, name)
        return value, c4d.plugins.GeLoadString(value)
    def __call__(self, name):
        return c4d.plugins.GeLoadString(getattr(self, name))
    def file(self, *parts):
        return os.path.join(os.path.dirname(__file__), 'res', *parts)
    DLG_MAIN                  = 0
    ID_DOCTREE                = 1
    IDC_QUICKDOCS             = 2
    IDC_QUICKDOCS_HELP        = 3
    IDC_CONTEXT_TOGGLEMENUBAR = 4
    IDC_CONTEXT_CLOSEDIALOG   = 5
    IDC_CONTEXT_CLOSE         = 6
    IDC_CONTEXT_CLOSEALL      = 7
    IDC_CONTEXT_CLOSEOTHERS   = 8

@singleton
class PluginData:

    PLUGIN_ID = 1030336
    ID_WITHMENUBAR = 1000

    def get(self):
        data = c4d.plugins.GetWorldPluginData(self.PLUGIN_ID)
        if data is None:
            data = c4d.BaseContainer()
        return data

    def set(self, data):
        c4d.plugins.SetWorldPluginData(self.PLUGIN_ID, data, add=True)

PLMSG_QUICKDOCS_OPEN = 1033709
PLMSG_QUICKDOCS_CLOSE = 1030337
PLMSG_QUICKDOCS_TOGGLEMENUBAR = 1030338

CMD_NEW_DOCUMENT = 12094
CMD_CLOSE_DOCUMENT = 12664
CMD_CLOSE_DOCUMENTS = 12390

class DocumentTreeModel(c4d.gui.TreeViewFunctions):

    def GetFirst(self, root, ud):
        return c4d.documents.GetFirstDocument()

    def GetNext(self, root, ud, doc):
        return doc.GetNext()

    def GetPred(self, root, ud, doc):
        return doc.GetPred()

    def GetName(self, root, ud, doc):
        name = doc.GetDocumentName()
        if doc.GetChanged():
            name = name + " (*)"
        return name

    def IsSelected(self, root, ud, doc):
        return doc == c4d.documents.GetActiveDocument()

    def Select(self, root, ud, doc, mode):
        if mode in (c4d.SELECTION_ADD, c4d.SELECTION_NEW):
            c4d.documents.SetActiveDocument(doc)

    def MouseDown(self, root, ud, doc, column, minfo, right_button):
        msg = minfo['inputmsg']
        if msg[c4d.BFM_INPUT_DOUBLECLICK]:
            c4d.CallCommand(CMD_NEW_DOCUMENT)
            return True
        return False

    def DeletePressed(self, root, ud):
        c4d.CallCommand(CMD_CLOSE_DOCUMENT)

    def CreateContextMenu(self, root, ud, doc, column, bc):
        bc.FlushAll()
        bc.SetString(*res['IDC_CONTEXT_CLOSE'])
        bc.SetString(*res['IDC_CONTEXT_CLOSEALL'])
        bc.SetString(*res['IDC_CONTEXT_CLOSEOTHERS'])
        bc.InsData(0, "")
        bc.SetString(*res['IDC_CONTEXT_TOGGLEMENUBAR'])
        bc.SetString(*res['IDC_CONTEXT_CLOSEDIALOG'])

    def ContextMenuCall(self, root, ud, doc, column, command):
        if command == res.IDC_CONTEXT_CLOSE:
            c4d.CallCommand(CMD_CLOSE_DOCUMENT)
        elif command == res.IDC_CONTEXT_CLOSEALL:
            c4d.CallCommand(CMD_CLOSE_DOCUMENTS)
        elif command == res.IDC_CONTEXT_CLOSEOTHERS:
            current = c4d.documents.GetActiveDocument()
            doc = c4d.documents.GetFirstDocument()
            while doc:
                next = doc.GetNext()
                if doc != current:
                    c4d.documents.SetActiveDocument(doc)
                    c4d.CallCommand(CMD_CLOSE_DOCUMENT)
                doc = next
            c4d.documents.SetActiveDocument(current)
        elif command == res.IDC_CONTEXT_TOGGLEMENUBAR:
            c4d.SpecialEventAdd(PLMSG_QUICKDOCS_TOGGLEMENUBAR)
        elif command == res.IDC_CONTEXT_CLOSEDIALOG:
            c4d.SpecialEventAdd(PLMSG_QUICKDOCS_CLOSE)
        else:
            return False
        return True

class Dialog(c4d.gui.GeDialog):

    def __init__(self, show_menubar):
        super(Dialog, self).__init__()
        if not show_menubar:
            self.AddGadget(c4d.DIALOG_NOMENUBAR, 0)
        self.tree = None

    def CreateLayout(self):
        result = self.LoadDialogResource(res.DLG_MAIN)
        self.SetTitle(Command.PLUGIN_NAME)
        return result

    def InitValues(self):
        self.tree = self.FindCustomGui(res.ID_DOCTREE, c4d.CUSTOMGUI_TREEVIEW)
        if self.tree:
            self.tree.SetRoot(None, DocumentTreeModel(), None)
        return bool(self.tree)

    def CoreMessage(self, gid, msg):
        if gid in [c4d.BFM_CORE_UPDATECOMMANDS, c4d.EVMSG_CHANGE]:
            if self.tree:
                self.tree.Refresh()
        return True

class DialogWrapper(object):

    def __init__(self):
        super(DialogWrapper, self).__init__()
        self._dlg = None
        self._changed = False

    def get_show_menubar(self):
        bc = PluginData.get()
        return bc.GetBool(PluginData.ID_WITHMENUBAR, True)

    def set_show_menubar(self, show):
        if operator.xor(self.show_menubar, show):
            self._changed = True
            bc = c4d.BaseContainer()
            bc.SetBool(PluginData.ID_WITHMENUBAR, bool(show))
            PluginData.set(bc)

    show_menubar = property(get_show_menubar, set_show_menubar)

    def get_dlg(self):
        if not self._dlg or self._changed:
            if self._dlg and self._dlg.IsOpen():
                self._dlg.Close()
            self._dlg = Dialog(self.show_menubar)
            self._changed = False
        return self._dlg

    dlg = property(get_dlg)

    def Close(self):
        if self._dlg and self._dlg.IsOpen():
            self._dlg.Close()

    def Open(self):
        return self.dlg.Open(c4d.DLG_TYPE_ASYNC, Command.PLUGIN_ID)

    def Restore(self, secret):
        return self.dlg.Restore(Command.PLUGIN_ID, secret)

class Command(c4d.plugins.CommandData):

    PLUGIN_ID = 1030336
    PLUGIN_NAME = res('IDC_QUICKDOCS')
    PLUGIN_HELP = res('IDC_QUICKDOCS_HELP')
    PLUGIN_INFO = c4d.PLUGINFLAG_COMMAND_HOTKEY
    PLUGIN_ICON = res.file('icon.png')

    execute_called = False

    def __init__(self, dlg):
        super(Command, self).__init__()
        self.dlg = dlg

    def register(self):
        icon = c4d.bitmaps.BaseBitmap()
        icon.InitWith(self.PLUGIN_ICON)
        return c4d.plugins.RegisterCommandPlugin(
            self.PLUGIN_ID, self.PLUGIN_NAME, self.PLUGIN_INFO,
            icon, self.PLUGIN_HELP, self)

    def Execute(self, doc):
        c4d.SpecialEventAdd(PLMSG_QUICKDOCS_OPEN)
        return True

    def RestoreLayout(self, secret):
        if not self.execute_called:
            self.dlg.show_menubar = False
            self.execute_called = True
        return self.dlg.Restore(secret)

class MessageHandler(c4d.plugins.MessageData):

    PLUGIN_ID = 1033708

    def __init__(self, dlg):
        super(MessageHandler, self).__init__()
        self.dlg = dlg

    def register(self):
        return c4d.plugins.RegisterMessagePlugin(
            self.PLUGIN_ID, "QuickDocs_MessageHandler", 0, self)

    def CoreMessage(self, type, data):
        if type == PLMSG_QUICKDOCS_OPEN:
            self.dlg.Open()
        elif type == PLMSG_QUICKDOCS_CLOSE:
            self.dlg.Close()
        elif type == PLMSG_QUICKDOCS_TOGGLEMENUBAR:
            self.dlg.Close()
            self.dlg.show_menubar ^= True
            c4d.SpecialEventAdd(PLMSG_QUICKDOCS_OPEN)
        return True

if __name__ == '__main__':
    dlg = DialogWrapper()
    Command(dlg).register()
    MessageHandler(dlg).register()
