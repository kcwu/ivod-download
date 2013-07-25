""" Class to read binary information using various predefined types. """

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


# Only implement required information to retrieve video and audio information


import datetime

import struct
import cStringIO


from videoparser.streams import endian


class BinaryStream(object):
    
    def __init__(self, fileobj, filesize, endianess=endian.little):
        self._endianess = endianess
        self._fileobj = fileobj
        self._filesize = filesize
        
    def __del__(self):
        self.close()
        
    def read(self, length):
        if not length:
            return ''
        
        return self._fileobj.read(length)

    def tell(self):
        return self._fileobj.tell()
    
    def seek(self, position):
        return self._fileobj.seek(position)
    
    def close(self):
        return self._fileobj.close()

    def bytes_left(self):
        return self._fileobj.tell() < self._filesize

    def set_endianess(self, endianess):
        self._endianess = endianess
    
    def get_endianess(self):
        return self._endianess
    
    def unpack(self, type, length):
        """ Shorthand for unpack which uses the endianess defined with
            set_endianess(), used internally."""
        data = self.read(length)
        
        assert len(data) == length, "Unexpected end of stream"
        
        try:
            if self._endianess == endian.big:
                return struct.unpack('>' + type, data)[0]
            else:
                return struct.unpack('<' + type, data)[0]
        except struct.error:
            print len(data)
            print "Unable to unpack '%r'" % data
            raise
        
    def read_float(self):
        """ Read a 32bit float."""
        return self.unpack('f', 4)

    def read_qtfloat_32(self):
        """ Read a 32bits quicktime float."""
        # This comes from hachoir
        return self.read_int16() + float(self.read_uint16()) /65535

    def read_qt_ufloat32(self):
        """ Read a 32bits quicktime float."""
        # This comes from hachoir
        return self.read_uint16() + float(self.read_uint16()) /65535
    
    def read_uint64(self):
        """ Read an unsigned 64bit integer."""
        return self.unpack('Q', 8)

    def read_int64(self):
        """ Read an signed 64bit integer."""
        return self.unpack('q', 4)
        
    def read_uint32(self):
        """ Read an unsigned 32bit integer."""
        return self.unpack('I', 4)

    def read_int32(self):
        """ Read an signed 32bit integer."""
        return self.unpack('i', 4)

    def read_uint16(self):
        """ Read an unsigned 16bit integer."""
        return self.unpack('H', 2)

    def read_int16(self):
        """ Read an signed 16bit integer."""
        return self.unpack('h', 2)
    
    def read_uint8(self):
        """ Read an unsigned 8bit integer."""
        return ord(self.read(1))
    
    def read_int8(self):
        """ Read a signed 8bit integer."""
        return struct.unpack('b', self.read(1))[0]
    
    def read_dword(self):
        return self.read(4)
    
    def read_word(self):
        return self.read(2)
    
    def read_qword(self):
        return self.read(8)
    
    def read_byte(self):
        return self.read(1)

    def read_fourcc(self):
        return self.read(4)
    
    
    def read_timestamp_mac(self):
        """ Read a timestamp in mac format (seconds sinds 1904) """
        timestamp_base = datetime.datetime(1904, 1, 1, 0, 0)
        timestamp_value = datetime.timedelta(seconds=self.read_uint32())
        return timestamp_base + timestamp_value

    def read_timestamp_win(self):
        timestamp_base = datetime.datetime(1601, 1, 1, 0, 0, 0)
        timestamp_value = datetime.timedelta(
            microseconds=self.read_uint64()/10)
        
        return timestamp_base + timestamp_value
    
    # TODO: FIXME
    def read_wchars(self, len, null_terminated=False):
        data = self.read(len * 2)
        
        # String is null terminated, remove the null char
        if null_terminated:
            data = data[:-2]
        if self._endianess == endian.big:
            return unicode(data, "UTF-16-BE")
        else:
            return unicode(data, "UTF-16-LE")
    
    def read_subsegment(self, length):
        data = self.read(length)
        return BinaryStream(cStringIO.StringIO(data), len(data),
                            self._endianess)
    
    def convert_uintvar(self, data, endianess=None):
        """ Convert a string of variable length to an integer """
        
        # using struct.unpack is twice as fast as this function, however
        # it's not flexible enough
        
        if endianess is None:
            endianess = self._endianess
            
        if endianess == endian.big:
            data = data[::-1]
            
        mask = 0
        value = ord(data[0])
        for octet in data[1:]:
            mask += 8
            value += (ord(octet) << mask)

        return value

    # ASF Specification requires the guid type, which is 128 bits aka 16 bytes
    def read_guid(self):
        # See http://www.ietf.org/rfc/rfc4122.txt for specification
        # The version number is in the most significant 4 bits of the time
        # stamp (bits 4 through 7 of the time_hi_and_version field).
        # Python 2.5 includes a built-in guid module, which should be used
        
        
        # retrieve version        
        position = self.tell()
        self.seek(position + 6)
        version = self.read_uint16() >> 12
        self.seek(position)
        
        #print repr([hex(ord(x)) for x in self.read(16)])
        
        self.seek(position)
        
        time_low = self.read_uint32() 
        time_mid = self.read_uint16()
        time_hi  = self.read_uint16()
        clock_seq_hi    = self.read_uint8()
        clock_seq_low   = self.read_uint8()
        node            = self.read(6)
        
        #print "uuid version = %d - %X" % (version, time_low)
        if version == 1:
            node = self.convert_uintvar(node, endian.big)
        else:
            node = self.convert_uintvar(node, endian.big)
        
        return "%08X-%04X-%04X-%X%X-%012X" % (time_low,
                                            time_mid,
                                            time_hi,
                                            clock_seq_hi,
                                            clock_seq_low,
                                            node)
                                     
    def read_waveformatex(self):
        obj = self.WAVEFORMATEX()
        
        obj.codec_id = self.read_uint16()
        obj.channels = self.read_uint16()
        obj.sample_rate = self.read_uint32()
        obj.bit_rate = self.read_uint32()
        obj.block_alignment = self.read_uint16()
        obj.bits_per_sample = self.read_uint16()
        obj.codec_size = self.read_uint16()
        obj.codec_data = self.read_subsegment(obj.codec_size)
        return obj
    
    def read_bitmapinfoheader(self):
        obj = self.BITMAPINFOHEADER()
        
        obj.format_data_size    = self.read_uint32()
        obj.image_width         = self.read_uint32()
        obj.image_height        = self.read_uint32()
        obj.reserved            = self.read_uint16()
        obj.bpp                 = self.read_uint16()
        obj.compression_id      = self.read(4)
        obj.image_size          = self.read_uint32()
        obj.h_pixels_meter      = self.read_uint32()
        obj.v_pixels_meter      = self.read_uint32()
        obj.colors              = self.read_uint32()
        obj.important_colors    = self.read_uint32()
        obj.codec_data          = self.read_subsegment(obj.format_data_size -
                                                       40)
        
        return obj


    class BITMAPINFOHEADER(object):
        def __repr__(self):
            buffer  = "BITMAPINFOHEADER structure: \n"
            buffer += " %-35s : %s\n" % ("Format Data Size", self.format_data_size)
            buffer += " %-35s : %s\n" % ("Image Width", self.image_width)
            buffer += " %-35s : %s\n" % ("Image Height", self.image_height)
            buffer += " %-35s : %s\n" % ("Reserved", self.reserved)
            buffer += " %-35s : %s\n" % ("Bits Per Pixel Count", self.bpp)
            buffer += " %-35s : %s\n" % ("Compression ID", self.compression_id)
            buffer += " %-35s : %s\n" % ("Image Size", self.image_size)
            buffer += " %-35s : %s\n" % ("Horizontal Pixels Per Meter", self.h_pixels_meter)
            buffer += " %-35s : %s\n" % ("Vertical Pixels Per Meter", self.v_pixels_meter)
            buffer += " %-35s : %s\n" % ("Colors Used Count", self.colors)
            buffer += " %-35s : %s\n" % ("Important Colors Count", self.important_colors)
            buffer += " %-35s : %s\n" % ("Codec Specific Data", self.codec_data)

            return buffer
        
    # Used in ASF and AVI parser, contains audio information
    class WAVEFORMATEX(object):
        codec_ids = {
            0x2004:     "A_REAL/COOK",
            0x2003:     "A_REAL/28_8",
            0x2002:     "A_REAL/14_4",
            0x0130:     "A_REAL/SIPR",
            0x0270:     "A_REAL/ATRC",
            0x2001:     "A_DTS",
            0x2000:     "A_AC3",
            0x162:      "WMAP",
            0x161:      "WMA2",
            0x160:      "WMA2",
            0x50:       "MP2",
            0x55:       "MP3",
            0x1:        "A_PCM/INT/LIT",
            'unknown':  "???",
        }
        
        def __repr__(self):
            buffer  = "WAVEFORMATEX structure: \n"
            buffer += " %-35s : %s\n" % ("Codec ID / Format Tag", self.codec_id)
            buffer += " %-35s : %s\n" % ("Number of Channels", self.channels)
            buffer += " %-35s : %s\n" % ("Samples Per Second", self.sample_rate)
            buffer += " %-35s : %s\n" % ("Average Number of Bytes Per Second", self.bit_rate)
            buffer += " %-35s : %s\n" % ("Block Alignment", self.block_alignment)
            buffer += " %-35s : %s\n" % ("Bits Per Sample", self.bits_per_sample)
            buffer += " %-35s : %s\n" % ("Codec Specific Data Size",self.codec_size)
            buffer += " %-35s : %s\n" % ("Codec Specific Data", repr(self.codec_data))
            
            return buffer    

