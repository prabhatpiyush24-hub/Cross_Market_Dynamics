import http.server
import socketserver
import os
import urllib.parse

PORT = 3000

class ResearchServerHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        parsed_path = urllib.parse.urlparse(path).path
        
        # Route API calls to the pre-calculated JSON files
        if parsed_path.startswith('/api/stats/'):
            filename = parsed_path.split('/')[-1] + '.json'
            return os.path.join(os.getcwd(), 'data', 'stats', filename)
            
        # Route /data requests directly to the data folder
        elif parsed_path.startswith('/data/'):
            # Remove leading slash so os.path.join works correctly
            return os.path.join(os.getcwd(), parsed_path.lstrip('/'))
            
        # Route the root to index.html in the public folder
        elif parsed_path == '/':
            return os.path.join(os.getcwd(), 'public', 'index.html')
            
        # Route everything else to the public folder (CSS, JS, etc.)
        else:
            return os.path.join(os.getcwd(), 'public', parsed_path.lstrip('/'))

# Set up and start the server
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("", PORT), ResearchServerHandler) as httpd:
    print(f"Python Research Server running at http://localhost:{PORT}")
    print("Serving static files and research data... Press Ctrl+C to stop.")
    httpd.serve_forever()
