import struct

"""
    As per Peer Wire Protocol all the messages exchanged in between 
    any two peers are of format given below 
    
    -----------------------------------------
    | Message Length | Message ID | Payload |
    -----------------------------------------
    
    Message Lenght (4 bytes) : length of message, excluding length part itself. 
    Message ID (1 bytes)     : defines the 9 different types of messages
    Payload                  : variable length stream of bytes

"""

# constant id for each message
KEEP_ALIVE      = None
CHOKE           = 0
UNCHOKE         = 1 
INTERESTED      = 2
UNINTERESTED    = 3
HAVE            = 4
BITFIELD        = 5
REQUEST         = 6
PIECE           = 7
CANCEL          = 8
PORT            = 9

# constant for message length
MESSAGE_LENGTH_SIZE = 4

# constant for message id
MESSAGE_ID_SIZE = 1

# constant handshake message length
HANDSHAKE_MESSAGE_LENGTH = 68

class peer_wire_message:
    def __init__(self, message_length, message_id, payload):
        self.message_length = message_length
        self.message_id = message_id
        self.payload = payload

    # return raw message
    def message(self):
        # pack the message length
        message = struct.pack("!I", self.message_length)

        # pack the message id
        if self.message_id is not None:
            message += struct.pack("!B", self.message_id)

        # pack the payload
        if self.payload is not None:
            message += self.payload
        
        return message
    
    # printing the peer wire message
    def __str__(self):
        message  = 'PEER WIRE MESSAGE : '
        message += '(message length : ' +  str(self.message_length) + '), '
        if self.message_id is None:
            message += '(message id : None), '
        else:
            message += '(message id : ' +  str(self.message_id)       + '), '
        if self.payload is None:
            message += '(protocol length : None)'
        else:
            message += '(payload length : ' +  str(len(self.payload)) + ')'
        return message
    
"""
    Handshake message format
    +------------+--------------------+------------+----------------+----------------+
    | 1 byte     | 19 bytes           | 8 bytes    | 20 bytes       | 20 bytes       |
    | Protocol   | Protocol Name      | Reserved   | Info Hash      | Peer ID        |
    +------------+--------------------+------------+----------------+----------------+
    Cấu trúc:
        Protocol Name Length (1 byte): Thường là 19 (độ dài chuỗi "BitTorrent protocol").
        Protocol Name (19 bytes): Chuỗi "BitTorrent protocol".
        Reserved (8 bytes): Đặt toàn bộ là 0.
        Info Hash (20 bytes): Hash SHA1 của thông tin tệp .torrent.
        Peer ID (20 bytes): Mã định danh của peer (tổng cộng là 20 bytes).
"""

class Handshake_message:
    def __init__(self, info_hash, client_peer_id):
        # protocol name : BTP 
        self.protocol_name = "BitTorrent protocol"
        # client peer info hash
        self.info_hash = info_hash
        # client peer id 
        self.client_peer_id = client_peer_id

    # return the raw hanshake message
    def message(self):
        # pack the protocol name
        message = struct.pack("!B", len(self.protocol_name))
        
        # pack the protocol name
        message += struct.pack("!19s", self.protocol_name.encode())

        # pack the reserved bytes
        message += struct.pack("!Q", 0x0)

        # pack the info hash
        message += struct.pack("!20s", bytes.fromhex(self.info_hash))

        # pack the peer id
        message += struct.pack("!20s", self.client_peer_id.encode())

        return message
    
    def validation(self, handshake_message):
        response_handshake_length = len(handshake_message)
        if response_handshake_length != HANDSHAKE_MESSAGE_LENGTH:
            print(f"Invalid handshake message length : {response_handshake_length}")
            return False
        
        peer_info_hash = handshake_message[28:48].hex()
        if peer_info_hash != self.info_hash:
            print(f"Invalid info hash : {peer_info_hash}")
            return False
        
        return True        
    
    # printing the handshake message
    def __str__(self):
        message  = 'HANDSHAKE MESSAGE : '
        message += '(protocol name : ' +  self.protocol_name + '), '
        message += '(info hash : ' +  str(self.info_hash) + '), '
        message += '(client peer id : ' +  str(self.client_peer_id) + ')'
        return message
    
