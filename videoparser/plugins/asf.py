"""ASF Parser Plugin."""
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

# Built-in modules
import datetime


__all__ = ['Parser']

# Project modules
import videoparser.plugins as plugins
import videoparser.streams as streams


# Only implement required information to retrieve video and audio information
guid_list = {
    'D2D0A440-E307-11D2-97F0-00A0C95EA850':
                                    'ASF_Extended_Content_Description_Object',
    '75B22630-668E-11CF-A6D9-00AA0062CE6C': 'ASF_Header_Object',
    '75B22633-668E-11CF-A6D9-00AA0062CE6C': 'ASF_Content_Description_Object',
    '8CABDCA1-A947-11CF-8EE4-00C00C205365': 'ASF_File_Properties_Object',
    '5FBF03B5-A92E-11CF-8EE3-00C00C205365': 'ASF_Header_Extension_Object',
    '86D15240-311D-11D0-A3A4-00A0C90348F6': 'ASF_Codec_List_Object',
    'B7DC0791-A9B7-11CF-8EE6-00C00C205365': 'ASF_Stream_Properties_Object',
    '7BF875CE-468D-11D1-8D82-006097C9A2B2':
                                     'ASF_Stream_Bitrate_Properties_Object',
    'F8699E40-5B4D-11CF-A8FD-00805F5C442B': 'ASF_Audio_Media',
    'BC19EFC0-5B4D-11CF-A8FD-00805F5C442B': 'ASF_Video_Media',
    'BFC3CD50-618F-11CF-8BB2-00AA00B4E220': 'ASF_Audio_Spread',
    '20FB5700-5B55-11CF-A8FD-00805F5C442B': 'ASF_No_Error_Correction',
    '7C4346A9-EFE0-4BFC-B229-393EDE415C85': 'ASF_Language_List_Object',
    'ABD3D211-A9BA-11cf-8EE6-00C00C205365': 'ASF_Reserved_1',
    'C5F8CBEA-5BAF-4877-8467-AA8C44FA4CCA': 'ASF_Metadata_Object',
    '14E6A5CB-C672-4332-8399-A96952065B5A':
                                    'ASF_Extended_Stream_Properties_Object',
    'D6E229DF-35DA-11D1-9034-00A0C90349BE': 'ASF_Index_Parameters_Object',
    'D4FED15B-88D3-454F-81F0-ED5C45999E24': 'ASF_Stream_Prioritization_Object',
    '1806D474-CADF-4509-A4BA-9AABCB96AAE8': 'ASF_Padding_Object',
}




