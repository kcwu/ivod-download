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
    RealMedia parser
    Based on:
        - http://www.multimedia.cx/rmff.htm
        - http://wiki.multimedia.cx/index.php?title=RealMedia
"""

import videoparser.plugins as plugins
import videoparser.streams as streams
import videoparser.types as types

class Parser(plugins.BaseParser):
    _endianess = streams.endian.big
    _file_types = ['rm']
    
    def __init__(self):
        plugins.BaseParser.__init__(self)

    def parse(self, filename, video):
        stream = streams.factory.create_filestream(filename,
                                                   endianess=self._endianess)
        if stream.read_fourcc() != '.RMF':
            return False
        stream.seek(0)
        
        data = self.parse_objects(stream)

        # Extract required information from the tree and place it in the
        # videofile object
        self.extract_information(data, video)
        
        return True

    def parse_objects(self, stream):
        objects = []
        while stream.bytes_left():
            id = stream.read_fourcc()
            size = stream.read_uint32()
            
            # It seems some files have random junk data after the INDX object
            if id == '\x00\x00\x00\x00':
                break

            if id in ['.RMF', 'PROP', 'MDPR', 'CONT']: #, 'DATA']:
                data = stream.read_subsegment(size - 8)
            else:
                stream.seek(stream.tell() + size - 8)
                continue
            
            if id == '.RMF':
                obj = self._parse_realmedia_file(data)
            
            elif id == 'PROP':
                obj = self._parse_fileproperties(data)
            
            elif id == 'MDPR':
                obj = self._parse_mediaproperties(data)
            
            elif id == 'CONT':
                obj = self._parse_contentdescription(data)
            
            #elif id == 'DATA':
            #    for i in range(0, 2):
            #        print repr(data.read(10))
            objects.append(obj)
            
        return objects


    def extract_information(self, data, video):
        for object in data:
            if object and object.id == 'MediaProperties':
                if object.mime_type == 'logical-fileinfo':
                    continue
                
                if object.mime_type == 'audio/x-pn-realaudio':
                    stream = video.new_audio_stream()
                    data = object.type_specific_data
                    stream.set_duration(microseconds=object.duration * 1000)
                    stream.set_sample_rate(data.sample_rate)
                    stream.set_bit_per_sample(data.sample_size)
                    stream.set_channels(data.num_channels)
                    stream.set_codec(data.fourcc_string)
                    
                if object.mime_type == 'video/x-pn-realvideo':
                    stream = video.new_video_stream()
                    data = object.type_specific_data
                    stream.set_duration(microseconds=object.duration * 1000)
                    stream.set_width(data.width)
                    stream.set_height(data.height)
                    stream.set_framerate(data.fps)
                    stream.set_codec(data.codec)
                    
                    
    def _parse_realmedia_file(self, data):
        """  RealMedia file header (.RMF) """
        return None

    def _parse_fileproperties(self, data):
        """ Parse the File properties header (PROP) """
        obj = plugins.Structure('FileProperties')
        obj.set('version', data.read_uint16(), types.int, 'Version')

        if obj.version == 0:
            obj.set('max_bit_rate', data.read_uint32(),
                    types.int, 'Maximum bitrate')
            
            obj.set('avg_bit_rate', data.read_uint32(),
                    types.int, 'Average bitrate')
            
            obj.set('max_packet_size', data.read_uint32(),
                    types.int, 'Maximum packet size')
            
            obj.set('avg_packet_size', data.read_uint32(),
                    types.int, 'Average packet size')
            
            obj.set('num_packets', data.read_uint32(),
                    types.int, 'Number of packets')
            
            obj.set('duration', data.read_uint32(),
                    types.int, 'Duration')
            
            obj.set('preroll', data.read_uint32(),
                    types.int, 'Preroll')
            
            obj.set('index_offset', data.read_uint32(),
                    types.int, 'Index offset')
            
            obj.set('data_offset', data.read_uint32(),
                    types.int, 'Data offset')
            
            obj.set('num_streams', data.read_uint16(),
                    types.int, 'Number of streams')
            
            obj.set('flags', data.read_uint16(),
                    types.int, 'Flags')
    
        
        return obj
    
    def _parse_mediaproperties(self, data):
        """ Parse the  Media properties header (MDPR)"""
        obj = plugins.Structure('MediaProperties')
        obj.set('version', data.read_uint16(), types.int, 'Version')
        
        if obj.version == 0:
            obj.set('stream_number', data.read_uint16(),
                    types.int, 'Stream number')
            
            obj.set('max_bit_rate', data.read_uint32(),
                    types.int, 'Maximum bitrate')

            obj.set('avg_bit_rate', data.read_uint32(),
                    types.int, 'Average bitrate')
            
            obj.set('max_packet_size', data.read_uint32(),
                    types.int, 'Maximum packet size')
            
            obj.set('avg_packet_size', data.read_uint32(),
                    types.int, 'Average packet size')
            
            obj.set('start_time', data.read_uint32(),
                    types.int, 'Start time')
            
            obj.set('preroll', data.read_uint32(),
                    types.int, 'Preroll')
            
            obj.set('duration', data.read_uint32(),
                    types.int, 'Duration')
            
            # Stream name
            obj.set('stream_name_size',  data.read_uint8(),
                    types.int, 'Stream name length')
            
            obj.set('stream_name',  data.read(obj.stream_name_size),
                    types.string, 'Stream name')
            
            
            # Mime-type
            obj.set('mime_type_size',  data.read_uint8(),
                    types.int, 'MIME-type length')
            
            obj.set('mime_type',  data.read(obj.mime_type_size),
                    types.string, 'MIME-type')
            
            
            # Type specific data
            obj.set('type_specific_len',  data.read_uint32(),
                    types.int, 'Type specific data length')

            type_data = data.read_subsegment(obj.type_specific_len)

            # Parse the type specific data based on the mime-type
            if obj.mime_type == 'video/x-pn-realvideo':
                type_specific_data = self._parse_type_realvideo(type_data)
            elif obj.mime_type == 'audio/x-pn-realaudio':
                type_specific_data = self._parse_type_realaudio(type_data)
            else:
                type_specific_data = type_data

            obj.set('type_specific_data', type_specific_data,
                    types.object, 'Type specific data')
            
        return obj


    def _parse_type_realvideo(self, data):
        
        # This is based on guessing, so it might not be 100% ok.
        # i still need to find the framerate (atleast i suppose it is included)
        
        obj = plugins.Structure('RealVideoProperties')
        obj.set('version', data.read_uint16(), types.int, 'Version')
        obj.set('size', data.read_uint16(), types.int, 'Size')
        obj.set('type', data.read_fourcc(), types.string, 'Type')
        obj.set('codec', data.read_fourcc(), types.string, 'Codec')
        obj.set('width', data.read_uint16(), types.int, 'Width')
        obj.set('height', data.read_uint16(), types.int, 'Height')

        # Skip over 6 unknown bytes        
        data.seek(data.tell() + 6)
        
        obj.set('fps', data.read_qtfloat_32(),
                types.float, 'Frames per second')

        # Ignore the other unknown bytes
        
        return obj
        
        
    def _parse_type_realaudio(self, data):

        # Based on information at:
        # http://wiki.multimedia.cx/index.php?title=RealMedia
        obj = plugins.Structure('RealAudioProperties')
        obj.set('type', data.read_fourcc(), types.string, 'Type')
        obj.set('version', data.read_uint16(), types.int, 'Version')
        
        if obj.version == 3:
            pass
            
        elif obj.version in [4, 5]:
            obj.set('unused', data.read_uint16(), types.int, 'Size')
            obj.set('signature',  data.read(4), types.string, 'Signature')
            obj.set('unknown_1', data.read_uint32(), types.bytes, 'Unknown')
            obj.set('version_2', data.read_uint16(), types.int, 'Version 2')
            obj.set('header_size', data.read_uint32(),
                    types.int, 'Header size')
            
            obj.set('codec_flavor', data.read_uint16(),
                    types.int, 'Codec flavor')
            
            obj.set('codec_frame_size', data.read_uint32(),
                    types.int, 'Codec frame size')
            
            obj.set('unknown_2', data.read(12), types.bytes, 'Unknown')
            obj.set('sub_packet', data.read_uint16(), types.int, 'Subpacket')
            obj.set('frame_size', data.read_uint16(), types.int, 'Frame size')
            obj.set('sub_packet_size', data.read_uint16(),
                    types.int, 'Subpacket size')
            
            obj.set('unknown_3', data.read_uint16(), types.bytes, 'Unknown')
        
            # Version 5 
            if obj.version == 5:
                obj.set('unknown_4', data.read(6), types.bytes, 'Unknown')
            
            # Version 4 and 5
            obj.set('sample_rate', data.read_uint16(),
                    types.int, 'Sample rate')
            
            obj.set('unknown_5', data.read_uint16(),
                    types.bytes, 'Unknown')
            
            obj.set('sample_size', data.read_uint16(),
                    types.int, 'Sample size')
            
            obj.set('num_channels', data.read_uint16(),
                    types.int, 'Number of channels')
            
            if obj.version == 4:
                # Interleaver id
                obj.set('interleaver_id_length', data.read_uint8(),
                        types.int, 'Interleaver id length')
                obj.set('interleaver_id', data.read(obj.interleaver_id_length),
                        types.string, 'Interleaver id')
                
                # FourCC string
                obj.set('fourcc_string_length', data.read_uint8(),
                        types.int, 'FourCC string length')
                
                obj.set('fourcc_string', data.read(obj.fourcc_string_length),
                        types.string, 'FourCC string')
            
            else: # Version 5
                obj.set('interleaver_id', data.read_dword(),
                        types.string, 'Interleaver id')
                obj.set('fourcc_string', data.read_dword(),
                        types.string, 'FourCC string')

            # Version 4 and 5
            obj.set('unknown_6', data.read(3), types.bytes, 'Unknown')
            
            if obj.version == 5:
                obj.set('unknown_7', data.read(1), types.bytes, 'Unknown')
            
            # Version 4 and 5
            obj.set('codec_extradata_length', data.read_uint32(),
                    types.int, 'Codec extra data length')
            
            obj.set('codec_extradata', data.read(obj.codec_extradata_length),
                    types.bytes, 'Codec extra data')

        return obj

                
    def _parse_contentdescription(self, data):
        """ Parse the  Content description header (CONT)"""
        return None


    
    