def handshake_message_decode( handshake_message ):
    info_hash = struct.unpack_from("!20s", handshake_message, 28)[0].hex()
    peer_id = struct.unpack_from("!20s", handshake_message, 48)[0].decode()
    
    # return the decoded handshake message
    return Handshake_message(info_hash, peer_id)

class keep_alive( peer_wire_message ):
    def __init__(self):
        message_length  = 0
        message_id      = KEEP_ALIVE
        payload         = None
        super().__init__(message_length, message_id, payload)

    def __str__(self):
        message  = 'KEEP ALIVE : '
        message += '(message length : ' + str(self.message_length) + '), '
        message += '(message id : None), '
        message += '(message paylaod : None)'
        return message
    
class choke( peer_wire_message ):
    def __init__(self):
        message_length  = 1
        message_id      = CHOKE
        payload         = None
        super().__init__(message_length, message_id, payload)

    def __str__(self):
        message  = 'CHOKE : '
        message += '(message length : ' + str(self.message_length) + '), '
        message += '(message id : ' + str(self.message_id) + '), '
        message += '(message paylaod : None)'
        return message
    
class unchoke( peer_wire_message ):
    def __init__(self):
        message_length  = 1
        message_id      = UNCHOKE
        payload         = None
        super().__init__(message_length, message_id, payload)

    def __str__(self):
        message  = 'UNCHOKE : '
        message += '(message length : ' + str(self.message_length) + '), '
        message += '(message id : ' + str(self.message_id) + '), '
        message += '(message paylaod : None)'
        return message
    
class interested( peer_wire_message ):
    def __init__(self):
        message_length  = 1
        message_id      = INTERESTED
        payload         = None
        super().__init__(message_length, message_id, payload)

    def __str__(self):
        message  = 'INTERESTED : '
        message += '(message length : ' + str(self.message_length) + '), '
        message += '(message id : ' + str(self.message_id) + '), '
        message += '(message paylaod : None)'
        return message
    
class uninterested( peer_wire_message ):
    def __init__(self):
        message_length  = 1
        message_id      = UNINTERESTED
        payload         = None
        super().__init__(message_length, message_id, payload)

    def __str__(self):
        message  = 'UNINTERESTED : '
        message += '(message length : ' + str(self.message_length) + '), '
        message += '(message id : ' + str(self.message_id) + '), '
        message += '(message paylaod : None)'
        return message
    
class have( peer_wire_message ):
    def __init__(self, piece_index):
        message_length  = 5
        message_id      = HAVE
        payload         = struct.pack("!I", piece_index)

        self.piece_index = piece_index

        super().__init__(message_length, message_id, payload)

    def __str__(self):
        message  = 'HAVE : '
        message += '(message length : ' + str(self.message_length) + '), '
        message += '(message id : ' + str(self.message_id) + '), '
        message += '(message paylaod : [piece index : ' + str(self.piece_index) + '])'
        return message
    

# handle bitfield message
def bitfield_to_payload(bitfield):
    # pack the bitfield
    while len(bitfield) % 8 != 0:
        bitfield.append(0)

    bit_field_payload = b''
    for i in range(0, len(bitfield), 8):
        byte = 0
        for j in range(8):
            byte = byte << 1
            byte |= bitfield[i + j]
        bit_field_payload += struct.pack("!B", byte)

    return bit_field_payload



