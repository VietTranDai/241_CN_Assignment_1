import threading
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import bencodepy
from beautifultable import BeautifulTable
import socket


def get_tracker_host():
    """
    Get the IP address of the local machine when running the local tracker.
    """
    try:
        # Connect to an external address to determine the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Connect to Google DNS to get IP
        tracker_host = s.getsockname()[0]  # Get the local IP address
        s.close()
        return tracker_host
    except Exception as e:
        print(f"Error getting tracker host address: {e}")
        return "127.0.0.1"  # Return localhost if there's an error

'''
    tracker_state = {
        "info_hash": {
            "complete": [list of complete peers],
            "incomplete": [list of incomplete peers],
            "peers": [list of all peers]
        }
    }
'''
class Tracker:
    def __init__(self, tracker_id):
        self.tracker_id = tracker_id
        self.tracker_state = {}

    def add_peer(self, info_hash, peer_id, ip, port, event, left):
        if event == "stopped":
            # If the event is "stopped" and there is no info_hash, remove the peer by ip and port
            self.remove_peer_by_ip_port(ip, port)
            return

        if info_hash not in self.tracker_state:
            self.tracker_state[info_hash] = {
                "complete": [],
                "incomplete": [],
                "peers": []
            }

        # Direct access to tracker_state
        peers = self.tracker_state[info_hash]["peers"]

        # Find peer by ip and port
        existing_peer = next((peer for peer in peers if peer["ip"] == ip and peer["port"] == port), None)

        if event == "started":
            print("Event: started")
            if not existing_peer:
                # Add new peer
                new_peer = {"peer_id": peer_id, "ip": ip, "port": port, "left": left}
                peers.append(new_peer)
                if left == 0:
                    self.tracker_state[info_hash]["complete"].append(new_peer)
                else:
                    self.tracker_state[info_hash]["incomplete"].append(new_peer)
            else:
                # Update peer if peer_id is different
                if existing_peer["peer_id"] != peer_id:
                    existing_peer["peer_id"] = peer_id
                    print(f"Peer ID updated for {ip}:{port}")

                # Update left state
                existing_peer["left"] = left
                if left == 0:
                    if existing_peer not in self.tracker_state[info_hash]["complete"]:
                        self.tracker_state[info_hash]["complete"].append(existing_peer)
                    if existing_peer in self.tracker_state[info_hash]["incomplete"]:
                        self.tracker_state[info_hash]["incomplete"].remove(existing_peer)
                else:
                    if existing_peer not in self.tracker_state[info_hash]["incomplete"]:
                        self.tracker_state[info_hash]["incomplete"].append(existing_peer)
                    if existing_peer in self.tracker_state[info_hash]["complete"]:
                        self.tracker_state[info_hash]["complete"].remove(existing_peer)

        elif event == "completed":
            print("Event: completed")
            if existing_peer and existing_peer["left"] > 0:
                existing_peer["left"] = 0
                # Move peer from incomplete to complete
                if existing_peer in self.tracker_state[info_hash]["incomplete"]:
                    self.tracker_state[info_hash]["incomplete"].remove(existing_peer)
                if existing_peer not in self.tracker_state[info_hash]["complete"]:
                    self.tracker_state[info_hash]["complete"].append(existing_peer)

    def remove_peer_by_ip_port(self, ip, port):
        """Remove peer from all lists based on ip and port."""
        for info_hash, state in self.tracker_state.items():
            peer_to_remove = next((peer for peer in state["peers"] if peer["ip"] == ip and peer["port"] == port), None)
            if peer_to_remove:
                state["peers"].remove(peer_to_remove)
                if peer_to_remove in state["complete"]:
                    state["complete"].remove(peer_to_remove)
                if peer_to_remove in state["incomplete"]:
                    state["incomplete"].remove(peer_to_remove)
                print(f"Peer {ip}:{port} removed from info_hash {info_hash}")

    def get_peers(self, info_hash):
        if info_hash not in self.tracker_state:
            return None, "Invalid info_hash", None

        return self.tracker_state.get(info_hash), None, "Request successful"
    
    def print_tracker_state(self):
        """Print the tracker_state using BeautifulTable."""
        if not self.tracker_state:
            print("Tracker state is empty.")
            return

        # Create table to display information
        table = BeautifulTable()
        table.columns.header = ["Info Hash", "Peer ID", "IP Address", "Port", "Status"]

        for info_hash, torrent_data in self.tracker_state.items():
            for peer in torrent_data["peers"]:
                peer_id = peer["peer_id"]
                ip = peer["ip"]
                port = peer["port"]
                status = "Complete" if peer in torrent_data["complete"] else "Incomplete"
                table.rows.append([info_hash, peer_id, ip, port, status])

        print(table)

class TrackerHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if self.path == "/":
                self.handle_root()
            elif self.path.startswith("/announce"):
                self.handle_announce()
            elif self.path.startswith("/get_torrent"):
                self.handle_get_torrent()
            else:
                self.send_response(404)
                self.end_headers()
        except Exception as e:
            print(f"Exception in request handling: {e}")
            self.send_error(500, message="Internal Server Error")

    def do_POST(self):
        try:
            if self.path == "/announce":
                self.handle_announce_of_post()
            else:
                self.send_response(404)
                self.end_headers()
        except Exception as e:
            print(f"Exception in request handling: {e}")
            self.send_error(500, message="Internal Server Error")

    def handle_root(self):
        """Handle request to root '/'."""
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h1>Tracker is running</h1>")

    def handle_announce(self):
        """Handle request to '/announce'."""
        query = self.path.split('?')[-1]
        params = dict(qc.split('=') for qc in query.split('&'))

        info_hash = params.get("info_hash")
        peer_id = params.get("peer_id")
        port = params.get("port")
        event = params.get("event", "started")
        left = int(params.get("left", "0"))

        if not peer_id or not port:
            self.send_error(400, message="Missing required parameters: peer_id, or port")
            return

        try:
            if event == "stopped":
                # If event is "stopped", no need for info_hash
                self.server.tracker.add_peer(
                    info_hash=None,
                    peer_id=peer_id,
                    ip=self.client_address[0],
                    port=int(port),
                    event=event,
                    left=left
                )
            else:
                if not info_hash:
                    self.send_error(400, message="Missing required parameter: info_hash")
                    return

                self.server.tracker.add_peer(
                    info_hash=info_hash,
                    peer_id=peer_id,
                    ip=self.client_address[0],
                    port=int(port),
                    event=event,
                    left=left
                )
        except Exception as e:
            print(f"Error adding peer: {e}")
            self.send_error(500, message="Error updating tracker state")
            return

        tracker_data, failure_reason, warning_message = self.server.tracker.get_peers(info_hash)

        if failure_reason:
            response = {b"failure reason": failure_reason.encode('utf-8')}
            self.send_response(400)
            self.send_header("Content-Type", "application/octet-stream")
            self.end_headers()
            self.wfile.write(bencodepy.encode(response))
            return

        complete_peers = len(tracker_data["complete"])
        incomplete_peers = len(tracker_data["incomplete"])
        all_peers = [
            peer for peer in tracker_data["peers"]
            if peer["peer_id"] != peer_id
        ]

        response = {
            b"interval": 1800,
            b"complete": complete_peers,
            b"incomplete": incomplete_peers,
            b"peers": b''.join(
                [self.encode_peer(peer) for peer in all_peers]
            ),
            b"tracker id": self.server.tracker.tracker_id.encode('utf-8')
        }

        if warning_message:
            response[b"warning message"] = warning_message.encode('utf-8')

        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.end_headers()
        self.wfile.write(bencodepy.encode(response))

        self.server.tracker.print_tracker_state()

    def encode_peer(self, peer):
        """Encode peer information in binary format."""
        ip_bytes = b"".join([int(octet).to_bytes(1, 'big') for octet in peer["ip"].split('.')])
        port_bytes = int(peer["port"]).to_bytes(2, 'big')
        return ip_bytes + port_bytes
    
    def handle_announce_of_post(self):
        """Handle the /announce request from a peer."""
        try:
            # Read data from request headers and body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error(400, "No data received")
                return

            # Read the body to get the torrent data and parameters
            payload, files = self.parse_multipart_request()

            # Get info_hash from payload
            info_hash = payload.get("info_hash").hex()
            if not info_hash:
                self.send_error(400, "Missing info_hash")
                return

            torrent_data_folder = "torrent_data_folder"
            os.makedirs(torrent_data_folder, exist_ok=True)

            # Path to save the file
            torrent_file_path = os.path.join(torrent_data_folder, f"{info_hash}.torrent")

            # Get torrent file from files
            torrent_file = files.get('torrent_file')
            if not torrent_file:
                self.send_error(400, "Missing torrent_file")
                return

            # Save the torrent file to folder
            with open(torrent_file_path, 'wb') as f:
                f.write(torrent_file)

            # Information required for the tracker
            peer_id = payload.get("peer_id", "").decode()
            port = int(payload.get("port", 0))
            event = payload.get("event", b"started").decode()
            left = int(payload.get("left", 0))
            ip = self.client_address[0]  # Peer IP from request

            # Add peer information to tracker
            self.server.tracker.add_peer(
                info_hash=info_hash,
                peer_id=peer_id,
                ip=ip,
                port=port,
                event=event,
                left=left
            )

            # Respond with success
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Torrent file saved at {torrent_file_path}".encode('utf-8'))

            self.server.tracker.print_tracker_state()
            print(f"Received torrent file for info_hash {info_hash} and saved to {torrent_file_path}")

        except Exception as e:
            print(f"Error handling announce request: {e}")
            self.send_error(500, "Internal Server Error")

    def parse_multipart_request(self):
        """Parse multipart/form-data request to get payload and files."""
        content_type = self.headers.get('Content-Type')
        if not content_type or "multipart/form-data" not in content_type:
            raise ValueError("Invalid Content-Type for multipart request")

        boundary = content_type.split("boundary=")[-1].encode()
        content = self.rfile.read(int(self.headers['Content-Length']))

        # Split the multipart parts
        parts = content.split(b"--" + boundary)
        payload = {}
        files = {}

        for part in parts:
            if b"Content-Disposition" in part:
                headers, body = part.split(b"\r\n\r\n", 1)
                body = body.rstrip(b"\r\n--")
                headers = headers.decode()

                if 'name="' in headers:
                    name = headers.split('name="')[1].split('"')[0]
                    if "filename=" in headers:
                        # This is a file
                        files[name] = body
                    else:
                        # This is a normal payload
                        payload[name] = body

        return payload, files

    def handle_get_torrent(self):
        """Handle /get_torrent request from a peer to return the torrent file."""
        try:
            # If the request is GET with a query string
            query = self.path.split('?')[-1]
            params = dict(qc.split('=') for qc in query.split('&'))

            # Get info_hash from query string
            info_hash = params.get("info_hash")
            if not info_hash:
                self.send_error(400, "Missing required parameter: info_hash")
                return

            # Find the torrent file in the torrent_data_folder
            torrent_data_folder = "torrent_data_folder"
            torrent_file_path = os.path.join(torrent_data_folder, f"{info_hash}.torrent")

            if not os.path.exists(torrent_file_path):
                self.send_error(404, f"Torrent file for info_hash {info_hash} not found.")
                return

            # Read the torrent file content
            with open(torrent_file_path, 'rb') as f:
                torrent_bytes = f.read()

            # Send the response with the torrent file content
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.end_headers()
            self.wfile.write(torrent_bytes)

            print(f"Sent torrent file for info_hash {info_hash} to peer.")

        except Exception as e:
            print(f"Error while handling /get_torrent request: {e}")
            self.send_error(500, "Error processing the request")

