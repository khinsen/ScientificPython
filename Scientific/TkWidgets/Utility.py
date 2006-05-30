# Various useful small widgets
#
# Written by Konrad Hinsen <khinsen@cea.fr>
# Last revision: 2005-3-11
#

import Tkinter, Dialog, FileDialog
import copy, os, string


class FilenameEntry(Tkinter.Frame):

    """Filename entry widget

    Constructor: FilenameEntry(|master|, |text|, |pattern|,
                               |must_exist_flag|=1)

    Arguments:

    |master| -- the master widget

    |text| -- the label in front of the filename box

    |pattern| -- the filename matching pattern that determines the
                 file list in the file selection dialog

    |must_exists_flag| -- allow only names of existing files

    A FilenameEntry widget consists of three parts: an identifying
    label, a text entry field for the filename, and a button labelled
    'browse' which call a file selection dialog box for picking a file
    name.
    """

    def __init__(self, master, text, browse_pattern = '*', must_exist = 1,
                 **attr):
        self.pattern = browse_pattern
        self.must_exist = must_exist
        newattr = copy.copy(attr)
        newattr['text'] = text
        Tkinter.Frame.__init__(self, master)
        apply(Tkinter.Label, (self,), newattr).pack(side=Tkinter.LEFT)
        self.filename = Tkinter.StringVar()
        Tkinter.Button(self, text="Browse...",
                       command=self.browse).pack(side=Tkinter.RIGHT)
        newattr = copy.copy(attr)
        newattr['textvariable'] = self.filename
        entry = apply(Tkinter.Entry, (self,), newattr)
        entry.pack(side=Tkinter.RIGHT, expand=1, fill=Tkinter.X)
        entry.icursor("end")

    def browse(self):
        if self.must_exist:
            file = FileDialog.LoadFileDialog(self).go(pattern=self.pattern)
        else:
            file = FileDialog.SaveFileDialog(self).go(pattern=self.pattern)
        if file:
            self.filename.set(file)

    def get(self):
        """Return the current filename. If |must_exist_flag| is true,
        verify that the name refers to an existing file.
        Otherwise an error message is displayed and a ValueError is raised.
        """
        filename =  self.filename.get()
        if self.must_exist and not os.path.exists(filename):
            Dialog.Dialog(self, title='File not found',
                          text='The file "' + filename + '" does not exist.',
                          bitmap='warning', default=0,
                          strings = ('Cancel',))
            raise ValueError
        return filename


class FloatEntry(Tkinter.Frame):

    """An entry field for float numbers

    Constructor: FloatEntry(|master|, |text|, |initial|=None,
                            |lower|=None, |upper|=None)

    Arguments:

    |master| -- the master widget

    |text| -- the label in front of the entry field

    |initial| -- an optional initial value (default: blank field)

    |upper| -- an optional upper limit for the value

    |lower| -- an optional lower limit for the value

    A FloatEntry widget consists of a label followed by a text entry
    field. 
    """
    
    def __init__(self, master, text, init = None, lower=None, upper=None,
                 name = None, **attr):
        self.text = text
        self.lower = lower
        self.upper = upper
        if name is None:
            name = text
        self.name = name
        newattr = copy.copy(attr)
        newattr['text'] = text
        Tkinter.Frame.__init__(self, master)
        apply(Tkinter.Label, (self,), newattr).pack(side=Tkinter.LEFT)
        self.value = Tkinter.DoubleVar()
        if init is not None:
            self.value.set(init)
        newattr = copy.copy(attr)
        newattr['textvariable'] = self.value
        self.entry = apply(Tkinter.Entry, (self,), newattr)
        self.entry.pack(side=Tkinter.RIGHT, anchor=Tkinter.E,
                        expand=1, fill=Tkinter.X)
        self.entry.icursor("end")

    def bind(self, sequence=None, func=None, add=None):
        self.entry.bind(sequence, func, add)

    def set(self, value):
        "Set the value to |value|."
        return self.value.set(value)

    def get(self):
        """Return the current value, verifying that it is a number
        and between the specified limits. Otherwise an error message
        is displayed and a ValueError is raised."""
        try:
            value = self.value.get()
        except (Tkinter.TclError, ValueError):
            Dialog.Dialog(self, title='Illegal value',
                          text='The value of "' + self.name +
                               '" must be a number.',
                          bitmap='warning', default=0,
                          strings = ('Cancel',))
            raise ValueError
        range_check = 0
        if self.lower is not None and value < self.lower:
            range_check = -1
        if self.upper is not None and value > self.upper:
            range_check = 1
        if range_check != 0:
            text = 'The value of "' + self.name + '" must not be '
            if range_check < 0:
                text = text + 'smaller than ' + `self.lower` + '.'
            else:
                text = text + 'larger than ' + `self.upper` + '.'
            Dialog.Dialog(self, title='Value out of range', text=text,
                          bitmap='warning', default=0,
                          strings = ('Cancel',))
            raise ValueError
        return value


