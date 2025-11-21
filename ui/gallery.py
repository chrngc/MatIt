import gi
import glob
import sys
from pathlib import Path

gi.require_version('Gtk', '4.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Gdk, GdkPixbuf
from gi.repository import GLib

from ui.widgets import Widgets


class Gallery:
    def __init__(self):
        self.app = Gtk.Application(application_id="com.matit.Gallery")
        self.css_paths = ['customization/ui/gallery.css']
        self.image_dir = Path("/home/chrngc-fedora/Pictures")
        # Default thumbnail size in pixels (square)
        self.thumbnail_size = 150

    def on_activate(self, app):
        # Create main window
        self.win = Gtk.ApplicationWindow(application=app)
        self.win.set_title("Photo Gallery")
        self.win.set_default_size(1200, 800)
        
        # Load CSS
        wf = Widgets(css_paths=self.css_paths)

        # Create header bar
        header = Gtk.HeaderBar()
        # keep reference so we can restore it later
        self._main_titlebar = header
        # Add zoom controls to header
        zoom_out = Gtk.Button(label='−')
        zoom_in = Gtk.Button(label='+')
        zoom_out.add_css_class('flat')
        zoom_in.add_css_class('flat')
        zoom_out.connect('clicked', lambda w: self.change_thumbnail_size(-20))
        zoom_in.connect('clicked', lambda w: self.change_thumbnail_size(20))
        header.pack_end(zoom_in)
        header.pack_end(zoom_out)
        self.win.set_titlebar(header)
        
        # Create scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        
        # Create flowbox for images
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(30)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flowbox.set_margin_start(10)
        self.flowbox.set_margin_end(10)
        self.flowbox.set_margin_top(10)
        self.flowbox.set_margin_bottom(10)
        self.flowbox.set_row_spacing(8)
        self.flowbox.set_column_spacing(8)
        # Reduce spacing to bring frames closer together (iOS-like)
        self.flowbox.set_margin_start(6)
        self.flowbox.set_margin_end(6)
        self.flowbox.set_margin_top(6)
        self.flowbox.set_margin_bottom(6)
        self.flowbox.set_row_spacing(4)
        self.flowbox.set_column_spacing(4)
        
        scrolled.set_child(self.flowbox)
        self.win.set_child(scrolled)

        # Allow Ctrl+scroll to change thumbnail size
        try:
            self.win.connect('scroll-event', self.on_scroll)
            scrolled.connect('scroll-event', self.on_scroll)
        except Exception:
            # Fallback: add EventControllerScroll to window if direct signal not available
            try:
                esc = Gtk.EventControllerScroll.new(self.win)
                esc.connect('scroll', lambda c, dx, dy: None)
            except Exception:
                pass
        
        # Show window first so UI appears immediately
        self.win.present()

        # Load images incrementally after launch to keep UI responsive
        self.load_images()

    def load_images(self):
        """Load images from directory into the gallery"""
        if not self.image_dir.exists():
            print(f"Directory {self.image_dir} does not exist")
            return
            
        # Find image files
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp', '*.JPG', '*.JPEG', '*.PNG']:
            image_files.extend(glob.glob(str(self.image_dir / ext)))
        
        if not image_files:
            print("No images found")
            return
        
        print(f"Preparing to load {len(image_files)} images...")

        # Use an idle callback to load images one-by-one so the window
        # appears immediately and the UI stays responsive while thumbnails
        # are rendered incrementally.
        files = sorted(image_files)
        self._image_iter = iter(files)
        GLib.idle_add(self._load_images_idle)

    def _load_images_idle(self):
        """Idle callback: load a single image and schedule next."""
        try:
            img_path = next(self._image_iter)
        except StopIteration:
            return False

        try:
            # Fast path: load a low-quality downscaled image first to speed up
            # thumbnail generation. We load at 2x the desired thumbnail size
            # (or fallback to full load) and crop from that smaller buffer.
            try:
                fast = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    img_path, self.thumbnail_size * 2, self.thumbnail_size * 2, True
                )
            except Exception:
                # If scaling on load isn't supported for this file, fall back
                fast = GdkPixbuf.Pixbuf.new_from_file(img_path)

            # Crop center square from the (already downscaled) pixbuf
            w = fast.get_width()
            h = fast.get_height()
            s = min(w, h)
            x = (w - s) // 2
            y = (h - s) // 2
            try:
                sub = fast.new_subpixbuf(x, y, s, s)
            except AttributeError:
                sub = GdkPixbuf.Pixbuf.new_subpixbuf(fast, x, y, s, s)

            # Use a low-quality (fast) interpolation for initial thumbnail
            src = sub
            pixbuf = src.scale_simple(self.thumbnail_size, self.thumbnail_size, GdkPixbuf.InterpType.NEAREST)
            texture = Gdk.Texture.new_for_pixbuf(pixbuf)

            # Create picture widget
            picture = Gtk.Picture.new_for_paintable(texture)
            picture.set_can_shrink(True)
            picture.set_content_fit(Gtk.ContentFit.COVER)
            # Center the picture inside its container
            picture.set_halign(Gtk.Align.CENTER)
            picture.set_valign(Gtk.Align.CENTER)

            # Create container
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            # Make frames square; size depends on current thumbnail_size
            box.set_size_request(self.thumbnail_size + 10, self.thumbnail_size + 10)
            # store the source square pixbuf to allow quick rescaling
            box._src_pixbuf = src
            # store original image path so we can rescale later reliably
            box._img_path = img_path
            box.append(picture)
            box.add_css_class('thumbnail-frame')
            # Center any children inside the box
            box.set_halign(Gtk.Align.CENTER)
            box.set_valign(Gtk.Align.CENTER)

            # Add to flowbox
            self.flowbox.append(box)
            # attach click handler to open fullscreen
            try:
                self._attach_click(box)
            except Exception:
                pass

        except Exception as e:
            print(f"Failed to load {img_path}: {e}")

        # Return True to keep the idle callback active until all images processed
        return True

    def change_thumbnail_size(self, delta):
        """Increase or decrease thumbnail size by `delta` pixels and rescale all thumbnails."""
        new_size = max(60, min(400, self.thumbnail_size + delta))
        if new_size == self.thumbnail_size:
            return
        self.thumbnail_size = new_size
        self.rescale_thumbnails()

    def on_scroll(self, widget, event):
        """Handle scroll events: Ctrl + wheel to zoom thumbnails."""
        try:
            state = getattr(event, 'state', None)
            if state is None:
                try:
                    state = event.get_state()
                except Exception:
                    state = 0

            if state & Gdk.ModifierType.CONTROL_MASK:
                # Determine direction
                dir = getattr(event, 'direction', None)
                if dir == Gdk.ScrollDirection.UP:
                    self.change_thumbnail_size(10)
                elif dir == Gdk.ScrollDirection.DOWN:
                    self.change_thumbnail_size(-10)
                else:
                    # Try delta-based
                    try:
                        dx, dy = event.get_scroll_deltas()
                        if dy < 0:
                            self.change_thumbnail_size(10)
                        elif dy > 0:
                            self.change_thumbnail_size(-10)
                    except Exception:
                        pass
                return True
        except Exception:
            pass
        return False

    def rescale_thumbnails(self):
        """Rescale thumbnails asynchronously so UI stays responsive.

        This schedules an idle callback that rescales one thumbnail per idle
        iteration by loading a size-appropriate pixbuf via
        `GdkPixbuf.Pixbuf.new_from_file_at_scale(img_path, size, size, True)`.
        """
        files = []
        for child in self.flowbox.get_children():
            try:
                target_box = child.get_child() if hasattr(child, 'get_child') else child
            except Exception:
                target_box = child

            img_path = getattr(target_box, '_img_path', None)
            if img_path:
                files.append((target_box, img_path))

        # create an iterator and schedule idle worker
        self._rescale_iter = iter(files)
        GLib.idle_add(self._rescale_images_idle)

    def _rescale_images_idle(self):
        """Idle worker: rescale one thumbnail per call."""
        try:
            target_box, img_path = next(self._rescale_iter)
        except StopIteration:
            return False

        try:
            # Load a fresh thumbnail at the target size (fast path)
            try:
                scaled_pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    img_path, self.thumbnail_size, self.thumbnail_size, True
                )
            except Exception:
                # fallback to loading full then scaling
                full = GdkPixbuf.Pixbuf.new_from_file(img_path)
                scaled_pb = full.scale_simple(self.thumbnail_size, self.thumbnail_size, GdkPixbuf.InterpType.BILINEAR)

            texture = Gdk.Texture.new_for_pixbuf(scaled_pb)

            # Replace children with the new picture
            try:
                existing = target_box.get_children()
            except Exception:
                existing = []

            for w in existing:
                try:
                    target_box.remove(w)
                except Exception:
                    pass

            newpic = Gtk.Picture.new_for_paintable(texture)
            newpic.set_can_shrink(True)
            newpic.set_content_fit(Gtk.ContentFit.COVER)
            newpic.set_halign(Gtk.Align.CENTER)
            newpic.set_valign(Gtk.Align.CENTER)
            target_box.append(newpic)

            # ensure thumbnail is clickable to open fullscreen
            try:
                self._attach_click(target_box)
            except Exception:
                pass

            # update stored small source so future fast resizes can use it
            try:
                target_box._src_pixbuf = scaled_pb
            except Exception:
                pass

            target_box.set_size_request(self.thumbnail_size + 10, self.thumbnail_size + 10)

        except Exception as e:
            print(f"Failed to rescale thumbnail {img_path}: {e}")

        return True

    def close_fullscreen(self):
        """Restore the gallery view after fullscreen and remove handlers."""
        try:
            # Do not change the window size when closing fullscreen — we
            # previously avoided resizing when opening, so nothing to undo here.

            # Restore previous child
            if getattr(self, '_gallery_child', None) is not None:
                try:
                    self.win.set_child(self._gallery_child)
                except Exception:
                    try:
                        # if set_child isn't available use present
                        self.win.set_child(self._gallery_child)
                    except Exception:
                        pass

            # Restore previous titlebar (if we replaced it)
            try:
                if getattr(self, '_prev_titlebar', None) is not None:
                    self.win.set_titlebar(self._prev_titlebar)
                elif getattr(self, '_main_titlebar', None) is not None:
                    self.win.set_titlebar(self._main_titlebar)
            except Exception:
                pass

            # Remove key controller if present
            if getattr(self, '_fs_key_controller', None) is not None:
                try:
                    self.win.remove_controller(self._fs_key_controller)
                except Exception:
                    pass
                self._fs_key_controller = None

            # Remove fallback signal if present
            if getattr(self, '_fs_key_sig', None) is not None:
                try:
                    self.win.disconnect(self._fs_key_sig)
                except Exception:
                    pass
                self._fs_key_sig = None

            # Restore window title
            try:
                self.win.set_title("Photo Gallery")
            except Exception:
                pass

        except Exception as e:
            print(f"Error closing fullscreen: {e}")

    def _attach_click(self, box):
        """Attach a click gesture to `box` to open the image fullscreen."""
        try:
            gesture = Gtk.GestureClick.new()
            gesture.connect('pressed', self.on_thumbnail_pressed, box)
            # Attach controller if available, otherwise try connect
            try:
                box.add_controller(gesture)
            except Exception:
                # fallback for older PyGObject: gestures may be connectable
                pass
        except Exception:
            # last-resort: connect button-press-event if still possible
            try:
                box.connect('button-press-event', lambda w, e: self.on_thumbnail_pressed(None, 0, 0, 0, box))
            except Exception:
                pass

    def on_thumbnail_pressed(self, gesture, n_press, x, y, box):
        """Open the clicked thumbnail in fullscreen."""
        img_path = getattr(box, '_img_path', None)
        if not img_path:
            return
        self.open_fullscreen_image(img_path)

    def open_fullscreen_image(self, img_path):
        """Show the image in the existing main window (replace gallery view).

        The original gallery child is saved and restored when the user clicks
        Back or presses Escape.
        """
        try:
            # Save current gallery child so we can restore it later
            try:
                self._gallery_child = self.win.get_child()
            except Exception:
                self._gallery_child = None

            # Create a header/back button for the image view and set it
            # as the window's titlebar (do NOT place it inside the content).
            header = Gtk.HeaderBar()
            back = Gtk.Button(label='Back')
            back.add_css_class('flat')
            back.connect('clicked', lambda w: self.close_fullscreen())
            header.pack_start(back)
            # save previous titlebar to restore later
            try:
                self._prev_titlebar = getattr(self, '_main_titlebar', None)
            except Exception:
                self._prev_titlebar = None
            try:
                self.win.set_titlebar(header)
            except Exception:
                pass

            # Determine screen size for scaling
            sw = 1600
            sh = 900
            try:
                disp = Gdk.Display.get_default()
                mon = disp.get_primary_monitor()
                geo = mon.get_geometry()
                scale = mon.get_scale_factor()
                sw = geo.width * scale
                sh = geo.height * scale
            except Exception:
                pass

            try:
                pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(img_path, sw, sh, True)
            except Exception:
                pb = GdkPixbuf.Pixbuf.new_from_file(img_path)

            texture = Gdk.Texture.new_for_pixbuf(pb)
            picture = Gtk.Picture.new_for_paintable(texture)
            picture.set_can_shrink(True)
            picture.set_content_fit(Gtk.ContentFit.SCALE_DOWN)

            container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            container.append(picture)

            # Create an outer box that holds the image content (header is the window titlebar)
            outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            outer.append(container)

            # Replace the window child with the fullscreen view
            try:
                self.win.set_title("Image")
            except Exception:
                pass
            try:
                self.win.set_child(outer)
            except Exception:
                # fallback to set_child on top-level if API differs
                self.win.set_child(container)

            # Keep the current window size — do NOT fullscreen or maximize.
            # We only replace the window's child with the image view so the
            # window geometry remains unchanged.

            # Add Escape key handler to close fullscreen
            try:
                keyc = Gtk.EventControllerKey.new(self.win)
                def on_key(controller, keyval, keycode, state):
                    try:
                        name = Gdk.keyval_name(keyval)
                        if name == 'Escape':
                            self.close_fullscreen()
                            return True
                    except Exception:
                        pass
                    return False
                keyc.connect('key-pressed', on_key)
                # store to remove later if needed
                self._fs_key_controller = keyc
            except Exception:
                try:
                    # fallback: connect key-press-event
                    self._fs_key_sig = self.win.connect('key-press-event', lambda w, e: self.close_fullscreen() if Gdk.keyval_name(e.keyval) == 'Escape' else False)
                except Exception:
                    pass

        except Exception as e:
            print(f"Failed to open fullscreen image in current window: {e}")

    def run(self):
        self.app.connect('activate', self.on_activate)
        return self.app.run(sys.argv)