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

import videoparser.types as types


class BaseParser(object):
    pass



class Structure(object):
    _formatting = {types.bytes:     r'%r',
                   types.stream:    r'%r',
                   types.float:     r'%f',
                   types.int:       r'%d',
                   types.string:    r'%s'
    }
    
    
    def __init__(self, id):
        self.id = id
        self._values = {}
        self._keys = []
    
    def set(self, key, value, type=types.bytes, description=''):
        
        # This should become a warning
        if key in self._keys:
            raise AssertionError("Duplicate key in structure")
        
        self._keys.append(key)
        self._values[key] = (value, type, description)
    

    def __getattr__(self, key):
        if key in self._keys:
            return self._values[key][0]
        
        raise AttributeError("Attribute '%s' not found." % key)
    

    def __repr__(self):
        buffer  = "%s structure:\n" % self.id
        
        for key in self._keys:
            value, type, description = self._values[key]
            
            try:
                buffer += " %-30s: " % description
                
                if type != types.object:
                    buffer += self._formatting[type] %  value
                    buffer += '\n'
                    
                else:
                    buffer += '\n'
                    buffer += "\n".join(["   %s" % line for line
                                         in repr(value).split('\n')])
                
            except TypeError:
                raise
                print "Unable to print value '%s' with format '%s'" % (
                    value, self._formatting[type])
                raise
        return buffer