class Bitfield( peer_wire_message ):
    def __init__(self, bitfield_payload):    
        message_length  = len(bitfield_payload) + 1
        message_id      = BITFIELD
        payload         = bitfield_payload

        super().__init__(message_length, message_id, payload)

    # extract the bitfield from the payload
    def payload_to_bitfield(self):
        bitfield = []

        for byte in (self.payload):
            for i in range(8):
                bit = (byte >> (7 - i)) & 1
                bitfield.append(bit)

        # # Delete the extra bits
        # if len(bitfield) > total_pieces:
        #     bitfield = bitfield[:total_pieces]
        return bitfield

    def __str__(self):
        message  = 'BITFIELD : '
        message += '(message length : ' + str(self.message_length) + '), '
        message += '(message id : ' + str(self.message_id) + '), '
        message += '(message paylaod : [bitfield : ' + str(self.payload_to_bitfield()) + '])'
        return message
    
class request( peer_wire_message ):
    def __init__(self, piece_index, block_offset, block_length):
        message_length  = 13                                # 4 bytes message length
        message_id      = REQUEST                           # 1 byte message id
        payload         = struct.pack("!I", piece_index)    # 12 bytes payload
        payload        += struct.pack("!I", block_offset) 
        payload        += struct.pack("!I", block_length)

        self.piece_index    = piece_index
        self.block_offset   = block_offset
        self.block_length   = block_length

        super().__init__(message_length, message_id, payload)

    def __str__(self):
        message  = 'REQUEST : '
        message += '(message paylaod : [ '
        message += 'piece index : '     + str(self.piece_index)     + ', '
        message += 'block offest : '    + str(self.block_offset)    + ', '
        message += 'block length : '    + str(self.block_length)    + ' ])'
        return message
    
class piece(peer_wire_message):
    # the piece message for any block data from file
    def __init__(self, piece_index, block_offset, block):
        message_length  = 9 + len(block)                    # 4 bytes message length
        message_id      = PIECE                             # 1 byte message id
        payload         = struct.pack("!I", piece_index)    # variable length payload
        payload        += struct.pack("!I", block_offset)
        payload        += block

        self.piece_index    = piece_index
        self.block_offset   = block_offset
        self.block          = block 

        super().__init__(message_length, message_id, payload)

    def __str__(self):
        message  = 'PIECE : '
        message += '(message paylaod : [ '
        message += 'piece index : '     + str(self.piece_index)     + ', '
        message += 'block offest : '    + str(self.block_offset)    + ', '
        message += 'block length : '    + str(len(self.block))      + ' ])'
        return message
    
class Peer_message_decoder():

    # initialize peer_message_decoder with given peer wire message instance
    def decode(self, peer_message):
        
        # deocdes the given peer_message
        if peer_message.message_id == KEEP_ALIVE :
            self.peer_decoded_message = keep_alive()

        elif peer_message.message_id == CHOKE :    
            self.peer_decoded_message = choke()

        elif peer_message.message_id == UNCHOKE :        
            self.peer_decoded_message = unchoke()

        elif peer_message.message_id == INTERESTED :     
            self.peer_decoded_message = interested()

        elif peer_message.message_id == UNINTERESTED :
            self.peer_decoded_message = uninterested()

        elif peer_message.message_id == HAVE :
            piece_index = struct.unpack_from("!I", peer_message.payload)[0]
            self.peer_decoded_message = have(piece_index)

        elif peer_message.message_id == BITFIELD :
            self.peer_decoded_message = Bitfield(peer_message.payload)

        elif peer_message.message_id == REQUEST :        
            piece_index  = struct.unpack_from("!I", peer_message.payload, 0)[0]
            block_offset = struct.unpack_from("!I", peer_message.payload, 4)[0]
            block_length = struct.unpack_from("!I", peer_message.payload, 8)[0]
            self.peer_decoded_message = request(piece_index, block_offset, block_length)

        elif peer_message.message_id == PIECE :          
            piece_index  = struct.unpack_from("!I", peer_message.payload, 0)[0]
            begin_offset = struct.unpack_from("!I", peer_message.payload, 4)[0]
            block = peer_message.payload[8:]
            self.peer_decoded_message = piece(piece_index, begin_offset, block)
        
        # returns the peer decoded message
        return self.peer_decoded_message