class Parser(plugins.BaseParser):
    _endianess = streams.endian.little
    _file_types = ['wmv']
    
    def __init__(self):
        plugins.BaseParser.__init__(self)
        
    def parse(self, filename, video):
        
        stream = streams.factory.create_filestream(filename,
                                                   endianess=self._endianess)
            
        object_id   = stream.read_guid()
        
        if guid_list.get(object_id) != 'ASF_Header_Object':
            return False

        try:                    
            header = self.parse_header(stream)
        except AssertionError:
            return False
    
        self.extract_information(header, video)
        return True
    
    
    def extract_information(self, header, video):

        #print header
        #print
        #print
        
        framerates = {}
        video.set_container('ASF')

        # Loop over all objects in the header, first search for the
        # StreamProperties
        for object in header.objects:
            if isinstance(object, self.StreamProperties):
                stream = video.get_stream(object.index)
                type_data = object.type_data
                
                if object.type == 'ASF_Audio_Media':
                    if not stream:
                        stream = video.new_audio_stream(object.index)
                    stream.set_channels(type_data.channels)
                    stream.set_sample_rate(type_data.sample_rate)
                    stream.set_codec(type_data.codec_ids.get(
                        type_data.codec_id, type_data.codec_id))
                    stream.set_bit_per_sample(type_data.bits_per_sample)

                if object.type == 'ASF_Video_Media':
                    if not stream:
                        stream = video.new_video_stream(object.index)
                    stream.set_width(type_data.width)
                    stream.set_height(type_data.height)
                    stream.set_codec(type_data.format_data.compression_id)
        
                    
        for object in header.objects:
            if isinstance(object, self.FileProperties):
                for stream in video.video_streams:
                    stream.set_duration(seconds=object.play_duration.seconds,
                                        microseconds= \
                                            object.play_duration.microseconds)
                
            # Extract additional information from the HeaderExtension
            if isinstance(object, self.HeaderExtension):
                for sub_object in object.extension_data:
                    if isinstance(sub_object, self.ExtendedStreamProperties):
                        
                        # Framerate (required for video)
                        stream = video.get_stream(sub_object.stream_number)
                        if stream.type == 'Video':
                            stream.set_framerate(1 / (
                                sub_object.avg_time_per_frame / 10000000.0))
                        
    
        return video
    
    
    def parse_header(self, stream):
        
        # Read the header information
        header = self.Header()
        header.size = stream.read_uint64()
        header.num_objects = stream.read_uint32()
        header.reserved_1  = stream.read_uint8()
        header.reserved_2  = stream.read_uint8()
        
        header.objects = []
        
        if header.reserved_2 != 0x02:
            raise AssertionError('Reserved2 in Header Object should be 0x02')
        
        # Loop through all objects contained in the header
        for i in range(0, header.num_objects):
            guid = stream.read_guid()
            size = stream.read_uint64()
            
            obj = None
            
            try:
                object_type = guid_list[guid]
            except:
                # Unrecognized object, skip over it
                raise AssertionError("Unregognized object: %s" % guid)
                stream.skip(size - 24)
                continue
            
            data = stream.read_subsegment(size - 24)

            if object_type == 'ASF_Content_Description_Object':
                obj = 'ASF_Content_Description_Object (TODO)'
            
            elif object_type == 'ASF_Extended_Content_Description_Object':
                obj = 'ASF_Extended_Content_Description_Object (TODO)'
            
            elif object_type == 'ASF_File_Properties_Object':
                obj = self.parse_file_properties(data)
                
            elif object_type == 'ASF_Header_Extension_Object':
                obj = self.parse_header_extension(data)
                
            elif object_type == 'ASF_Codec_List_Object':
                obj = self.parse_codec_list(data)
                
            elif object_type == 'ASF_Stream_Properties_Object':
                obj = self.parse_stream_properties(data)
                
            elif object_type == 'ASF_Stream_Bitrate_Properties_Object':
                obj = self.parse_stream_bitrate_properties(data)
            
            else:
                print "Warning: unhandled object: %s" % object_type
                
            header.objects.append(obj)

            data.close()
            #print guid_list[guid], size

        return header
        
    # mandatory, one only
    def parse_file_properties(self, data):
        fileprop = self.FileProperties()
        fileprop.id = data.read_guid()
        fileprop.size = data.read_uint64()
        fileprop.create_date = data.read_timestamp_win()
        fileprop.packet_count = data.read_uint64()
        fileprop.play_duration = datetime.timedelta(
                                    microseconds=data.read_uint64()/10)
        fileprop.send_duration = datetime.timedelta(
                                    microseconds=data.read_uint64()/10)
        fileprop.preroll = data.read_uint64()

        # Flags
        flags = data.read_uint32()
        fileprop.broadcast_flag = flags & 0x01
        fileprop.seekable_flag = (flags >> 1) & 0x01
        fileprop.reserved = flags >> 2
        
        fileprop.min_packet_size = data.read_uint32()
        fileprop.max_packet_size = data.read_uint32()
        fileprop.max_bitrate = data.read_uint32()
        
        return fileprop
    
    # mandatory, one only
    def parse_stream_properties(self, data):
        stream = self.StreamProperties()
        
        stream.type = guid_list[data.read_guid()]
        stream.ecc_type    = guid_list[data.read_guid()]
        stream.time_offset = data.read_uint64()
        stream.type_length = data.read_uint32()
        stream.ecc_length  = data.read_uint32()
        flags              = data.read(2)
        stream.index       = ord(flags[0]) & 0x7f

        stream.reserved    = data.read(4)
        
        type_data   = data.read_subsegment(stream.type_length)
        
        if stream.type == 'ASF_Audio_Media':
            obj = type_data.read_waveformatex()

        elif stream.type == 'ASF_Video_Media':
            obj = self.VideoMedia()
            
            obj.width = type_data.read_uint32()
            obj.height = type_data.read_uint32()
            obj.reserved_flags = type_data.read_byte()
            obj.format_data_size = type_data.read_uint16()
            obj.format_data = type_data.read_bitmapinfoheader()

        else:
            obj = None

        stream.type_data = obj
        stream.ecc_data  = repr(data.read(stream.ecc_length))

        return stream
        
    # mandatory, one only
    def parse_header_extension(self, data):
        header = self.HeaderExtension()
        header.reserved_1 = data.read_guid()   # should be ASF_Reserved_1
        header.reserved_2 = data.read_uint16() # should be 6
        header.size       = data.read_uint32()
        header.extension_data = []
        
        # Check reserved_1
        bytes = header.size
        while bytes > 0:
            object_id = data.read_guid()
            object_size = data.read_uint64()
            bytes -= object_size
            
            if object_size == 0:
                continue
        
            sub_data = data.read_subsegment(object_size - 24)
            
            try:
                object_type = guid_list[object_id]
            except KeyError:
                # Skip unknown guid's, since authors are allowed to create
                # there own
                #
                #print "WARNING: object_id '%s' not found in guid_list" % \
                # object_id
                #header.extension_data.append(object_id)
                continue
                
            if object_type == 'ASF_Language_List_Object':
                obj = self.parse_language_list(sub_data)

            elif object_type == 'ASF_Metadata_Object':
                obj = self.parse_metadata(sub_data)

            elif object_type == 'ASF_Extended_Stream_Properties_Object':
                obj = self.parse_extended_stream_properties(sub_data)
            
            elif object_type == 'ASF_Stream_Prioritization_Object':
                obj = self.parse_stream_prioritization(sub_data)
                
            elif object_type == 'ASF_Padding_Object':
                # Ignore the padding object, since it contains no information
                continue
            
            elif object_type == 'ASF_Index_Parameters_Object':
                obj = 'ASF_Index_Parameters_Object (TODO)'
            
            else:
                raise AssertionError("object_type '%s' not processed in " +
                                     "header_extension" % object_type)
            
            #if obj is None:
            #    raise AssertionError("obj is None: %s" % object_type)
            header.extension_data.append(obj)
        return header        
    
    def parse_language_list(self, data):
        obj = self.LanguageList()
        
        obj.num_records = data.read_uint16()
        obj.records = []
        
        for i in range(0, obj.num_records):
            language_id_length = data.read_uint8()
            language_id = data.read_wchars(language_id_length / 2)
            obj.records.append(language_id)
        
        return obj
        
        
    def parse_metadata(self, data):
        return None
    
    def parse_extended_stream_properties(self, data):
        obj = self.ExtendedStreamProperties()
        obj.start_time      = data.read_uint64()
        obj.end_time        = data.read_uint64()
        obj.data_bitrate    = data.read_uint32()
        obj.buffer_size     = data.read_uint32()
        obj.initial_buffer_fullness  = data.read_uint32()
        obj.alt_data_bitrate    = data.read_uint32()
        obj.alt_buffer_size     = data.read_uint32()
        obj.alt_initial_buffer_fullness = data.read_uint32()
        obj.max_object_size     = data.read_uint32()
        
        # Parse flags
        flags = data.read_uint32()
        obj.reliable_flag   = flags & 0x01
        obj.seekable_flag   = (flags >> 1) & 0x01
        obj.no_cleanpoints_flag = (flags >> 2) & 0x01
        obj.resend_cleanpoints_flag = (flags >> 3) & 0x01
        obj.reserved_flags      = flags >> 4
        
        obj.stream_number       = data.read_uint16()
        obj.stream_language_id  = data.read_uint16()
        obj.avg_time_per_frame  = data.read_uint64()
        obj.stream_name_length  = data.read_uint16()
        obj.payload_extension_length = data.read_uint16()
        obj.stream_names = None
        obj.payload_extensions = None
        obj.stream_properties_object = None
        
        return obj
        
    
    def parse_stream_prioritization(self, data):
        return None
    
    # Optional, one only
    def parse_codec_list(self, data):
        codeclist = self.CodecList()
        
        codeclist.reserved = data.read_guid()
        codeclist.num_codecs = data.read_uint32()
        codeclist.codec_entries = []
        
        for i in range(0, codeclist.num_codecs):
            entry = self.CodecEntry()
            entry.type = data.read_uint16()
            entry.name_length = data.read_uint16()
            entry.name = data.read_wchars(entry.name_length,
                                          null_terminated=True)
            entry.description_length = data.read_uint16()
            entry.description = data.read_wchars(entry.description_length,
                                                 null_terminated=True)
            entry.information_length = data.read_uint16()
            entry.information = repr(data.read(entry.information_length))
            codeclist.codec_entries.append(entry)
        return codeclist
        
    
    # Optional but recommended, one only
    def parse_stream_bitrate_properties(self, data):
        bitratelist = self.StreamBitrateProperties()
        
        bitratelist.num_records = data.read_uint16()
        bitratelist.records = []
        for i in range(0, bitratelist.num_records):
            entry = self.StreamBitrateRecord()
            flags = data.read(2)
            entry.stream_index = ord(flags[0]) & 0x7f
            entry.reserved = chr(ord(flags[0]) & 0x80) + flags[1]
            
            
            entry.avg_bitrate = data.read_uint32()
        
            bitratelist.records.append(entry)
        return bitratelist 


    # 
    # Objects to represent internal structure of the ASF File for debuging
    #
    class Structure(object):
        def repr_childs(self, obj):
            buffer = ""
            for entry in obj:
                buffer += "\n".join(["   %s" % line for line
                                     in repr(entry).split('\n')])
                buffer += "\n"
            return buffer
    
    class Header(Structure):
        __slots__ = ['size', 'num_objects', 'reserved_1', 'reserved_2',
                     'objects']
        
        def __repr__(self):
            buffer  = "ASF_Header_Object Structure: \n"
            buffer += " %-30s: %s\n" % ('Object Size', self.size)
            buffer += " %-30s: %s\n" % ('Number of Header Objects',
                                        self.num_objects)
            buffer += " %-30s: %s\n" % ('Reserved1', repr(self.reserved_1))
            buffer += " %-30s: %s\n" % ('Reserved2', repr(self.reserved_2))
            buffer += self.repr_childs(self.objects)
            
            return buffer
            
        
    class VideoMedia(Structure):
        __slots__ = ['width', 'height', 'reserved_flags', 'format_data_size',
                     'format_data']
            
        def __repr__(self):
            buffer  = "ASF_Video_Media Structure: \n"
            buffer += " %-30s: %s\n" % ('Encoded Image Width', self.width)
            buffer += " %-30s: %s\n" % ('Encoded Image Height', self.height)
            buffer += " %-30s: %s\n" % ('Reserved Flags',
                                        repr(self.reserved_flags))
            buffer += " %-30s: %s\n" % ('Format Data Size',
                                        self.format_data_size)
            buffer += " %-30s\n" % ('Format Data')
            buffer += self.repr_childs([self.format_data])
            
            return buffer
    
    class LanguageList(Structure):
        __slots__ = ['num_records', 'records']
        
        def __repr__(self):
            buffer  = "ASF_Language_List_Object: \n"
            buffer += " %-30s: %s\n" % ('Language ID Records Count',
                                        self.num_records)
            buffer += self.repr_childs([self.records])
            return buffer
    
    class FileProperties(Structure):
        __slots__ = ['id', 'size', 'create_data', 'packet_count',
                     'play_duration', 'send_duration', 'preroll',
                     'broadcast_flag', 'seekable_flag', 'reserved',
                     'min_packet_size', 'max_packet_size', 'max_bitrate']
                     
        def __repr__(self):
            buffer  = "FileProperties Structure: \n"
            buffer += " %-30s: %s\n" % ('File ID', self.id)
            buffer += " %-30s: %s\n" % ('File Size', self.size)
            buffer += " %-30s: %s\n" % ('Creation Date', self.create_date)
            buffer += " %-30s: %s\n" % ('Data Packets Count',
                                        self.packet_count)
            buffer += " %-30s: %s\n" % ('Play Duration', self.play_duration)
            buffer += " %-30s: %s\n" % ('Send Duration', self.send_duration)
            buffer += " %-30s: %s\n" % ('Preroll', repr(self.preroll))
            buffer += " %-30s: %s\n" % ('Broadcast Flag', self.broadcast_flag)
            buffer += " %-30s: %s\n" % ('Seekable Flag', self.seekable_flag)
            buffer += " %-30s: %s\n" % ('Reserved', repr(self.reserved))
            buffer += " %-30s: %s\n" % ('Minimum Data Packet Size',
                                        self.min_packet_size)
            buffer += " %-30s: %s\n" % ('Maximum Data Packet Size',
                                        self.max_packet_size)
            buffer += " %-30s: %s\n" % ('Maximum Bitrate',
                                        self.max_bitrate)
            return buffer
    
    
    class HeaderExtension(Structure):
        def __repr__(self):
            buffer  = "HeaderExtension Structure: \n"
            buffer += " %-30s: %s\n" % ('Reserved_1', self.reserved_1)
            buffer += " %-30s: %s\n" % ('Reserved_2', self.reserved_2)
            buffer += " %-30s: %s\n" % ('Header Extension Data Size',
                                        self.size)
            buffer += " %-30s\n" % ('Header Extension Data')
            buffer += self.repr_childs(self.extension_data)
            return buffer
        
        
    class StreamProperties(Structure):
        __slots__ = ['type', 'ecc_type', 'time_offset', 'type_length',
                     'ecc_length', 'index', 'reserved', 'type_data',
                     'ecc_data']
        
        def __repr__(self):
            buffer  = "StreamProperties Structure: \n"
            buffer += " %-30s: %s\n" % ('Stream Type', self.type)
            buffer += " %-30s: %s\n" % ('Error Correction Type', self.ecc_type)
            buffer += " %-30s: %s\n" % ('Time Offset', self.time_offset)
            buffer += " %-30s: %s\n" % ('Type-Specific Data Length',
                                        self.type_length)
            buffer += " %-30s: %s\n" % ('Error Correction Data Length',
                                        self.ecc_length)
            buffer += " %-30s: %s\n" % ('Stream Index', self.index)
            buffer += " %-30s: %s\n" % ('Reserved', repr(self.reserved))
            buffer += " %-30s\n" % ('Type-Specific Data')
            buffer += self.repr_childs([self.type_data])
            buffer += " %-30s: %s\n" % ('Error Correction Data', self.ecc_data)
            
            
            return buffer


    class StreamBitrateRecord(Structure):
        __slots__ = ['stream_index', 'reserved', 'avg_bitrate']
        
        def __repr__(self):
            buffer  = "StreamBitrateRecord Structure: \n"
            buffer += " %-30s: %s\n" % ('Stream number', self.stream_index)
            buffer += " %-30s: %r\n" % ('Reserved', self.reserved)
            buffer += " %-30s: %s\n" % ('Average Bitrate', self.avg_bitrate)
            return buffer
    


    class StreamBitrateProperties(Structure):
        __slots__ = ['num_records', 'records']
        
        def __repr__(self):
            buffer  = "StreamBitrateProperties Structure: \n"
            buffer += " %-30s: %s\n" % ('Bitrate Entries Count',
                                        self.num_records)
            buffer += " %-30s\n" % ('Codec Entries')
            buffer += self.repr_childs(self.records)
            return buffer      

        
    class CodecList(Structure):
        __slots__ = ['reserved', 'num_codecs', 'codec_entries']
        
        def __repr__(self):
            buffer  = "CodecList Structure: \n"
            buffer += " %-30s: %s\n" % ('Reserved', self.reserved)
            buffer += " %-30s: %s\n" % ('Codec Entries Count', self.num_codecs)
            buffer += " %-30s\n" % ('Codec Entries')
            buffer += self.repr_childs(self.codec_entries)
            return buffer
        
        
    class CodecEntry(Structure):
        __slots__ = ['type', 'name_length', 'name', 'description_length',
                     'description', 'information_length', 'information']
        
        def __repr__(self):
            buffer  = "CodecEntry Structure: \n"
            buffer += " %-30s: %s\n" % ('Type', self.type)
            buffer += " %-30s: %s\n" % ('Codec Name Length', self.name_length)
            buffer += " %-30s: %s\n" % ('Codecx Name', repr(self.name))
            buffer += " %-30s: %s\n" % ('Codec Description Length',
                                        self.description_length)
            buffer += " %-30s: %s\n" % ('Codec Description',
                                        repr(self.description))
            buffer += " %-30s: %s\n" % ('Codec Information Length',
                                        self.information_length)
            buffer += " %-30s: %s\n" % ('Codec Information', self.information)
            
            return buffer


    class ExtendedStreamProperties(Structure):
        __slots__ = ['start_time', 'end_time', 'data_bitrate', 'buffer_size',
                     'initial_buffer_fullness', 'alt_data_bitrate',
                     'alt_buffer_size', 'alt_initial_buffer_fullness',
                     'max_object_size', 'reliable_flag', 'seekable_flag',
                     'no_cleanpoints_flag', 'resend_cleanpoints_flag',
                     'reserved_flags', 'stream_number', 'stream_language_id',
                     'avg_time_per_frame', 'stream_name_length',
                     'payload_extension_length', 'stream_names',
                     'payload_extensions', 'stream_properties_object']
        
        def __repr__(self):
            buffer = "ExtendedStreamProperties Structure: \n"
            buffer += " %-30s: %s\n" % ('Start Time', self.start_time)
            buffer += " %-30s: %s\n" % ('End Time', self.end_time)
            buffer += " %-30s: %s\n" % ('Data Bitrate', self.data_bitrate)
            buffer += " %-30s: %s\n" % ('Buffer Size', self.buffer_size)
            buffer += " %-30s: %s\n" % ('Initial Buffer Fullness',
                                        self.initial_buffer_fullness)
            buffer += " %-30s: %s\n" % ('Alternate Data Bitrate',
                                        self.alt_data_bitrate)
            buffer += " %-30s: %s\n" % ('Alternate Buffer Size',
                                        self.alt_buffer_size)
            buffer += " %-30s: %s\n" % ('Alternate Initial Buffer Fullness',
                                        self.alt_initial_buffer_fullness)
            buffer += " %-30s: %s\n" % ('Maximum Object Size',
                                        self.max_object_size)
            buffer += " %-30s: %s\n" % ('Reliable Flag', self.reliable_flag)
            buffer += " %-30s: %s\n" % ('Seekable Flag',
                                        self.seekable_flag)
            buffer += " %-30s: %s\n" % ('No Cleanpoints Flag',
                                        self.no_cleanpoints_flag)
            buffer += " %-30s: %s\n" % ('Resend Live Cleanpoints Flag',
                                        self.resend_cleanpoints_flag)
            buffer += " %-30s: %s\n" % ('Reserved Flags', self.reserved_flags)
            buffer += " %-30s: %s\n" % ('Stream Number', self.stream_number)
            buffer += " %-30s: %s\n" % ('Stream Language ID Index',
                                        self.stream_language_id)
            buffer += " %-30s: %s\n" % ('Average Time Per Frame',
                                        self.avg_time_per_frame)
            buffer += " %-30s: %s\n" % ('Stream Name Count',
                                        self.stream_name_length)
            buffer += " %-30s: %s\n" % ('Payload Extension System Count',
                                        self.payload_extension_length)
            buffer += " %-30s: %s\n" % ('Stream Names', self.stream_names)
            buffer += " %-30s: %s\n" % ('Payload Extension Systems',
                                        self.payload_extensions)
            buffer += " %-30s: %s\n" % ('Stream Properties Object',
                                        self.stream_properties_object)
    
            return buffer



