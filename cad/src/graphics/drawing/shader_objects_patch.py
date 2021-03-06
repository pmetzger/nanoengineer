"""
### This is a copy of file OpenGL/GL/ARB/shader_objects.py from
### /Library/Python/2.5/site-packages/PyOpenGL-3.0.0b3-py2.5.egg .
### It replaces the broken version in PyOpenGL-3.0.0a6-py2.5.egg .
###
### The difference between the two is mainly that the wrapper function
### definitions aren't in "if" statements checking for null (undefined) wrapper
### functions. These don't work on Windows because its dll wrappers are
### different, so none of the wrappers get defined on Windows in the a6 version.
### 
### The only change to the b3 version to make it work in a6 is that two calls to
### "if OpenGL.ERROR_CHECKING:" are commented out with ### below.

OpenGL extension ARB.shader_objects

$version: $Id$

This module customises the behaviour of the 
OpenGL.raw.GL.ARB.shader_objects to provide a more 
Python-friendly API
"""
from OpenGL import platform, constants, constant, arrays
from OpenGL import extensions, wrapper
from OpenGL.GL import glget
import ctypes
from OpenGL.raw.GL.ARB.shader_objects import *

import OpenGL
from OpenGL import converters, error
GL_INFO_LOG_LENGTH_ARB = constant.Constant( 'GL_INFO_LOG_LENGTH_ARB', 0x8B84 )

glShaderSourceARB = platform.createExtensionFunction( 
    'glShaderSourceARB', dll=platform.GL,
    resultType=None, 
    argTypes=(constants.GLhandleARB, constants.GLsizei, ctypes.POINTER(ctypes.c_char_p), arrays.GLintArray,),
    doc = 'glShaderSourceARB( GLhandleARB(shaderObj), str( string) ) -> None',
    argNames = ('shaderObj', 'count', 'string', 'length',),
)
conv = converters.StringLengths( name='string' )
glShaderSourceARB = wrapper.wrapper(
    glShaderSourceARB
).setPyConverter(
    'count' # number of strings
).setPyConverter( 
    'length' # lengths of strings
).setPyConverter(
    'string', conv.stringArray
).setCResolver(
    'string', conv.stringArrayForC,
).setCConverter(
    'length', conv,
).setCConverter(
    'count', conv.totalCount,
)
del conv

for size in (1,2,3,4):
    for format,arrayType in (
        ('f',arrays.GLfloatArray),
        ('i',arrays.GLintArray),
        ):
        name = 'glUniform%(size)s%(format)svARB'%globals()
        globals()[name] = arrays.setInputArraySizeType(
            globals()[name],
            size,
            arrayType, 
            'value',
        )
        del format, arrayType
    del size

base_glGetObjectParameterivARB = glGetObjectParameterivARB
def glGetObjectParameterivARB( shader, pname ):
    """
    Retrieve the integer parameter for the given shader
    """
    status = arrays.GLintArray.zeros( (1,))
    status[0] = 1 
    base_glGetObjectParameterivARB(
        shader, pname, status
    )
    return status[0]
glGetObjectParameterivARB.wrappedOperation = base_glGetObjectParameterivARB
base_glGetObjectParameterfvARB = glGetObjectParameterfvARB
def glGetObjectParameterfvARB( shader, pname ):
    """
    Retrieve the float parameter for the given shader
    """
    status = arrays.GLfloatArray.zeros( (1,))
    status[0] = 1.0
    base_glGetObjectParameterfvARB(
        shader, pname,status
    )
    return status[0]
glGetObjectParameterfvARB.wrappedOperation = base_glGetObjectParameterfvARB
def _afterCheck( key ):
    """
    Generate an error-checking function for compilation operations
    """
    def GLSLCheckError( 
        result,
        baseOperation=None,
        cArguments=None,
        *args
        ):
        result = error.glCheckError( result, baseOperation, cArguments, *args )
        status = glGetObjectParameterivARB(
            cArguments[0], key
        )
        if not status:
            raise error.GLError( 
                result = result,
                baseOperation = baseOperation,
                cArguments = cArguments,
                description= glGetInfoLogARB( cArguments[0] )
            )
        return result
    return GLSLCheckError

###if OpenGL.ERROR_CHECKING:
glCompileShaderARB.errcheck = _afterCheck( GL_OBJECT_COMPILE_STATUS_ARB )
###if OpenGL.ERROR_CHECKING:
glLinkProgramARB.errcheck = _afterCheck( GL_OBJECT_LINK_STATUS_ARB )
## Not sure why, but these give invalid operation :(
##if glValidateProgramARB and OpenGL.ERROR_CHECKING:
##	glValidateProgramARB.errcheck = _afterCheck( GL_OBJECT_VALIDATE_STATUS_ARB )

base_glGetInfoLogARB = glGetInfoLogARB
def glGetInfoLogARB( obj ):
    """
    Retrieve the program/shader's error messages as a Python string

    returns string which is '' if no message
    """
    length = int(glGetObjectParameterivARB(obj, GL_INFO_LOG_LENGTH_ARB))
    if length > 0:
        log = ctypes.create_string_buffer(length)
        base_glGetInfoLogARB(obj, length, None, log)
        return log.value.strip('\000') # null-termination
    return ''
glGetInfoLogARB.wrappedOperation = base_glGetInfoLogARB

base_glGetAttachedObjectsARB = glGetAttachedObjectsARB
def glGetAttachedObjectsARB( obj ):
    """
    Retrieve the attached objects as an array of GLhandleARB instances
    """
    length= glGetObjectParameterivARB( obj, GL_OBJECT_ATTACHED_OBJECTS_ARB )
    if length > 0:
        storage = arrays.GLuintArray.zeros( (length,))
        base_glGetAttachedObjectsARB( obj, length, None, storage )
        return storage
    return arrays.GLuintArray.zeros( (0,))
glGetAttachedObjectsARB.wrappedOperation = base_glGetAttachedObjectsARB

base_glGetShaderSourceARB = glGetShaderSourceARB
def glGetShaderSourceARB( obj ):
    """
    Retrieve the program/shader's source code as a Python string

    returns string which is '' if no source code
    """
    length = int(glGetObjectParameterivARB(obj, GL_OBJECT_SHADER_SOURCE_LENGTH_ARB))
    if length > 0:
        source = ctypes.create_string_buffer(length)
        base_glGetShaderSourceARB(obj, length, None, source)
        return source.value.strip('\000') # null-termination
    return ''
glGetShaderSourceARB.wrappedOperation = base_glGetShaderSourceARB

base_glGetActiveUniformARB = glGetActiveUniformARB
def glGetActiveUniformARB(program, index):
    """
    Retrieve the name, size and type of the uniform of the index in the program
    """
    max_index = int(glGetObjectParameterivARB( program, GL_OBJECT_ACTIVE_UNIFORMS_ARB ))
    length = int(glGetObjectParameterivARB( program, GL_OBJECT_ACTIVE_UNIFORM_MAX_LENGTH_ARB))
    if index < max_index and index >= 0 and length > 0:
        name = ctypes.create_string_buffer(length)
        size = arrays.GLintArray.zeros( (1,))
        gl_type = arrays.GLuintArray.zeros( (1,))
        base_glGetActiveUniformARB(program, index, length, None, size, gl_type, name)
        return name.value, size[0], gl_type[0]
    raise IndexError, 'Index %s out of range 0 to %i' % (index, max_index - 1, )
glGetActiveUniformARB.wrappedOperation = base_glGetActiveUniformARB
