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
    http://msdn2.microsoft.com/en-us/library/ms779636.aspx
    
    This is a really basic parser designed to get the required information fast

"""
# For testing
if __name__ == "__main__":
    import sys; sys.path.append('../../'); sys.path.append('..')

import datetime

# Project modules
import videoparser.plugins as plugins
import videoparser.streams as streams

# Define the structure of the movie atom
atom_structure = {
    'ftyp':     ('Description', "validate_file_format"),
    'moov':     ('Movie atom', {
        'mvhd':     ('Movie header atom', "parse_movie_header_atom"),
        'trak':     ('Track atom', {
            'tkhd':      ('Track header atom', "parse_track_header_atom"),
            'clip':      ('Track clipping atom', {
                'crgn':     ('Clipping region atom', None),
            }),
            'matt':      ('Track matte atom', {
                'kmat':     ('Compressed matte atomm', None),
            }),
            'edts':      ('Edit atom', {
                'elst':     ('Edit list atom', None),
            }),
            'tref':      ('DescriptionHere', {
                'tmcd':       ('DescriptionHere', None)
            }),
            'mdia':      ('Media atom', {
                'mdhd':       ('Media header atom', None),
                'hdlr':       ('Media handler reference atom',
                                "parse_handler_reference_atom"),
                'minf':       ('Video media information atom', {
                    'smhd':    ('DescriptionHere', None),
                    'gmhd':    ('DescriptionHere', None),
                    'vmhd':        ('Video media information header atom',
                                    None),
                    'hdlr':        ('Data handler reference atom', None),
                    'dinf':        ('Data information atom', {
                        'dref':         ('Data reference atom', None)
                    }),
                    'stbl':        ('Sample table atom', {
                        'stsd':         ('Sample description atom',
                                         "parse_sample_descr_atom"),
                        'stts':         ('Time-to-sample atom',
                                         "parse_time_to_sample_atom"),
                        'stsc':         ('Sample-to-chunk atom', None),
                        'stsz':         ('Sample size atom', None),
                        'stco':         ('Chunk offset atom', None),
                    }),
                }),
            }),
            'udta':    ('DescriptionHere', None),
            'meta':    ('DescriptionHere', {
                'hdlr':    ('DescriptionHere', None),
                'keys':    ('DescriptionHere', None),
                'ilst':    ('DescriptionHere', None),
            }),
        }),
        'udta':    ('User data atom', None),
        'meta':    ('Metadata atom (Guess?)', {
            'hdlr':    ('Undocumented (HDLR)', None),
            'keys':    ('Undocumented (KEYS)', None),
            'ilst':    ('Undocumented (ILST)', None),
        }),
        'cmov':     ('Color table atom', None),
        'cmov':     ('Compressed movie atom', None),
        'rmra':     ('Reference movie atom', None),
    }),
    'free':     ('Description', None),
    'wide':     ('Description', None),
    'mdat':     ('Description', None),
}
    



class Parser(plugins.BaseParser):
    _endianess = streams.endian.big
    _file_types = ['mov', 'mp4']
    
    def __init__(self):
        plugins.BaseParser.__init__(self)
        self._tkhd_subtype = None
        
    def parse(self, filename, video):
        stream = streams.factory.create_filestream(filename,
                                                   endianess=self._endianess)

        # Make sure that we are dealing with a quicktime file format
        if stream.read(12) != '\x00\x00\x00 ftypqt  ':
            #print "Warning: This file does not start with the quicktime sig.."
            stream.seek(4)
            if stream.read(4) != 'moov':
                return False
            
        stream.seek(0)
        
        # Build a tree with all information extracted
        dest_tree = {}
        try:
            self.parse_atom(stream, atom_tree=atom_structure,
                            dest_tree=dest_tree)
        except AssertionError:
            raise
            return False
        
        # Extract required information from the tree and place it in the
        # videofile object
        self.extract_information(dest_tree, video)
        
        video.set_container("QuickTime")
        return True
    
    def parse_ftyp(self, data):
        print repr(data)
        
    def parse_atom(self, data, atom_tree=None, dest_tree=None):

        while data.bytes_left():
            atom_data = None
            atom_size = data.read_uint32()
            atom_type = data.read(4)

            atom_tree_item = atom_tree.get(atom_type)
            if not atom_tree_item:
                continue
            
            description, item_arg = atom_tree_item

            # Check if the atom is a container or contains data
            childs = None
            handler = None
            if type(item_arg) == dict:
                childs = item_arg
            else:
                handler = item_arg
            
            # Prepare the destination tree for new items
            if atom_type not in dest_tree:
                dest_tree[atom_type] = [{}]
                idx = 0
            else:
                dest_tree[atom_type].append({})
                idx = len(dest_tree[atom_type]) - 1
            
            # Recurse
            if childs:
                atom_data = data.read_subsegment(atom_size - 8)

                self.parse_atom(atom_data, atom_tree=atom_tree_item[1],
                                dest_tree=dest_tree[atom_type][idx])
            
            # Parse the data in the atom with the specified handler method
            elif handler:
                atom_data = data.read_subsegment(atom_size - 8)
                method = self.__class__.__getattribute__(self, handler)
                dest_tree[atom_type] = method(atom_data)
            
            # Don't read the data, since we are not processing it
            else:
                atom_data = data.seek(data.tell() + atom_size - 8)
            
        
    def extract_information(self, tree, video):
        
        duration = tree['moov'][0]['mvhd'].duration
        timescale = tree['moov'][0]['mvhd'].timescale
        
        for trak in tree['moov'][0]['trak']:
            # Shortcut to atoms
            mdia_atom = trak['mdia'][0]
            sample_atom = mdia_atom['minf'][0]['stbl'][0]
            sample_table = sample_atom['stsd'].sample_table[0]
            
            track_type = mdia_atom['hdlr'].subtype
            
            if track_type == 'vide':
                stream = video.new_video_stream()
                stream.set_width(sample_table['width'])
                stream.set_height(sample_table['height'])
                stream.set_codec(sample_table['format'])
                
                # Calculate the framerate
                stream_duration = 0
                frames = 0
                for s_count, s_duration in sample_atom['stts'].sample_table:
                    stream_duration += (s_count * s_duration)
                    frames += s_count
                    
                stream.set_framerate(timescale / (stream_duration /
                                                  float(frames)))
                stream.set_duration(seconds=stream_duration / float(timescale))
                
                #print trak['tkhd'].duration, duration, timescale
            elif track_type == 'soun':
                stream = video.new_audio_stream()
                stream.set_codec(sample_table['format'])
                stream.set_channels(sample_table['channels'])
                stream.set_sample_rate(sample_table['sample_rate'])
                stream.set_bit_per_sample(sample_table['bits'])


    def validate_file_format(self, data):
        major_brand = data.read(4)
        minor_version = data.read(4)

        if major_brand != 'qt  ':
            raise AssertionError("Invalid parser for this file " + \
                                 "(major brand = %r)" % major_brand)
        
        while data.bytes_left():
            compat_brand = data.read(4)
            if compat_brand == 'qt  ':
                return
        
        raise AssertionError("Invalid parser for this file")
    
    

    def parse_movie_header_atom(self, data):
        obj = self.MovieHeaderAtom()
        obj.version = data.read_uint8()
        obj.flags = data.read(3)
        obj.creation_time = data.read_timestamp_mac()
        obj.modification_time = data.read_timestamp_mac()
        obj.timescale = data.read_uint32()
        obj.duration = data.read_uint32()
        obj.preferred_rate = data.read_uint32()
        obj.preferred_volume = data.read_uint16()
        obj.reserved_1 = data.read(10)
        obj.matrix = data.read(36)
        obj.preview_time = data.read_uint32()
        obj.preview_duration = data.read_uint32()
        obj.poster_time = data.read_uint32()
        obj.selection_time = data.read_uint32()
        obj.selection_duration = data.read_uint32()
        obj.current_time = data.read_uint32()
        obj.next_track_id = data.read_uint32()
        return obj

    def parse_track_header_atom(self, data):
        obj = self.TrackHeaderAtom()
        obj.version = data.read_uint8()
        obj.flags = data.read(3)
        obj.creation_time = data.read_timestamp_mac()
        obj.modification_time = data.read_timestamp_mac()
        obj.track_id = data.read_uint32()
        obj.reserved_1 = data.read(4)
        obj.duration = data.read_uint32()
        obj.reserved_2 = data.read(8)
        obj.layer = data.read_uint16()
        obj.alt_group = data.read_uint16()
        obj.volume = data.read_uint16()
        obj.reserved_3 = data.read(2)
        obj.matrix = data.read(36)
        obj.width = data.read_qtfloat_32()
        obj.height = data.read_qtfloat_32()
        return obj
        
    def parse_handler_reference_atom(self, data):
        obj = self.HandlerReferenceAtom()
        obj.version = data.read_uint8()
        obj.flags = data.read(3)
        obj.type = data.read(4)
        obj.subtype = data.read(4)
        obj.manufacturer = data.read_uint32()
        obj.cflags = data.read_uint32()
        obj.cflags_mask = data.read_uint32()
        obj.name = data.read(data._filesize - data.tell())
        
        # FIXME: This is a louse hack, but we need to know the subtype to parse
        # the stsd atom correctly (subtype specifies if this is a sound or
        # video track or something else (tmcd)
        self._tkhd_subtype = obj.subtype
        return obj
        

    def parse_time_to_sample_atom(self, data):
        obj = self.TimeToSampleAtom()
        obj.version = data.read_uint8()
        obj.flags = data.read(3)
        obj.num_entries = data.read_uint32()
        obj.sample_table = []
        
        for i in range(0, obj.num_entries):
            obj.sample_table.append((data.read_uint32(), data.read_uint32()))

        return obj
    
    def parse_sample_descr_atom(self, data):
        obj = self.SampleDescrAtom()
        obj.version = data.read_uint8()
        obj.flags = data.read(3)
        obj.num_entries = data.read_uint32()
        
        obj.sample_table = []
        
        assert(self._tkhd_subtype is not None)
        for i in range(0, obj.num_entries):
            size = data.read_uint32()
            
            table_entry = {}

            table_entry['size'] = size
            table_entry['format'] = data.read(4)
            table_entry['reserved'] = data.read(6)
            table_entry['data_ref_index'] = data.read_uint16()
            table_entry['version'] = data.read_uint16()
            table_entry['revision'] = data.read_uint16()
            
            if self._tkhd_subtype == 'vide':
                table_entry['vendor'] =  repr(data.read_dword())
                table_entry['temporal_quality'] =  data.read_int32()
                table_entry['spatial_quality'] =  data.read_int32()
                table_entry['width'] =  data.read_int16()
                table_entry['height'] =  data.read_int16()
                table_entry['horizontal_res'] =  data.read_qtfloat_32()
                table_entry['vertical_res'] =  data.read_qtfloat_32()
                table_entry['data_size'] =  data.read_int32()
                table_entry['frame_count'] =  data.read_int16()
                table_entry['compressor'] =  repr(data.read_dword())
                table_entry['depth'] =  data.read_uint16()
                table_entry['color_table_id'] =  data.read_int16()
                
            if self._tkhd_subtype == 'soun':
                table_entry['vendor'] =  data.read_uint32()
                table_entry['channels'] =  data.read_uint16()
                table_entry['bits'] =  data.read_uint16()
                table_entry['compression_id'] =  data.read_int16()
                table_entry['packet_size'] =  data.read_uint16()
                table_entry['sample_rate'] =  data.read_qt_ufloat32()
            
            obj.sample_table.append(table_entry)
        
        return obj


    class TimeToSampleAtom(object):
        pass
        # TODO implement repr
        
        
    class SampleDescrAtom(object):
        pass
        # TODO implement repr
    
    class MovieHeaderAtom(object):
        def __repr__(self):
            buffer = "MovieHeaderAtom:\n"
            buffer += " %-30s: %s\n" % ("Version", self.version)
            buffer += " %-30s: %r\n" % ("Flags", self.flags)
            buffer += " %-30s: %s\n" % ("Creation time", self.creation_time)
            buffer += " %-30s: %s\n" % ("Modification time", self.modification_time)
            buffer += " %-30s: %s\n" % ("Time scale", self.timescale)
            buffer += " %-30s: %s\n" % ("Duration", self.duration)
            buffer += " %-30s: %s\n" % ("Preferred rate", self.preferred_rate)
            buffer += " %-30s: %s\n" % ("Preferred volume", self.preferred_volume)
            buffer += " %-30s: %r\n" % ("Reserved", self.reserved_1)
            buffer += " %-30s: %r\n" % ("Matrix structure ", self.matrix)
            buffer += " %-30s: %s\n" % ("Preview time", self.preview_time)
            buffer += " %-30s: %s\n" % ("Preview duration", self.preview_duration)
            buffer += " %-30s: %s\n" % ("Poster time", self.poster_time)
            buffer += " %-30s: %s\n" % ("Selection time", self.selection_time)
            buffer += " %-30s: %s\n" % ("Selection duration", self.selection_duration)
            buffer += " %-30s: %s\n" % ("Current time", self.current_time)
            buffer += " %-30s: %s\n" % ("Next track ID", self.next_track_id)
            return buffer

        
    class TrackHeaderAtom(object):
        def __repr__(self):
            buffer = "TrackHeaderAtom:\n"
            buffer += " %-30s: %s\n" % ("Version", self.version)
            buffer += " %-30s: %r\n" % ("Flags", self.flags)
            buffer += " %-30s: %s\n" % ("Creation time", self.creation_time)
            buffer += " %-30s: %s\n" % ("Modification time", self.modification_time)
            buffer += " %-30s: %s\n" % ("Track ID", self.track_id)
            buffer += " %-30s: %r\n" % ("Reserved", self.reserved_1)
            buffer += " %-30s: %s\n" % ("Duration", self.duration)
            buffer += " %-30s: %r\n" % ("Reserved", self.reserved_2)
            buffer += " %-30s: %s\n" % ("Layer", self.layer)
            buffer += " %-30s: %s\n" % ("Alternate group", self.alt_group)
            buffer += " %-30s: %s\n" % ("Volume", self.volume)
            buffer += " %-30s: %r\n" % ("Reserved", self.reserved_3)
            buffer += " %-30s: %r\n" % ("Matrix structure ", self.matrix)
            buffer += " %-30s: %s\n" % ("Track width", self.width)
            buffer += " %-30s: %s\n" % ("Track height", self.height)
            return buffer    
    

    class HandlerReferenceAtom(object):
        def __repr__(self):
            buffer = "HandlerReferenceAtom:\n"
            buffer += " %-30s: %s\n" % ("Version", self.version)
            buffer += " %-30s: %r\n" % ("Flags", self.flags)
            buffer += " %-30s: %s\n" % ("Component type", self.type)
            buffer += " %-30s: %s\n" % ("Component subtype", self.subtype)
            buffer += " %-30s: %s\n" % ("Component manufacturer", self.manufacturer)
            buffer += " %-30s: %r\n" % ("Component flags", self.cflags)
            buffer += " %-30s: %r\n" % ("Component flags mask", self.cflags_mask)
            buffer += " %-30s: %s\n" % ("Component name", self.name)
            return buffer


        
        
if __name__ == "__main__":
    import sys
    import videofile
    
    import plugins
    video = videofile.VideoFile()
    p = Parser()
    if not p.parse(sys.argv[1], video):
        print "This is not a quicktime file.."
        sys.exit(1)
        
    print video
    


