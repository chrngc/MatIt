import gi

# Ensure GTK4 is available
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

from ui.widgets import Widgets

class Demo:

    def __init__(self):
        self.app = Gtk.Application(application_id="org.example.Demo")
        self.css_paths = ['customization/ui/widgets.css']

    def on_activate(self, app):
        win = Gtk.ApplicationWindow(application=app, title="Widgets Demo")
        wf = Widgets(css_paths=self.css_paths)

        vbox = Gtk.Box.new(Gtk.Orientation.VERTICAL, 24)
        vbox.set_homogeneous(False) # Ensure the box is not homogeneous
        vbox.set_vexpand(False)   # For horizontal scale
        vbox.set_hexpand(True)
        slider = wf.make_slider(0, 100, 1, value=25)
        # Add a CSS class so the slider length can be controlled from CSS
        try:
            slider.get_style_context().add_class('wide-scale')
        except Exception:
            pass

        # We'll control exact width programmatically so it stays within min/max
        slider.set_hexpand(True)
        slider.set_halign(Gtk.Align.FILL)

        check = wf.make_checkbutton('Enable feature')
        entry = wf.make_entry('Type something')

        def on_button_clicked(button):
            try:
                print('Entry:', entry.get_text())
            except Exception:
                pass
            try:
                print('Checked:', check.get_active())
            except Exception:
                pass
            try:
                print('Slider:', slider.get_value())
            except Exception:
                pass

        btn = wf.make_button('Print values', on_button_clicked)

        vbox.append(wf.make_row('Slider:', slider))
        vbox.append(wf.make_row('Check:', check))
        vbox.append(wf.make_row('Text:', entry))
        vbox.append(btn)

        win.set_child(vbox)
        win.present()

    def run(self):
        self.app.connect('activate', self.on_activate)
        self.app.run(None)