class IntEntry(FloatEntry):

    """An entry field for integer numbers

    Constructor: IntEntry(|master|, |text|, |initial|=None,
                          |lower|=None, |upper|=None)

    Arguments:

    |master| -- the master widget

    |text| -- the label in front of the entry field

    |initial| -- an optional initial value (default: blank field)

    |upper| -- an optional upper limit for the value

    |lower| -- an optional lower limit for the value

    A IntEntry widget consists of a label followed by a text entry
    field. 
    """
    
    def get(self):
        """Return the current value, verifying that it is an integer
        and between the specified limits. Otherwise an error message
        is displayed and a ValueError is raised."""
        value = FloatEntry.get(self)
        ivalue = int(value)
        if ivalue != value:
            Dialog.Dialog(self, title='Illegal value',
                          text='The value of "' + self.name +
                               '" must be an integer.',
                          bitmap='warning', default=0,
                          strings = ('Cancel',))
            raise ValueError
        return ivalue

class ButtonBar(Tkinter.Frame):

    """A horizontal array of buttons

    Constructor: ButtonBar(|master|, |left_button_list|, |right_button_list|)

    Arguments:

    |master| -- the master widget

    |left_button_list| -- a list of (text, action) tuples specifying the
                          buttons on the left-hand side of the button bar

    |right_button_list| -- a list of (text, action) tuples specifying the
                           buttons on the right-hand side of the button bar
    """

    def __init__(self, master, left_button_list, right_button_list):
        Tkinter.Frame.__init__(self, master, bd=2, relief=Tkinter.SUNKEN)
        for button, action in left_button_list:
            Tkinter.Button(self, text=button,
                           command=action).pack(side=Tkinter.LEFT)
        for button, action in right_button_list:
            Tkinter.Button(self, text=button,
                           command=action).pack(side=Tkinter.RIGHT)


class StatusBar(Tkinter.Frame):

    """A status bar

    Constructor: StatusBar(|master|)

    Arguments:

    |master| -- the master widget

    A status bar can be used to inform the user about the status of an
    ongoing calculation. A message can be displayed with set() and
    removed with clear(). In both cases, the StatusBar object makes
    sure that the change takes place immediately. While a message
    is being displayed, the cursor form is changed to a watch.
    """

    def __init__(self, master):
        Tkinter.Frame.__init__(self, master, bd=2, relief=Tkinter.RAISED)
        self.text = Tkinter.Label(self, text='')
        self.text.pack(side=Tkinter.LEFT, expand=Tkinter.YES)

    def set(self, text):
        self.text.configure(text = text)
        self.text.update_idletasks()
        self.master.configure(cursor='watch')
        self.update()
        self.update_idletasks()

    def clear(self):
        self.text.configure(text = '')
        self.text.update_idletasks()
        self.master.configure(cursor='top_left_arrow')
        self.update_idletasks()


#
# The following class was taken from the Pythonware Tkinter introduction
#
class ModalDialog(Tkinter.Toplevel):

    def __init__(self, parent, title = None):

        Tkinter.Toplevel.__init__(self, parent)
        self.transient(parent)
        
        if title:
            self.title(title)

        self.parent = parent

        self.result = None

        body = Tkinter.Frame(self)
        self.initial_focus = self.body(body)
        body.pack(padx=5, pady=5)

        self.buttonbox()

        self.grab_set()

        if not self.initial_focus:
            self.initial_focus = self

        self.protocol("WM_DELETE_WINDOW", self.cancel)

        self.geometry("+%d+%d" % (parent.winfo_rootx()+50,
                                  parent.winfo_rooty()+50))

        self.initial_focus.focus_set()

        self.wait_window(self)

    #
    # construction hooks

    def body(self, master):
        # create dialog body.  return widget that should have
        # initial focus.  this method should be overridden

        pass

    def buttonbox(self):
        # add standard button box. override if you don't want the
        # standard buttons

        box = Tkinter.Frame(self)

        w = Tkinter.Button(box, text="OK", width=10,
                           command=self.ok, default=Tkinter.ACTIVE)
        w.pack(side=Tkinter.LEFT, padx=5, pady=5)
        w = Tkinter.Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=Tkinter.LEFT, padx=5, pady=5)

        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

        box.pack()

    #
    # standard button semantics

    def ok(self, event=None):

        if not self.validate():
            self.initial_focus.focus_set() # put focus back
            return

        self.withdraw()
        self.update_idletasks()

        self.apply()

        self.cancel()

    def cancel(self, event=None):

        # put focus back to the parent window
        self.parent.focus_set()
        self.destroy()

    #
    # command hooks

    def validate(self):

        return 1 # override

    def apply(self):

        pass # override


if __name__ == '__main__':
    
    class MyDialog(ModalDialog):

        def body(self, master):

            Tkinter.Label(master, text="First:").grid(row=0)
            Tkinter.Label(master, text="Second:").grid(row=1)

            self.e1 = IntEntry(master, '', 0, 0, 10, fg='red')
            self.e2 = Tkinter.Entry(master)

            self.e1.grid(row=0, column=1)
            self.e2.grid(row=1, column=1)
            return self.e1 # initial focus

        def apply(self):
            first = string.atoi(self.e1.get())
            second = string.atoi(self.e2.get())
            self.result = first, second

    root = Tkinter.Tk()
    Tkinter.Button(root, text="Hello!").pack()
    root.update()
    d = MyDialog(root)
    print d.result
