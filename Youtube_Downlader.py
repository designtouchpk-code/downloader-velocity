# Bootstrapper launcher wrapper to preserve desktop shortcut compatibility.
# Directs stream calls to the partitioned Velocity.py interface.

from Velocity import Velocity

if __name__ == "__main__":
    app = Velocity()
    app.mainloop()
