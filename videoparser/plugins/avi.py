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

__all__ = ['Parser']


# For testing
if __name__ == "__main__":
    import sys
    sys.path.append('../../')
    sys.path.append('..')

# Project modules
import videoparser.plugins as plugins
import videoparser.streams as streams


class Parser(plugins.BaseParser):
    """ Parser for AVI RIFF Containers """
    _endianess = streams.endian.little
    _file_types = ['avi']
    
    def __init__(self):
        plugins.BaseParser.__init__(self)
        
        self._parse_level = 0
        self._last_stream_header = None

    def parse(self, filename, video):
        stream = streams.factory.create_filestream(filename,
                                                   endianess=self._endianess)

        # Read fourcc
        if stream.read(4) != 'RIFF':
            return False

        # Unused at this point
        filesize = stream.read_uint32()
        filetype = stream.read(4)
        
        # Parse the first block (which is a header)
        
        header = self._parse_block(stream)
        self._extract_information(header, video)
        return True
    
    
    def _extract_information(self, header, video):
        
        video.set_container('AVI RIFF')
        for child in header.childs:
            if isinstance(child, self.AVIMainHeader):
                pass
            
            if isinstance(child, self.ListItem) and child.type == 'strl':
                
                # childs[0] should be the streamheader and childs[1] should
                # be the streamformat
                header = child.childs[0]
                format = child.childs[1]
                
                if header.type == 'vids':
                    stream = video.new_video_stream()
                    stream.set_framerate(header.rate / float(header.scale))
                    stream.set_width(format.image_width)
                    stream.set_height(format.image_height)
                    stream.set_codec(format.compression_id)
                    stream.set_duration(seconds=header.length /
                                        (header.rate / float(header.scale)))
                    
                elif header.type == 'auds':
                    stream = video.new_audio_stream()
                    stream.set_channels(format.channels)
                    stream.set_sample_rate(format.sample_rate)
                    stream.set_codec(format.codec_ids.get(format.codec_id,
                                                          'Unknown'))
        
    
    def _parse_block(self, stream):
        id = stream.read(4)
        if id == 'LIST':
            return self._parse_list(stream)
        else:
            return self._parse_chunk(stream, id)
            
    def _parse_list(self, stream):
        item = self.ListItem()
        item.size = stream.read_uint32()
        item.type = stream.read_dword()

        
        item.childs = []
        
        data = stream.read_subsegment(item.size-4 )
        while data.tell() < item.size - 4:
            sub_item = self._parse_block(data)
            item.childs.append(sub_item)

        
        return item

    def _parse_chunk(self, stream, chunk_id):
        
        chunk_size = stream.read_uint32()
        chunk_size += chunk_size % 2 # Align to dword
        
        if chunk_id in ['avih', 'strh', 'strf']:
            data = stream.read_subsegment(chunk_size)
            if chunk_id == 'avih':
                return self._parse_mainheader(data)
            
            elif chunk_id == 'strh':
                return self._parse_streamheader(data)
                
            elif chunk_id == 'strf':
                if self._last_stream_header.type == 'vids':
                    return data.read_bitmapinfoheader()

                elif self._last_stream_header.type == 'auds':
                    return data.read_waveformatex()

                else:
                    assert("invalid stream type")
        else:
            stream.seek(stream.tell() + chunk_size)
        
        return None

    def _parse_streamheader(self, data):
        header = self.AVIStreamHeader()
        header.type = data.read(4)
        header.handler = data.read(4)
        header.flags = data.read_uint32()
        header.priority = data.read_uint16()
        header.language = data.read_uint16()
        header.initial_frames = data.read_uint32()
        header.scale = data.read_uint32()
        header.rate  = data.read_uint32()
        header.start = data.read_uint32()
        header.length = data.read_uint32()
        header.suggested_buffer_size = data.read_uint32()
        header.quality = data.read_uint32()
        header.sample_size = data.read_uint32()
        header.frame_left = data.read_uint8()
        header.frame_top = data.read_uint8()
        header.frame_right = data.read_uint8()
        header.frame_bottom = data.read_uint8()
        
        self._last_stream_header = header
        return header
        
    
    def _parse_mainheader(self, data):
        header = self.AVIMainHeader()
        header.ms_per_frame         = data.read_uint32()
        header.max_bytes_per_frame  = data.read_uint32()
        header.padding_granularity  = data.read_uint32()
        header.flags                = data.read_uint32()
        header.total_frames         = data.read_uint32()
        header.initial_frames       = data.read_uint32()
        header.streams              = data.read_uint32()
        header.suggested_buffer_size    = data.read_uint32()
        header.width        = data.read_uint32()
        header.height       = data.read_uint32()
        header.reserved     = data.read_uint32()
        
        return header


    class ListItem(object):
        __slots__ = ['type', 'size', 'childs']
        def __repr__(self):
            buffer = "ListItem => type: %s size: %s\n" % (self.type, self.size)
            for entry in self.childs:
                buffer += "\n".join(["   %s" % line for line in
                                     repr(entry).split('\n')])
                buffer += "\n"

            buffer = buffer[:-1]            
            return buffer
    
    
    class AVIMainHeader(object):
        __slots__ = ['ms_per_frame', 'max_bytes_per_frame',
                     'padding_granularity', 'flags', 'total_frames',
                     'initial_frames', 'streams', 'suggested_buffer_size',
                     'width', 'height', 'reserved']
    
        def __repr__(self):
            buffer  = "AVIMAINHEADER structure:\n"
            buffer += " %-30s: %s\n" % ('Microseconds per frame',
                                        self.ms_per_frame)
            buffer += " %-30s: %s\n" % ('Max bytes per frame',
                                        self.max_bytes_per_frame)
            buffer += " %-30s: %s\n" % ('Padding Granularity',
                                        self.padding_granularity)
            buffer += " %-30s: %s\n" % ('Flags', self.flags)
            buffer += " %-30s: %s\n" % ('Total frames', self.total_frames)
            buffer += " %-30s: %s\n" % ('Initial frames', self.initial_frames)
            buffer += " %-30s: %s\n" % ('Streams', self.streams)
            buffer += " %-30s: %s\n" % ('Suggested Buffer Size',
                                        self.suggested_buffer_size)
            buffer += " %-30s: %s\n" % ('Width', self.width)
            buffer += " %-30s: %s\n" % ('Height', self.height)
            buffer += " %-30s: %s\n" % ('Reserved[4]', self.reserved)
            return buffer
    
    class AVIStreamHeader(object):
        __slots__ = ['type', 'handler', 'flags', 'priority', 'language',
                     'initial_frames', 'scale', 'rate', 'start', 'length',
                     'suggested_buffer_size', 'quality', 'sample_size',
                     'frame_left', 'frame_top', 'frame_right', 'frame_bottom']
        
        def __repr__(self):
            buffer  = "AVISTREAMHEADER structure:\n"
            buffer += " %-30s: %s\n" % ('Type', self.type)
            buffer += " %-30s: %s\n" % ('Handler', self.handler)
            buffer += " %-30s: %s\n" % ('Flags', self.flags)
            buffer += " %-30s: %s\n" % ('Priority', self.priority)
            buffer += " %-30s: %s\n" % ('Language', self.language)
            buffer += " %-30s: %s\n" % ('Initial Frames', self.initial_frames)
            buffer += " %-30s: %s\n" % ('Scale', self.scale)
            buffer += " %-30s: %s\n" % ('Rate', self.rate )
            buffer += " %-30s: %s\n" % ('Start', self.start)
            buffer += " %-30s: %s\n" % ('Length', self.length)
            buffer += " %-30s: %s\n" % ('Suggested buffer size',
                                        self.suggested_buffer_size)
            buffer += " %-30s: %s\n" % ('Quality', self.quality)
            buffer += " %-30s: %s\n" % ('Sample size', self.sample_size)
            buffer += " %-30s: %s\n" % ('Frame left', self.frame_left)
            buffer += " %-30s: %s\n" % ('Frame top', self.frame_top)
            buffer += " %-30s: %s\n" % ('Frame right', self.frame_right)
            buffer += " %-30s: %s\n" % ('Frame bottom', self.frame_bottom)
    
            return buffer
