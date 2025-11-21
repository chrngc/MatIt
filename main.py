import gi

# Ensure GTK4 is available
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

from ui.gallery import Gallery


def main():
    app = Gallery()
    app.run()


if __name__ == '__main__':
    main()
