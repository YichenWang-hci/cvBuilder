#!/usr/bin/env python3
"""Start local web UI for knowledge/ management."""

from web.app import create_app

if __name__ == "__main__":
    app = create_app()
    print("cvBuilder local UI: http://127.0.0.1:5050")
    print("Data stays in knowledge/ on this machine.")
    app.run(host="127.0.0.1", port=5050, debug=True)
