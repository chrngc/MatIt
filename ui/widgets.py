import gi
from pathlib import Path

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk


class Widgets:
    """
    Usage:
      wf = WidgetsFactory(css_paths=['customization/ui/widgets.css'])
      slider = wf.make_slider(0, 100, 1)
      check = wf.make_checkbutton('Enable')
      entry = wf.make_entry('Placeholder')
      btn = wf.make_button('Click', on_clicked)
    """

    def __init__(self, css_paths=None):
        self.css_provider = None
        if css_paths:
            self.load_css(css_paths)

    def load_css(self, css_paths):
        """Load one or more CSS files and register them for the default display."""
        if isinstance(css_paths, (str, Path)):
            css_paths = [css_paths]

        self.css_provider = Gtk.CssProvider()
        for p in css_paths:
            path = str(Path(p).expanduser())
            try:
                # Preferred: load from path
                self.css_provider.load_from_path(path)
            except Exception:
                # Fallback: try loading as raw data
                try:
                    data = Path(path).read_bytes()
                    self.css_provider.load_from_data(data)
                except Exception as e:
                    print(f"widgets.py: failed to load CSS '{path}': {e}")

        display = Gdk.Display.get_default()
        if display and self.css_provider:
            Gtk.StyleContext.add_provider_for_display(
                display, self.css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    def make_slider(self, minimum=0, maximum=100, step=1, value=None, orientation=Gtk.Orientation.HORIZONTAL):
        """Create a horizontal or vertical slider (scale)."""
        try:
            scale = Gtk.Scale.new_with_range(orientation, minimum, maximum, step)
        except AttributeError:
            # Fallback for APIs where new_with_range isn't present
            adjustment = Gtk.Adjustment.new(value or minimum, minimum, maximum, step, step * 10, 0)
            scale = Gtk.Scale.new(orientation, adjustment)

        if value is not None:
            scale.set_value(value)
        return scale

    def make_checkbutton(self, label=""):
        """Create a check button with an optional label."""
        return Gtk.CheckButton.new_with_label(label)

    def make_entry(self, placeholder_text=""):
        """Create a single-line text entry."""
        entry = Gtk.Entry()
        if placeholder_text:
            entry.set_placeholder_text(placeholder_text)
        return entry

    def make_button(self, label, on_clicked=None):
        """Create a button and optionally connect a clicked handler."""
        btn = Gtk.Button.new_with_label(label)
        if on_clicked:
            btn.connect('clicked', on_clicked)
        return btn

    def make_row(self, label_text, widget, spacing=8):
        """Create a labeled row (horizontal) containing a label and a widget."""
        box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, spacing)
        lbl = Gtk.Label.new(label_text)
        lbl.set_halign(Gtk.Align.START)
        box.append(lbl)
        box.append(widget)
        return box

    def demo_application(self, css_paths=None):
        """Return a Gtk.Application that demonstrates the widgets.

        Note: running this requires GTK4 + PyGObject to be installed in the environment.
        """
        if css_paths:
            self.load_css(css_paths)

        app = Gtk.Application()

        def on_activate(app):
            win = Gtk.ApplicationWindow(application=app, title="Widgets Demo")
            vbox = Gtk.Box.new(Gtk.Orientation.VERTICAL, 12)

            slider = self.make_slider(0, 100, 1, value=25)
            check = self.make_checkbutton('Enable feature')
            entry = self.make_entry('Type something')

            def on_button_clicked(button):
                print('Entry:', entry.get_text())
                print('Checked:', check.get_active())
                try:
                    print('Slider:', slider.get_value())
                except Exception:
                    pass

            btn = self.make_button('Print values', on_button_clicked)

            vbox.append(self.make_row('Slider:', slider))
            vbox.append(self.make_row('Check:', check))
            vbox.append(self.make_row('Text:', entry))
            vbox.append(btn)

            win.set_child(vbox)
            win.present()

        app.connect('activate', on_activate)
        return app


if __name__ == '__main__':
    wf = Widgets(css_paths=['../customization/ui/widgets.css'])
    app = wf.demo_application()
    app.run(None)
