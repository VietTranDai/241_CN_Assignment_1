import time
from peer_wire_messages import *
from peer_socket import Peer_socket
from io_file_handler import torrent_shared_file_handler

import hashlib


class Peer_connection():
    def __init__(self, peer_ip, peer_port, client_peer_id, torrent_metadata, torrent_log, data_folder_path, peer_socket = None):
        # peer ip, port, and socket
        self.peer_ip = peer_ip
        self.peer_port = peer_port

        # torrent log
        self.torrent_log = torrent_log

        # data folder path
        self.data_folder_path = data_folder_path

        # info hash
        self.torrent_metadata = torrent_metadata
        self.info_hash = None
        if self.torrent_metadata:
            self.info_hash = self.torrent_metadata.info_hash

        # client peer id
        self.client_peer_id = client_peer_id

        # peer socket
        self.peer_sock = Peer_socket(peer_ip, peer_port, peer_socket)

        # peer id
        self.peer_id = None

        # block size
        if self.torrent_metadata:
            self.block_length = torrent_metadata.block_length

        # file_handler for file operations
        self.file_handler = None

        # handshake flag
        self.handshake_flag = False

        # bitfield
        self.bitfield = None

        # response message handler for recieved message
        self.response_handler = { KEEP_ALIVE    : self.recieved_keep_alive,
                                  HAVE          : self.recieved_have, 
                                  BITFIELD      : self.recieved_bitfield,
                                  REQUEST       : self.recieved_request,
                                  PIECE         : self.recieved_piece
                                }
        
    def update_torrent_metadata(self, torrent_metadata):
        self.torrent_metadata = torrent_metadata
        self.info_hash = self.torrent_metadata.info_hash
        self.block_length = torrent_metadata.block_length

        self.file_handler = torrent_shared_file_handler(self.torrent_metadata, self.data_folder_path)

        print(f"Torrent metadata: {self.torrent_metadata}")

    """
        ======================================================================
                            CONNECTION PEER HADNLER FUNCTIONS 
        ======================================================================
    """

    '''
        function to request connection to the peer
    '''
    def send_connection_request(self):
        print(f"Connecting to peer {self.peer_ip}:{self.peer_port}")
        connection_status = None
        if self.peer_sock.request_connection():
            print(f"Connected to peer {self.peer_ip}:{self.peer_port}")
            connection_status = True
        else:
            print(f"Connection to peer {self.peer_ip}:{self.peer_port} failed")
            connection_status = False

        return connection_status

    '''
        function to start handle listening
    '''
    def start_listening(self):
       self.peer_sock.config_socket_to_listening()


    '''
        function to accept connection from the peer
    '''
    def accept_connection(self):
        self.peer_sock.accept_connection()

    """
        disconnects the peer socket connection
    """
    def close_peer_connection(self):
        self.peer_sock.disconnect()


    """
        function helps in recieving data from peers
    """
    def recieve(self, data_size):
        return self.peer_sock.recieve_data(data_size)

    """
        function helps send raw data to the peer connection
        function sends the complete message to peer
    """
    def send(self, raw_data):
        if not self.peer_sock.send_data(raw_data):
            print(f"Failed to send data to peer {self.peer_ip}:{self.peer_port}")
            self.close_peer_connection()

    """
        function helps in sending peer messgae given peer wire message 
        class object as an argument to the function
    """
    def send_message(self, peer_request):
        if self.handshake_flag:
            # send the message 
            self.send(peer_request.message())

    """
        functions helpes in recieving peer wire protocol messages.
    """
    def recieve_message(self):
        # extract the peer wire message information by receiving chunks of data
        # recieve the message length 
        raw_message_length = self.recieve(MESSAGE_LENGTH_SIZE)
        if raw_message_length is None or len(raw_message_length) < MESSAGE_LENGTH_SIZE:
            return None

        # unpack the message length which is 4 bytes long
        message_length = struct.unpack_from("!I", raw_message_length)[0]
        # keep alive messages have no message ID and payload
        if message_length == 0:
            return peer_wire_message(message_length, None, None)

        # attempt to recieve the message ID from message
        raw_message_ID =  self.recieve(MESSAGE_ID_SIZE)
        if raw_message_ID is None:
            return None
        
        # unpack the message length which is 4 bytes long
        message_id  = struct.unpack_from("!B", raw_message_ID)[0]
        # messages having no payload 
        if message_length == 1:
            return peer_wire_message(message_length, message_id, None)
       
        # extract all the payload
        payload_length = message_length - 1
        
        # extract the message payload 
        message_payload = self.recieve(payload_length)
        if message_payload is None:
            return None
        
        # keep alive timer updated 
        self.keep_alive_timer = time.time()

        # return peer wire message object given the three parameters
        return peer_wire_message(message_length, message_id, message_payload)
    
    
    """
        functions helps in initiating handshake with the peer
    """
    def initiate_handshake(self):
        # only do handshake if not earlier and established TCP connection
        if self.send_connection_request():
            # send handshake message
            handshake_message = Handshake_message(self.info_hash, self.client_peer_id).message()
            self.send(handshake_message)

            # recieve handshake message
            raw_handshake_response = self.recieve(HANDSHAKE_MESSAGE_LENGTH)
            if raw_handshake_response is None:
                return False
            
            # validate the hanshake message recieved obtained
            handshake_response = self.handshake_validation(raw_handshake_response)
            if handshake_response is None:
                return False
            
            self.handshake_flag = True
            # handshake success 
            return True
        # already attempted handshake with the peer
        return False
    
    def handshake_validation(self, raw_handshake_response):
        handshake_message = Handshake_message(self.info_hash, self.client_peer_id)
        if(handshake_message.validation(raw_handshake_response)):
            return handshake_message
        return None
    
    
    '''
        function to send bitfield message to the peer
    '''
    def set_bitfield(self):
        self.bitfield = self.torrent_log.get_bitfield(self.info_hash)

    def initialize_bitfield(self):
        # peer connection not established
        if not self.peer_sock.peer_connection_active():
            return self.bitfield
        # recieve only if handshake is done successfully
        if not self.handshake_flag:
            return self.bitfield
        # loop for all the message that are recieved by the peer
        messages_begin_recieved = True
        while(messages_begin_recieved):
            # handle responses recieved
            response_message = self.handle_response()
            # if you no respone message is recieved 
            if response_message is None: 
                messages_begin_recieved = False
        # returns bitfield obtained by the peer
        return self.bitfield

    """
        function handles any peer message
    """
    def handle_response(self):
        # recieve messages from the peer
        peer_response_message = self.recieve_message()
        # if there is no response from the peer
        if peer_response_message is None:
            return None

        # DECODE the peer wire message into appropriate peer wire message type type
        decoded_message = Peer_message_decoder().decode(peer_response_message)
        if decoded_message is None:
            return None

        # select the respective message handler 
        message_handler = self.response_handler[decoded_message.message_id]
        message_handler(decoded_message)

        return decoded_message




    """
            ======================================================================
                            RECIVED MESSAGES HADNLER FUNCTIONS 
            ======================================================================
    """
    """
        function checks if the peer has the piece or not
    """
    def have_piece(self, piece_index):
        return self.bitfield[piece_index] == 1

    """
        Add file handler to the peer connection to read and write file
    """
    def add_file_handler(self, file_handler):
        self.file_handler = file_handler

    """
        function validates if correct block was recieved from peer for the request
    """
    def validate_request_piece_messages(self, request, piece):
        if request.piece_index != piece.piece_index:
            return False
        if request.block_offset != piece.block_offset:
            return False
        if request.block_length != len(piece.block):
            return False
        return True

    """
        recieved keepalive      : indicates peer is still alive in file sharing
    """
    def recieved_keep_alive(self, keep_alive_message):
        # reset the timer when keep alive is recieved
        print(f"Keep alive message recieved from peer {self.peer_ip}:{self.peer_port} with meesage {keep_alive_message}")
        self.keep_alive_timer = time.time()

    '''
        recieved handshake      : peer sends the handshake message to client
    '''
    def recieved_handshake(self, handshake_message):
        print(f"Handshake message recieved from peer {self.peer_ip}:{self.peer_port} with meesage {handshake_message}")
        if self.handshake_flag:
            return True
        
        handshake_info = handshake_message_decode(handshake_message)
        if handshake_info is None:
            print(f"Handshake message decode failed for peer {self.peer_ip}:{self.peer_port}")
            return False
        
        self.update_torrent_metadata(self.torrent_log.get_torrent_metadata_by_infohash(handshake_info.info_hash))
        
        # send handshake message
        handshake_message = Handshake_message(self.info_hash, self.client_peer_id).message()
        self.send(handshake_message)

        self.handshake_flag = True

        # send bitfield message to the peer
        try:
            self.send_bitfield()
            print(f"Bitfield message sent to peer {self.peer_ip}:{self.peer_port}.")
        except Exception as e:
            print(f"Failed to send bitfield: {e}")
            self.close_peer_connection()
            return False

        return True

    """
        recieved bitfields      : peer sends the bitfiled values to client 
                                    after recieving the bitfields make client interested
    """
    def recieved_bitfield(self, bitfield_message):
        print(f"Bitfield message recieved from peer {self.peer_ip}:{self.peer_port} with meesage {bitfield_message}")
        # extract the bitfield piece information from the message
        cur_bitfield = bitfield_message.payload_to_bitfield()
        self.total_pieces = self.torrent_metadata.pieces_count
        # update the bitfield information in the peer bitfiled fixed length
        self.bitfield = cur_bitfield[:self.total_pieces]


    """
        recieved have           : peer sends information of piece that it has
    """
    def recieved_have(self, have_message):
        print(f"Have message recieved from peer {self.peer_ip}:{self.peer_port} with meesage {have_message}")
        # update the piece information in the peer bitfiled 
        # self.torrent_log.update_bitfield(self.info_hash, have_message.piece_index, 1)
        self.bitfield = self.torrent_log.get_bitfield(self.info_hash)
        
    """
        recieved request        : peer has requested some piece from client
    """
    def recieved_request(self, request_message):
        print(f"Request message recieved from peer {self.peer_ip}:{self.peer_port} with meesage {request_message}")
        # extract block requested
        piece_index     = request_message.piece_index
        block_offset    = request_message.block_offset
        block_length    = request_message.block_length
        # validate the block requested exits in file
        if self.torrent_metadata.validate_piece_length(piece_index, block_offset, block_length):
            # read the datablock 
            data_block = self.file_handler.read_block(piece_index, block_offset, block_length)
            # create response piece message and send it the peer
            response_message = piece(piece_index, block_offset, data_block)
            self.send_message(response_message)
        else:
            print(f"Block requested not found for piece {piece_index} block {block_offset} length {block_length}")
            return None

    """
        recieved piece          : peer has responed with the piece to client
                                    after recieving any piece, it is written into file
    """
    def recieved_piece(self, piece_message):
        print(f"Piece message recieved from peer {self.peer_ip}:{self.peer_port} with meesage {piece_message}")
        # write the block of piece into the file
        self.file_handler.write_block(piece_message) 


    """
        ======================================================================
                            SEND MESSAGES HADNLER FUNCTIONS 
        ======================================================================
    """
    
    """
        send keep alive         : client message to keep the peer connection alive
    """
    def send_keep_alive(self):
        self.send_message(keep_alive())

    """
        send have               : client has the given piece to offer the peer
    """
    def send_have(self, piece_index):
        self.send_message(have(piece_index))
    
    """
        send bitfield           : client sends the bitfield message of pieces
    """
    def send_bitfield(self):
        self.set_bitfield()
        bitfield_payload = bitfield_to_payload(self.bitfield)
        self.send_message(Bitfield(bitfield_payload))
    
    
    """
        send request            : client sends request to the peer for piece
    """
    def send_request(self, piece_index, block_offset, block_length):
        self.send_message(request(piece_index, block_offset, block_length))
    

    """
        send piece              : client sends file's piece data to the peer 
    """
    def send_piece(self, piece_index, block_offset, block_data):
        self.send_message(piece(piece_index, block_offset, block_data))



    """
        ======================================================================
                            DOWNLOAD HADNLER FUNCTIONS 
        ======================================================================
    """
    def download_possible(self):
        # socket connection still active to recieve/send
        if not self.peer_sock.peer_connection_active():
            return False
        # if peer has not done handshake piece will never be downloaded
        if not self.handshake_flag:
            return False
        # all conditions satisfied 
        return True
    
    """
        function validates if correct block was recieved from peer for the request
    """
    def validate_request_piece_messages(self, request, piece):
        if request.piece_index != piece.piece_index:
            return False
        if request.block_offset != piece.block_offset:
            return False
        if request.block_length != len(piece.block):
            return False
        return True
    
    """
        function validates piece recieved and given the piece index.
    """
    def validate_piece(self, piece, piece_index):
        # compare the length of the piece recieved
        piece_length = self.torrent_metadata.get_piece_length(piece_index)
        if (len(piece) != piece_length):
            print(f"Piece length not matched for piece {piece_index}")
            return False

        piece_hash = hashlib.sha1(piece).digest()
        index = piece_index * 20
        torrent_piece_hash = self.torrent_metadata.pieces[index : index + 20]
        
        # compare the pieces hash with torrent file piece hash
        if piece_hash != torrent_piece_hash:
            print(f"Piece hash not matched for piece {piece_index}")
            return False
        return True

    def download_piece( self, piece_index):
        if not self.have_piece(piece_index):
            return False
        
        if not self.download_possible():
            return False

        # recieved piece data from the peer
        recieved_piece = b''  
        # block offset for downloading the piece
        block_offset = 0
        # block length 
        block_length = 0
        # piece length for torrent 
        piece_length = self.torrent_metadata.get_piece_length(piece_index)

        # loop untill you download all the blocks in the piece
        while self.download_possible() and block_offset < piece_length:
            # find out how much max length of block that can be requested
            if piece_length - block_offset >= self.block_length:
                block_length = self.block_length
            else:
                block_length = piece_length - block_offset
            
            block_data = self.download_block(piece_index, block_offset, block_length)
            if block_data:
                # increament offset according to size of data block recieved
                recieved_piece += block_data
                block_offset   += block_length
        
        # validate the piece and update the peer downloaded bitfield
        if(not self.validate_piece(recieved_piece, piece_index)):
            return False
        
        # updata the bitfield of the peer
        self.torrent_log.update_bitfield(self.info_hash, piece_index, 1)
    
        return True
    
    """
        function helps in download given block of the piece from peer
    """
    def download_block(self, piece_index, block_offset, block_length):
        # create a request message for given piece index and block offset
        request_message = request(piece_index, block_offset, block_length)
        # send request message to peer
        self.send_message(request_message)
        
        # recieve response message and handle the response
        response_message = self.handle_response()
        
        # if the message recieved was a piece message
        if not response_message or response_message.message_id != PIECE:
            print(f"Failed to download block {block_offset} of piece {piece_index}")
            return None
        # validate if correct response is recieved for the piece message
        if not self.validate_request_piece_messages(request_message, response_message):
            print(f"Block {block_offset} of piece {piece_index} validation failed")
            return None

        # successfully downloaded and validated block of piece
        return response_message.block

    """
        ======================================================================
                            UPLOAD HADNLER FUNCTIONS 
        ======================================================================
    """
     
    """ 
        piece can be only uploaded only upon given conditions
    """
    def upload_possible(self):
        # socket connection still active to recieve/send
        if not self.peer_sock.peer_connection_active():
            return False
        # if peer has not done handshake piece will never be downloaded
        if not self.handshake_flag:
            return False
        # all conditions satisfied 
        return True