class TrackerHTTPServer:
    def __init__(self, tracker_id, tracker_ip, tracker_port):
        self.tracker_id = tracker_id
        self.tracker_ip = tracker_ip
        self.tracker_port = tracker_port

        # Initialize Tracker object to store important information
        self.tracker = Tracker(tracker_id)
        
        # Create HTTP server with handler and assign tracker to server
        self.server = HTTPServer((tracker_ip, tracker_port), TrackerHTTPRequestHandler)
        self.server.tracker = self.tracker  # Assign tracker to server for handler access

    def start(self):
        print(f"Tracker HTTP Server started at http://{self.tracker_ip}:{self.tracker_port}")
        server_thread = threading.Thread(target=self.server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        print("Tracker HTTP Server stopped")


if __name__ == "__main__":
    try:
        tracker_id = "-TK0001-0001"
        tracker_host = get_tracker_host()
        tracker_port = int(input("Enter the tracker port (e.g. 22236): "))

        tracker_server = TrackerHTTPServer(tracker_id, tracker_host, tracker_port)
        tracker_server.start()

        # Keep the server running until the 'stop' command is received
        while True:
            command = input("Type 'stop' to stop the tracker: ")
            if command == "stop":
                tracker_server.stop()
                break
            else:
                continue

    except Exception as e:
        print(f"Exception: {e}")
    except KeyboardInterrupt:
        os._exit(0)