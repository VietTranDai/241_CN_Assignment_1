from socket import *
from select import *
from threading import *
import sys


# class for general peer socket 
class Peer_socket():
    def __init__(self, peer_ip, peer_port, peer_socket = None):
        if peer_socket is None:
            # initializing a peer socket for TCP communiction 
            self.peer_socket = socket(AF_INET, SOCK_STREAM)
            # peer connection
            self.peer_connection = False
        else:
            # peer connection
            self.peer_connection = True
            # initializing using the constructor argument socket
            self.peer_socket = peer_socket
        
        self.timeout = 5
        self.peer_socket.settimeout(self.timeout)
        
        # IP and port of the peer
        self.ip        = peer_ip
        self.port       = peer_port

        # the maximum peer request
        self.max_peer_requests = 50


    # function to configure the socket to listening
    def config_socket_to_listening(self):
        try:
            self.peer_socket.bind((self.IP, self.port))
            self.peer_socket.listen(self.max_peer_requests)
        except Exception as err:
            print(f"Error in seeding: {err}")
            sys.exit(0)

    """
        function returns raw data of given data size which is recieved 
        function returns the exact length data as recieved else return None
    """
    def recieve_data(self, data_size):
        if not self.peer_connection:
            return 
        peer_raw_data = b''
        recieved_data_length = 0
        request_size = data_size
        
        # loop untill you recieve all the data from the peer
        while(recieved_data_length < data_size):
            # attempt recieving requested data size in chunks
            try:
                chunk = self.peer_socket.recv(request_size)
            except:
                chunk = b''
            if len(chunk) == 0:
                return None
            peer_raw_data += chunk
            request_size -=  len(chunk)
            recieved_data_length += len(chunk)

        # return required size data recieved from peer
        return peer_raw_data
   
    """
        function helps send raw data by the socket
        function sends the complete message, returns success/failure depending
        upon if it has successfully send the data
    """
    def send_data(self, raw_data):
        if not self.peer_connection:
            return False
        data_length_send = 0
        while(data_length_send < len(raw_data)):
            try:
                # attempting to send data 
                data_length_send += self.peer_socket.send(raw_data[data_length_send:])
            except:
                # the TCP connection is broken
                return False
        return True

    """
        attempts to connect the peer using TCP connection 
    """
    def request_connection(self):
        try:
            self.peer_socket.connect((self.ip, self.port))
            self.peer_connection = True
        except Exception as err:
            self.peer_connection = False
            print(f"Connection to {self.ip}:{self.port} failed with error: {err}")
        return self.peer_connection
    
    """
        accepts an incomming connection
        return connection socket and ip address of incoming connection
    """
    def accept_connection(self):

        try:
            connection = self.peer_socket.accept()
            print(f"Connection accepted from {connection[1]}")
        except Exception as err:
            connection = None
            print(f"Error in accepting connection: {err}")
        
        return connection


    """
        checks if the peer connection is active or not
    """
    def peer_connection_active(self):
        return self.peer_connection

    """
        disconnects the socket
    """
    def disconnect(self):
        self.peer_socket.close() 
        self.peer_connection = False

