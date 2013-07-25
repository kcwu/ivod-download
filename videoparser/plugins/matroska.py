#
#  Copyright (c) 2007 Michael van Tellingen <michaelvantellingen@gmail.com>
#  All rights reserved.
# 
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions
#  are met:
#  1. Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#  2. The name of the author may not be used to endorse or promote products
#     derived from this software without specific prior written permission
# 
#  THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
#  IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
#  OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
#  IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
#  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
#  NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
#  THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

"""
    EBML / Matroska header parser
    
    See http://www.matroska.org/technical/specs/index.html
"""

# Project modules
import videoparser.plugins as plugins
import videoparser.streams as streams

__all__ = ['Parser']

class Types:
    string          = 1
    sub_elements    = 2
    u_integer       = 3
    float           = 4
    binary          = 5
    utf_8           = 6

types = Types()

# Only implement required information to retrieve video and audio information

#   Class-id        Element-name           Element-type     Element-level
class_ids = {

    # EBML Basics
    0x1a45dfa3:     ('EBML',               types.sub_elements,  0),
    0x4282:         ('DocType',            types.string,    1),
    0x4287:         ('DocTypeVersion',     types.u_integer, 1),
    0x4285:         ('DocTypeReadVersion', types.u_integer, 1),
        
    # Global data
    0xEC:           ('Void',  types.binary, 1),
    
    # The main elements (level 0)
    0x18538067:     ('Segment',     types.sub_elements, 0), # Segment
    0x114D9B74:     ('SeekHead',    types.sub_elements, 1), # Meta Seek Info
    0x1549a966:     ('Info',        types.sub_elements, 1), # Segment Info
    0x1F43B675:     ('Cluster',     types.sub_elements, 1), # Cluster
    0x1c53bb6b:     ('Cues',        types.sub_elements, 1),    
        
    # Tracks (This is were we are interested in)
    0x1654AE6B:     ('Tracks',          types.sub_elements, 1), 
    0xAE:           ('TrackEntry',      types.sub_elements, 2),
    0xD7:           ('TrackNumber',     types.u_integer,    3),
    0x73C5:         ('TrackUID',        types.u_integer,    3),
    0x83:           ('TrackType',       types.u_integer,    3),
    0xB9:           ('FlagEnabled',     types.u_integer,    3),
    0x88:           ('FlagDefault',     types.u_integer,    3),
    0x55AA:         ('FlagForced',      types.u_integer,    3),
    0x9C:           ('FlagLacing',      types.u_integer,    3),
    0x6DE7:         ('MinCache',        types.u_integer,    3),
    0x6DF8:         ('MaxCache',        types.u_integer,    3),
    0x23E383:       ('DefaultDuration', types.u_integer,    3),
    0x23314F:       ('TrackTimecodeScale', types.float,     3),
    
    0x55EE:         ('MaxBlockAdditionID',  types.u_integer, 3),
    0x536E:         ('Name',                types.utf_8,     3),
    0x22B59C:       ('Language',            types.string,    3),
    0x86:           ('CodecID',             types.string,    3),
    0x63A2:         ('CodecPrivate',        types.binary,    3),
    0x258688:       ('CodecName',           types.utf_8,     3),
    0x7446:         ('AttachmentLink',      types.u_integer, 3),
    0xAA:           ('CodecDecodeAll',      types.u_integer, 3),
    
    # Video specific elements
    0xE0:           ('Video',           types.sub_elements, 3),
    0x1a:           ('FlagInterlaced',  types.u_integer,    4),
    0xB0:           ('PixelWidth',      types.u_integer,    4),
    0xBA:           ('PixelHeight',     types.u_integer,    4),
    0x54B0:         ('DisplayWidth',    types.u_integer,    4),
    0x54BA:         ('DisplayHeight',   types.u_integer,    4),
    0x9A:           ('Unknown',         types.u_integer,    4),

    # Audio specific elements
    0xE1:           ('Audio', types.sub_elements,       3),        
    0xB5:           ('SamplingFrequency', types.float,  4),
    0x9F:           ('Channels', types.u_integer,       4),
    0x6264:         ('BitDepth', types.u_integer,       4),
}




