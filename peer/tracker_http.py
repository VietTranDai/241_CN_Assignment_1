from enum import Enum
import requests
import bencodepy
from beautifultable import BeautifulTable

from torrent_helper import process_torrent_bytes_to_folder

class Event(Enum):
    STARTED = "started"  # Event when Peer starts downloading/uploading
    STOPPED = "stopped"  # Event when Peer stops activity
    COMPLETED = "completed"  # Event when Peer finishes downloading

class Tracker_http():
    def __init__(self, torrent_log, peer_id, peer_ip ,peer_port, info_hash, tracker_url, torrent_folder_path):
        if not info_hash:
            raise ValueError("info_hash not found in request.")

        self.tracker_url = tracker_url

        # Get torrent information from torrent_log
        self.torrent_log = torrent_log
        self.info_hash = info_hash
        self.torrent_info = self.torrent_log.torrent_data.get(self.info_hash)

        self.torrent_folder_path = torrent_folder_path

        # Set up request information
        self.compact = 1
        self.peer_id = peer_id
        self.port = peer_port
        self.uploaded = 0
        
        self.downloaded = 0
        if self.torrent_info:
            self.downloaded = sum(self.torrent_info["bitfield"])
        
        self.left = 10
        if self.torrent_info:
            self.left = self.torrent_info["piece_count"] - self.downloaded
            
        self.peer_ip = peer_ip
        self.event = None

        # Request parameters for the tracker
        self.request_parameters = {
            'info_hash': self.info_hash,
            'peer_id': self.peer_id,
            'ip': self.peer_ip,
            'port': self.port,
            'uploaded': self.uploaded,
            'downloaded': self.downloaded,
            'left': self.left,
            'compact': self.compact,
            'event': self.event,
            'tracker_id': "-TK0001-0001"
        }

        self.request_parameters_for_handle_torrent_file = {
            'info_hash': bytes.fromhex(self.info_hash),
            'peer_id': self.peer_id,
            'ip': self.peer_ip,
            'port': self.port,
            'uploaded': self.uploaded,
            'downloaded': self.downloaded,
            'left': self.left,
            'compact': self.compact,
            'event': self.event,
            'tracker_id': "-TK0001-0001"
        }

        # Response data from tracker
        self.interval = None
        self.complete = None
        self.incomplete = None
        self.peers_list = []
        self.tracker_id = None
        self.failure_reason = None
        self.warning_message = None

    def update_event(self, current_event):
        """Update event for the request."""
        if current_event not in [e.value for e in Event]:
            raise ValueError(f"Invalid event: {current_event}")
        self.event = current_event
        self.request_parameters['event'] = self.event
        print(f"Updated event to: {self.event}")

    def announce_started(self):
        """Send a request to notify the tracker that the Peer has started downloading."""
        self.update_event(Event.STARTED.value)
        return self.request_announce()

    def announce_completed(self):
        """Send a request to notify the tracker that the Peer has completed downloading (left = 0)."""
        self.left = 0
        self.request_parameters['left'] = self.left
        self.update_event(Event.COMPLETED.value)
        return self.request_announce()
    
    def announce_started_but_already_completed(self):
        """
        Send a request to notify the tracker that the Peer has completed downloading (left = 0)
        and attach the torrent file data (torrent bytes) to the tracker.
        """
        # Peer has finished downloading, no more data to download
        self.left = 0
        self.request_parameters['left'] = self.left
        self.update_event(Event.STARTED.value)

        # Get torrent bytes from info_hash
        torrent_bytes = self.torrent_log.get_bytes_of_torrent_file(self.info_hash)
        if not torrent_bytes:
            print(f"Torrent bytes for info_hash {self.info_hash} do not exist or are empty. Cannot send to tracker.")
            return False

        print(f"Announcing to tracker: {self.tracker_url} with event: {self.event}")

        try:
            # Regular payload for the tracker
            payload = self.request_parameters_for_handle_torrent_file

            # Attach torrent file bytes in the files section
            files = {'torrent_file': ('torrent.torrent', torrent_bytes, 'application/octet-stream')}

            # Send POST request to the tracker
            response = requests.post(f"{self.tracker_url}/announce", data=payload, files=files, timeout=5)

            # Handle tracker response
            if response.status_code == 200:
                tracker_response = response.content.decode('utf-8')
                print(f"Tracker response: {tracker_response}")

                # Check if the file was saved successfully
                if "Torrent file saved at" in tracker_response:
                    print("Announce started (but already completed) request was successful.")
                    return True
                else:
                    print(f"Unexpected tracker response: {tracker_response}")
                    return False
            else:
                print(f"Tracker responded with error status code {response.status_code}: {response.content.decode('utf-8')}")
                return False

        except requests.exceptions.RequestException as req_error:
            print(f"Request error: {req_error}")
            return False
        except Exception as error_msg:
            print(f"Unexpected error: {error_msg}")
            return False
        
    def request_torrent_file(self):
        """
        Send a request to the tracker to fetch the torrent file based on info_hash and save it in the specified folder.
        """
        print(f"Requesting torrent file from tracker: {self.tracker_url}")

        try:
            # Regular payload to request the torrent file
            payload = {
                'info_hash': self.info_hash,
            }

            # Send HTTP request to the tracker
            response = requests.get(f"{self.tracker_url}/get_torrent", params=payload, timeout=5)

            # Check response status
            if response.status_code == 200:
                try:
                    process_torrent_bytes_to_folder(response.content, self.torrent_folder_path)
                    self.torrent_log.scan_torrent_files()

                    print("Torrent file has been saved.")
                    return True
                except Exception as error_msg:
                    print(f"Error while processing torrent file: {error_msg}")
                    return False

            elif response.status_code == 404:
                print(f"Torrent file does not exist at the tracker for info_hash: {self.info_hash}")
            else:
                print(f"Tracker returned HTTP error: {response.status_code}, Content: {response.text}")
            return None

        except requests.exceptions.RequestException as error_msg:
            print(f"Error while requesting torrent file: {error_msg}")
            return None

    def request_announce(self):
        """Send an HTTP request to the tracker and process the response."""
        if not self.event:
            raise ValueError("Event must be set before announcing to tracker.")
        print(f"Announcing to tracker: {self.tracker_url} with event: {self.event}")
        try:
            tracker_url = self.tracker_url
            response = requests.get(tracker_url + "/announce", params=self.request_parameters, timeout=5)
            raw_response_dict = bencodepy.decode(response.content)
            self.parse_http_tracker_response(raw_response_dict)
            return True
        except Exception as error_msg:
            print(f"Error while announcing to tracker: {error_msg}")
            return False

    def parse_http_tracker_response(self, raw_response_dict):
        """Parse the response from the HTTP tracker."""
        if b'interval' in raw_response_dict:
            self.interval = raw_response_dict[b'interval']

        if b'peers' in raw_response_dict:
            self.peers_list = []
            raw_peers_data = raw_response_dict[b'peers']
            raw_peers_list = [raw_peers_data[i:6 + i] for i in range(0, len(raw_peers_data), 6)]
            for raw_peer_data in raw_peers_list:
                ip = ".".join(str(int(a)) for a in raw_peer_data[0:4])
                port = raw_peer_data[4] * 256 + raw_peer_data[5]
                self.peers_list.append((ip, port))

            # Update peer list in torrent_log
            self.torrent_log.update_peers_list(self.info_hash, self.peers_list)

        if b'complete' in raw_response_dict:
            self.complete = raw_response_dict[b'complete']

        if b'incomplete' in raw_response_dict:
            self.incomplete = raw_response_dict[b'incomplete']

        if b'tracker id' in raw_response_dict:
            self.tracker_id = raw_response_dict[b'tracker id']

        if b'failure reason' in raw_response_dict:
            self.failure_reason = raw_response_dict[b'failure reason']

        if b'warning message' in raw_response_dict:
            self.warning_message = raw_response_dict[b'warning message']

    def get_peers_data(self):
        """Get peer information from the HTTP tracker response."""
        return {
            'interval': self.interval,
            'peers': self.peers_list,
            'leechers': self.incomplete,
            'seeders': self.complete
        }

    def __str__(self):
        tracker_table = BeautifulTable()
        tracker_table.columns.header = ["HTTP TRACKER RESPONSE DATA", "DATA VALUE"]

        tracker_table.rows.append(['HTTP Tracker URL', self.tracker_url])
        tracker_table.rows.append(['Interval', str(self.interval)])
        tracker_table.rows.append(['Peer List', str(self.peers_list)])
        tracker_table.rows.append(['Number of Leechers', str(self.incomplete)])
        tracker_table.rows.append(['Number of Seeders', str(self.complete)])

        if self.peers_list:
            peer_data = f"{self.peers_list[0][0]}:{self.peers_list[0][1]}... ({len(self.peers_list) - 1} more peers)"
            tracker_table.rows.append(['Peers', peer_data])

        return str(tracker_table)