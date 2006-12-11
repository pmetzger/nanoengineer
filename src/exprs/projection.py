"""
projection.py - utilities loosely related to setting up the projection matrix

$Id$
"""

from basic import *

from prefs_constants import UPPER_RIGHT, UPPER_LEFT, LOWER_LEFT, LOWER_RIGHT

from OpenGL.GL import *
from OpenGL.GLU import gluPickMatrix, gluUnProject

class DelegatingInstanceOrExpr(InstanceOrExpr, DelegatingMixin): pass #e refile if I like it

class DrawInCorner1(DelegatingInstanceOrExpr):
    delegate = Arg(Widget2D)
    corner = Arg(int, LOWER_RIGHT) # WARNING: only the default corner works properly yet
    def draw(self):
        # this code is modified from GLPane.drawcompass

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glMatrixMode(GL_PROJECTION) # WARNING: we're now in nonstandard matrixmode (for sake of gluPickMatrix and glOrtho -- needed??##k)
        glPushMatrix()
        glLoadIdentity()

        try:
            glpane = self.env.glpane
            aspect = 1.0 ###WRONG but the cases that use it don't work right anyway; BTW does glpane.aspect exist?
            corner = self.corner
            delegate = self.delegate

            ###e should get glpane to do this for us (ie call a method in it to do this if necessary)
            # (this code is copied from it)
            glselect = glpane.current_glselect
            if glselect:
                print "%r (ipath %r) setting up gluPickMatrix" % (self, self.ipath)
                x,y,w,h = glselect
                gluPickMatrix(
                        x,y,
                        w,h,
                        glGetIntegerv( GL_VIEWPORT ) #k is this arg needed? it might be the default...
                )
            
            if corner == UPPER_RIGHT:
                glOrtho(-50*aspect, 5.5*aspect, -50, 5.5,  -5, 500) # Upper Right
            elif corner == UPPER_LEFT:
                glOrtho(-5*aspect, 50.5*aspect, -50, 5.5,  -5, 500) # Upper Left
            elif corner == LOWER_LEFT:
                glOrtho(-5*aspect, 50.5*aspect, -5, 50.5,  -5, 500) # Lower Left
            else:
                ## glOrtho(-50*aspect, 5.5*aspect, -5, 50.5,  -5, 500) # Lower Right
                ## glOrtho(-50*aspect, 0, 0, 50,  -5, 500) # Lower Right [used now] -- x from -50*aspect to 0, y (bot to top) from 0 to 50
                glOrtho(-glpane.width * PIXELS, 0, 0, glpane.height * PIXELS,  -5, 500)
                    # approximately right for the checkbox, but I ought to count pixels to be sure (note, PIXELS is a pretty inexact number)

            glMatrixMode(GL_MODELVIEW) ###k guess 061210 at possible bugfix (and obviously needed in general) --
                # do this last to leave the matrixmode standard
                # (status of bugs & fixes unclear -- hard to test since even Highlightable(projection=True) w/o any change to
                # projection matrix (test _9cx) doesn't work!)
            offset = (-delegate.bright, delegate.bbottom) # only correct for LOWER_RIGHT
            glTranslatef(offset[0], offset[1], 0)
            delegate.draw()
            
        finally:
            glMatrixMode(GL_PROJECTION)
            glPopMatrix()
            glMatrixMode(GL_MODELVIEW) # be sure to do this last, to leave the matrixmode standard
            glPopMatrix()

        return
    pass # end of class DrawInCorner1

# Will this really work with highlighting? (I mean if delegate contains a Highlightable?)
# NO, because that doesn't save both matrices!
# is it inefficient to make every highlightable save both? YES, so let them ask whether they need to,
# and set a flag here that says they need to (but when we have displists we'll need to say how they should treat that flag,
# unless we're saving the ipath instead, as I presume we will be by then).

# BUT FOR NOW, just always save it, since easier.

# ==

# Since the above does not yet work with highlighting, try it in a completely different way for now, not using projection matrix,
# since we need the feature. Works!

