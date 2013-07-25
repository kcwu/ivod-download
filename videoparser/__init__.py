"""Parser to retrieve header information from various video formats."""
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

# Python built-in modules
import sys
import os

# Project modules
import videofile
import streams

__all__ = ['VideoParser']
__author__ = "Michael van Tellingen <michaelvantellingen at gmail.com>"

from videoparser.version import version as __version__

# List of plugins
parser_plugins = ['asf', 'matroska', 'avi', 'realmedia', 'quicktime']

class VideoParser(object):
    """ The VideoParser object will first guess the required parser based on
        the file extension. If that fails it will try each available parser.
        
        On success it will return the videofile.VideoFile object
    
        Example:
            parser = VideoParser()
            video = parser.parse_file("video.mkv")
            
            for video_stream in video.video_streams:
                print video_stream.resolution
                print video_stream.codec"""

    def __init__(self):
        """ Initialise the VideoParser object."""
        self.parsers = []
        self._import_parsers()
    
    def _import_parsers(self):
        """ Import the specified parsers in the global list parser_plugins. """
        # Import the parsers
        for plugin_filename in parser_plugins:
            try:
                module = __import__("videoparser.plugins." + plugin_filename,
                                    None, None, "plugins")
            except ImportError, err:
                raise
                print "Unable to open parser module '%s'" % plugin_filename 
                continue
        
            # Create parser object
            try:
                parser = module.Parser()
            except AttributeError, err:
                print "Invalid parser plugin: %s" % err
                continue
            
            self.parsers.append(parser)

    
    def parse_file(self, filename):
        """ Parse the given file and return a videofile.VideoFile object on
            success or None when there was a parsing error or no matching
            parser was found. """
            
        video = videofile.VideoFile()
        

        filetype = filename[filename.rindex(os.extsep)+1:]
        # Guess on the extension which parser to use
        for parser in self.parsers:
            if filetype in parser._file_types:
                break
            parser = None
        
        guessed_parser = parser
        if guessed_parser and self._parse_file_with(filename, parser, video):
            return video
        
        # Don't try other parsers
        #return None
    
        # Try all parsers then
        for parser in self.parsers:
            
            # Don't parse the file twice with the same parser
            if parser == guessed_parser:
                continue
            
            if self._parse_file_with(filename, parser, video):
                return video
    
        return None
    
    def _parse_file_with(self, filename, parser, video):
            
        # Check if this is the right parser for the file
        try:
            #print "Trying to parse %s with %s" % (filename, parser)
            if parser.parse(filename, video):
                return True
            
            print "failed..."
        except AssertionError:
            raise
            return False
        except IOError:
            print "IOError on file '%s'"  % filename
            return False
        except:
            print "Error parsing '%s'" % filename
            raise

if __name__ == "__main__":
    video_parser = VideoParser()
    for filename in sys.argv[1:]:
        print repr(video_parser.parse_file(filename))
