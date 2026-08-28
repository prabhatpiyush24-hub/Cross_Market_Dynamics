import http.server
import socketserver
import os

PORT = 3000

class ResearchServerHandler(http.server.SimpleHTTPRequestHandler):
    pass

# Set up and start the server
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("", PORT), ResearchServerHandler) as httpd:
    print(f"Python Research Server running at http://localhost:{PORT}")
    print("Serving static files and research data... Press Ctrl+C to stop.")
    httpd.serve_forever()