class Parser(plugins.BaseParser):
    _endianess = streams.endian.big
    _file_types = ['mkv']
    
    def __init__(self, *args, **kwargs):
        plugins.BaseParser.__init__(self, *args, **kwargs)

        
    def parse(self, filename, video):
        
        
        stream = streams.factory.create_filestream(filename,
                                                   endianess=self._endianess)

        # Check if this is an EBML file
        if stream.read_uint32() != 0x1a45dfa3:
            return False
        stream.seek(0)
        
        video.set_container('matroska')
        
        tree = self._build_tree(stream)
        self._extract_information(tree, video)
    
        return True


    def _build_tree(self, stream):
        """ Iterate over all the elements in the file and create a tree out of
            it. """

                
        parsed_tracks_element = False

        previous_element = self.LevelElement()
        previous_element.key = 'Root'
        previous_element.parent = None
        previous_element.level = -1
        root_elm = previous_element
        
        for elm in self.parse_header(stream):
            if elm is None:
                continue

            # Create element
            obj = self.LevelElement()
            obj.key, obj.value, obj.level = elm
            
            if parsed_tracks_element and obj.level == 1:
                break
            
            if obj.key == 'Tracks':
                parsed_tracks_element = True
            
            # We are going back in the tree
            if obj.level < previous_element.level:
                while obj.level <= previous_element.level:
                    previous_element = previous_element.parent
                obj.parent = previous_element
                
            # We are going deeper in the tree (child of previous_element)
            elif obj.level > previous_element.level:
                obj.parent = previous_element
                
            # We are on the same level als the previous_element
            else:
                obj.parent = previous_element.parent

            obj.parent.childs.append(obj)
            previous_element = obj
            
        return root_elm

    
    def _extract_information(self, tree, video):
        for track in tree.Segment[0].Tracks[0].TrackEntry:
            if track.TrackType[0].value == 1:
                stream = video.new_video_stream()
                
                vid = track.Video[0]
                stream.set_width(vid.PixelWidth[0].value)
                stream.set_height(vid.PixelHeight[0].value)
                
                timecodescale = track.TrackTimecodeScale[0].value
                stream.set_framerate(23.976 * timecodescale)
                stream.set_duration(seconds=track.DefaultDuration[0].value /
                                    (1000000.0 * timecodescale))
                
                stream.set_codec(track.CodecID[0].value)
            
            if track.TrackType[0].value == 2:
                stream = video.new_audio_stream()
                audio = track.Audio[0]
                stream.set_channels(audio.Channels[0].value)
                stream.set_sample_rate(audio.SamplingFrequency[0].value)
                stream.set_codec(track.CodecID[0].value)
        

            
    
    
    def parse_header(self, stream):
        
        # Elements incorporate an Element ID, a descriptor for the size of the
        # element, and the binary data itself.
        
        while stream.bytes_left():
            # Fetch the element id
            octet = stream.read_byte()
            
            classid_size, classid_bytes = self.parse_octet(octet)
            
            # Read all the bytes from the complete class-id:
            if classid_size > 1:
                class_id = stream.convert_uintvar(octet +
                                                  stream.read(classid_size-1))
            else:
                class_id = ord(octet)
            
            # Fetch the descriptor for the size of the element
            octet = stream.read_byte()
            length_bytes, length =  self.parse_octet(octet)
            length = stream.convert_uintvar(chr(length) +
                                            stream.read(length_bytes-1))
            
            try:
                value = None
                class_name, class_type, class_level = class_ids[class_id]
                
                if class_type == types.string:
                    value = stream.read(length)
                    
                elif class_type == types.u_integer:
                    value = stream.convert_uintvar(stream.read(length))
    
                elif class_type == types.binary:
                    stream.seek(stream.tell() + length)
                
                elif class_type == types.float:
                    value = stream.read_float()
                    
                elif class_type == types.utf_8:
                    value = stream.read(length)
                    
                elif class_type == types.sub_elements:
                    if class_name in ['Info', 'SeekHead', 'Cluster', 'Cues']:
                        stream.seek(stream.tell() + length)
                        continue
                    
                yield (class_name, value, class_level)
                
            except KeyError:
                #raise AssertionError("Unhandled class-id: %s" % hex(class_id))
                print "Unhandled class-id: %s" % hex(class_id)
                continue
    
    
    def parse_octet(self, octet):
        """ Retrieve the length of the class-id. """
        
        octet = ord(octet)

        # The bytesize of the class-id is the number of leading 0 bits + 1
        # The value stored in this byte is with the marker bit removed (which
        #  is the highest bit)
        
        if octet == 0x00:
            return (None, None)

        # Calculate the length of the class-id            
        mask = 0x80
        length = 1
        while mask:
            if octet & mask:
                break

            length += 1
            mask >>= 1

        # return the bytesize and the value with the marker bit xor'ed out
        return (length, octet ^ 2**(8-length))


    class LevelElement(object):
        __slots__ = ['key', 'value', 'level', 'childs', 'parent'    ]
        
        def __init__(self):
            self.childs = []

        def __repr__(self):
            
            buffer = "  " * (self.level + 1) + self.key + "\n"
            for child in self.childs:
                buffer += repr(child)
            return buffer
        
        def __getattr__(self, key):
            if key == 'value':
                return self.value
            
            if key == 'key':
                return self.key
            
            
            items = []
            
            for child in self.childs:
                if child.key == key:
                    items.append(child)
            
            if len(items) == 0:
                raise AttributeError(key)
            return items