class DrawInCorner(DelegatingInstanceOrExpr):
    delegate = Arg(Widget2D)
    corner = Arg(int, LOWER_RIGHT) # also allow it to be a pair of +-1, +-1
    want_depth = Option(float, 0.01) # this choice is nearer than cov_depth (I think!) but doesn't preclude 3D effects.
    def draw(self):
        glMatrixMode(GL_MODELVIEW) # not needed
        glPushMatrix()
        glLoadIdentity()
        try:
            glpane = self.env.glpane
            ## aspect = 1.0 ###WRONG but the cases that use it don't work right anyway; BTW does glpane.aspect exist?
            corner = self.corner
            delegate = self.delegate
            want_depth = self.want_depth
                # note about cov_depth:
                ## self.near = 0.25
                ## self.far = 12.0
                # so I predict cov_depth is 0.75 / 11.75 == 0.063829787234042548
                # but let's print it from a place that computes it, and see.
                # ... hmm, only place under that name is in selectMode.py, and that prints 0.765957458814 -- I bet it's something
                # different, but not sure. ###k (doesn't matter for now)

            # modified from _setup_modelview:
##            glTranslatef( 0.0, 0.0, - glpane.vdist) # this should make no difference, I think. try leaving it out. ###k

            if glpane.current_glselect or (0 and 'KLUGE' and hasattr(self, '_saved_stuff')):
                            # kluge did make it faster; still slow, and confounded by the highlighting-delay bug;
                            # now I fixed that bug, and now it seems only normally slow for this module -- ok for now.
                x1, y1, z1 = self._saved_stuff # this is needed to make highlighting work!
            else:
                x1, y1, z1 = self._saved_stuff = gluUnProject(glpane.width, glpane.height, want_depth) # max x and y, i.e. right top
                # (note, min x and y would be (0,0,want_depth), since these are windows coords, 0,0 is bottom left corner (not center))
                # Note: Using gluUnProject is probably better than knowing and reversing _setup_projection,
                # since it doesn't depend on knowing the setup code, except meaning of glpane height & width attrs,
                # and knowing that origin is centered between them.
##            print x1,y1,z1
            x1wish = glpane.width / 2.0 * PIXELS # / 2.0 because in these coords, screen center indeed has x == y == 0
            r = x1/x1wish
            glScale(r,r,r) # compensate for zoom*scale in _setup_projection, for error in PIXELS, and for want_depth != cov_depth
##            x1 /= r
##            y1 /= r
            z1 /= r
            # now the following might work except for z, so fix z here
            glTranslatef( 0.0, 0.0, z1)
            del x1,y1 # not presently used
            
            # I don't think we need to usage-track glpane height & width (or scale or zoomFactor etc)
            # since we'll redraw when those change, and redo this calc every time we draw.
            # The only exception would be if we're rendering into a display list.
            # I don't know if this code (gluUnProject) would even work in that case.
            # [I think I wrote a similar comment in some other file earlier today. #k]
            
            # move to desired corner, and align it with same corner of lbox
            # (#e could use an alignment prim for the corner if we had one)
            if corner == LOWER_RIGHT or corner == (+1, -1):
                glTranslatef( + glpane.width / 2.0 * PIXELS, - glpane.height / 2.0 * PIXELS, 0.0)
                offset = (- delegate.bright, + delegate.bbottom)
            elif corner == UPPER_RIGHT or corner == (+1, +1):
                glTranslatef( + glpane.width / 2.0 * PIXELS, + glpane.height / 2.0 * PIXELS, 0.0)
                offset = (- delegate.bright, - delegate.btop)
            elif corner == LOWER_LEFT or corner == (-1, -1):
                glTranslatef( - glpane.width / 2.0 * PIXELS, - glpane.height / 2.0 * PIXELS, 0.0)
                offset = (+ delegate.bleft,  + delegate.bbottom)
            elif corner == UPPER_LEFT or corner == (-1, +1):
                glTranslatef( - glpane.width / 2.0 * PIXELS, + glpane.height / 2.0 * PIXELS, 0.0)
                offset = (+ delegate.bleft,  - delegate.btop)
            else:
                raise ValueError, "invalid corner %r" % (corner,)
            
            glTranslatef(offset[0], offset[1], 0)
            
            delegate.draw()
            
        finally:
            glMatrixMode(GL_MODELVIEW) # not needed
            glPopMatrix()

        return
    pass # end of class DrawInCorner
