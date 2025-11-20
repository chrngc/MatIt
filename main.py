import gi

# This line is essential for GTK 4
gi.require_version('Gtk', '4.0') 
from gi.repository import Gtk

def main():
    # Application setup
    app = Gtk.Application(application_id="org.example.Gtk4App")
    
    # Connect the activate signal to a handler function
    app.connect("activate", on_activate)
    
    # Run the application
    app.run(None)

def on_activate(app):
    # Create a new window
    window = Gtk.ApplicationWindow(application=app, title="GTK 4 Window")
    
    # Create a button
    button = Gtk.Button.new_with_label("Hello GTK 4!")
    
    # Set the button as the child of the window
    window.set_child(button)
    
    window.present()

if __name__ == "__main__":
    main()
