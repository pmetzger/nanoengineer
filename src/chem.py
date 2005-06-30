# Copyright (c) 2004-2005 Nanorex, Inc.  All rights reserved.
'''
chem.py -- class Atom, for single atoms, and related code

TEMPORARILY OWNED BY BRUCE AS OF 050502 for introducing higher-valence bonds #####@@@@@

$Id$

History:

- originally by Josh

- lots of changes, by various developers

- class molecule, for chunks, was moved into new file chunk.py circa 041118

- elements.py was split out of this module on 041221

- class Bond and associated code was moved into new file bonds.py by bruce 050502

- bruce optimized some things, including using 'is' and 'is not' rather than '==', '!='
  for atoms, molecules, elements, parts, assys, atomtypes in many places (not all commented individually); 050513

- bruce 050610 renamed class atom to class Atom; for now, the old name still works.
  The name should gradually be changed in all code (as of now it is not changed anywhere,
   not even in this file except for creating the class), and then the old name should be removed. ###@@@

- bruce 050610 changing how atoms are highlighted during Build mode mouseover. ###@@@ might not be done

'''
__author__ = "Josh"

# some of these imports might not be needed here in chem.py;
# it's not easy to clean this up, since this file imports everything from chunk.py and bond.py
# at the end (as of 050502), and a lot of other code imports everything from this file.
# [bruce comment 050502] ###@@@

from VQT import *
from LinearAlgebra import *
import string
import re
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

from drawer import *
from shape import *

from constants import *
from qt import *
from Utility import *
from MoleculeProp import *
from mdldata import marks, links, filler
from povheader import povpoint #bruce 050413

from HistoryWidget import orangemsg
from debug import print_compact_stack, print_compact_traceback, compact_stack

import platform # for atom_debug; note that uses of atom_debug should all grab it
  # from platform.atom_debug since it can be changed at runtime

from elements import *

import env

## from chunk import *
# -- done at end of file,
# until other code that now imports its symbols from this module
# has been updated to import from chunk directly.
# [-- bruce 041110, upon moving class molecule from this file into chunk.py]

## from bonds import *
# -- done at end of file,
# until other code that now imports its symbols from this module
# has been updated to import from bonds directly.
# [-- bruce 050502, upon moving class Bond (etc) from this file into bonds.py]

# ==

CPKvdW = 0.25

Gno = 0
def gensym(string):
    # warning, there is also a function like this in jigs.py
    # but with its own global counter!
    """return string appended with a unique number"""
    global Gno
    Gno += 1
    return string + str(Gno)

def genKey():
    """ produces generators that count indefinitely """
    i=0
    while 1:
        i += 1
        yield i

atKey = genKey() # generator for atom.key attribute.
    # As of bruce 050228, we now make use of the fact that this produces keys
    # which sort in the same order as atoms are created (e.g. the order they're
    # read from an mmp file), so we now require this in the future even if the
    # key type is changed.

###Huaicai: ... I'll add one more function for transferring
### vector to a string, which is mainly used for color vector
# [see also povpoint] [bruce revised this comment, 050502]

def stringVec(v):
    return "<" + str(v[0]) + "," + str(v[1]) + "," + str(v[2]) + ">"    

# == Atom

##e bruce 041109 thinks class atom should be renamed Atom so it's easier to find
# all its uses in the code. To ease the change, I'll wait for my rewrites to
# go in before doing the renaming at all, then define atom() to print a warning
# and call Atom().

from inval import InvalMixin #bruce 050510

class Atom(InvalMixin): #bruce 050610 renamed this from class atom, but most code still uses "atom" for now
    """An atom instance represents one real atom, or one "singlet"
    (a place near a real atom where another atom could bond to it).
       At any time, each atom has an element, a position in space,
    a list of bond objects it's part of, a list of jigs it's part of,
    and a reference to exactly one molecule object ("chunk") which
    owns it; all these attributes can change over time.
       It also has a never-changing key used as its key in self.molecule.atoms,
    a selection state, a display mode (which overrides that of its molecule),
    and (usually) some attributes added externally by its molecule, notably
    self.index. The attributes .index and .xyz are essentially for the
    private use of the owning molecule; see the methods posn and baseposn
    for details. Other code might add other attributes to an atom; some of
    those might be copied in the private method atom.copy_for_mol_copy().
    """
    # bruce 041109-16 wrote docstring
    # default values of instance variables:
    __killed = 0
    picked = 0
    display = diDEFAULT # rarely changed for atoms
    _modified_valence = False #bruce 050502
    info = None #bruce 050524 optim (can remove try/except if all atoms have this)
    ## atomtype -- set when first demanded, or can be explicitly set using set_atomtype or set_atomtype_but_dont_revise_singlets
    def __init__(self, sym, where, mol): #bruce 050511 allow sym to be elt symbol (as before), another atom, or an atomtype
        """Create an atom of element sym (e.g. 'C')
        (or, same elt/atomtype as atom sym; or, same atomtype as atomtype sym)
        at location where (e.g. V(36, 24, 36))
        belonging to molecule mol (can be None).
        Atom initially has no bonds and default hybridization type.
        """
        # unique key for hashing
        self.key = atKey.next()
        self.glname = env.alloc_my_glselect_name( self) #bruce 050610
        # self.element is an Elem object which specifies this atom's element
        # (this will be redundant with self.atomtype when that's set,
        #  but at least for now we keep it as a separate attr,
        #  both because self.atomtype is not always set,
        #  and since a lot of old code wants to use self.element directly)
        atype = None
        try:
            self.element = sym.element
                # permit sym to be another atom or an atomtype object -- anything that has .element
            #e could assert self.element is now an Elem, but don't bother -- if not, we'll find out soon enough
        except:
            # this is normal, since sym is usually an element symbol like 'C'
            self.element = PeriodicTable.getElement(sym)
        else:
            # sym was an atom or atomtype; use its atomtype for this atom as well (in a klugy way, sorry)
            try:
                atype = sym.atomtype # works if sym was an atom
            except:
                atype = sym
            assert atype.element is self.element # trivial in one of these cases, should improve #e
        
        # 'where' is atom's absolute location in model space,
        # until replaced with 'no' by shakedown, indicating
        # the location should be found using the formula in self.posn();
        # or it can be passed as 'no' by caller of __init__
        self.xyz = where
        # list of bond objects
        self.bonds = []
        # list of jigs (###e should be treated analogously to self.bonds)
        self.jigs = [] # josh 10/26 to fix bug 85
        # whether the atom is selected; see also assembly.selatoms
        # (note that Nodes also have .picked, with the same meaning, but atoms
        #  are not Nodes)
        ## [initialized as a class constant:]
        ## self.picked = 0
        # can be set to override molecule or global value
        ## [initialized as a class constant:]
        ## self.display = diDEFAULT

        # pointer to molecule containing this atom
        # (note that the assembly is not explicitly stored
        #  and that the index is only set later by methods in the molecule)
        self.molecule = None # checked/replaced by mol.addatom
        if mol is not None:
            mol.addatom(self)
            # bruce 041109 wrote addatom to do following for us and for hopmol:
            ## self.molecule = mol
            ## self.molecule.atoms[self.key] = self
            ## # now do the necessary invals in self.molecule for adding an atom
            ## ...
        else:
            # this now happens in mol.copy as of 041113
            # print "fyi: creating atom with mol == None"
            pass
        # (optional debugging code to show which code creates bad atoms:)
        ## if platform.atom_debug:
        ##     self._source = compact_stack()
        if atype is not None:
            self.set_atomtype_but_dont_revise_singlets( atype)
        return # from atom.__init__

    def atomtype_iff_set(self):
        return self.__dict__.get('atomtype', None)
    
    _inputs_for_atomtype = []
    def _recompute_atomtype(self):
        """Something needs this atom's atomtype but it doesn't yet have one.
        Give it our best guess of type, for whatever current bonds it has.
        """
        return self.reguess_atomtype()

    def reguess_atomtype(self):
        """Compute and return the best guess for this atom's atomtype
        given its current real bonds and open bond user-assigned types
        (but don't save this, and don't compare it to the current self.atomtype).
        """
        return self.element.atomtypes[0] ###@@@ stub. when it works, might use it in Transmute or even build_utils.

    def set_atomtype_but_dont_revise_singlets(self, atomtype): ####@@@@ should merge with set_atomtype*; perhaps use more widely
        "#doc"
        atomtype = self.element.find_atomtype( atomtype) # handles all forms of the request; exception if none matches
        assert atomtype.element is self.element # [redundant with find_atomtype]
        self.atomtype = atomtype
        self._changed_structure() #bruce 050627
        ###e need any more invals or updates for this method?? ###@@@
        return
        
    def set_atomtype(self, atomtype, always_remake_singlets = False):
        """[public method; not super-fast]
        Set this atom's atomtype as requested, and do all necessary invalidations or updates,
        including remaking our singlets as appropriate, and [###@@@ NIM] invalidating or updating bond valences.
           It's ok to pass None (warning: this sets default atomtype even if current one is different!),
        atomtype's name (specific to self.element) or fullname, or atomtype object. ###@@@ also match to fullname_for_msg()??? ###e
        The atomtype's element must match the current value of self.element --
        we never change self.element (for that, see mvElement).
           Special case: if new atomtype would be same as existing one (and that is already set), do nothing
        (rather than killing and remaking singlets, or even correcting their positions),
        unless always_remake_singlets is true. [not sure if this will be used in atomtype-setting menu-cmds ###@@@]
        """
        # Note: mvElement sets self.atomtype directly; if it called this method, we'd have infrecur!
        atomtype = self.element.find_atomtype( atomtype) # handles all forms of the request; exception if none matches
        assert atomtype.element is self.element # [redundant with find_atomtype] #e or transmute if not??
        if always_remake_singlets or (self.atomtype_iff_set() is not atomtype):
            self.direct_Transmute( atomtype.element, atomtype ) ###@@@ not all its needed invals/updates are implemented yet
            # note: self.atomtype = atomtype is done in direct_Transmute when it calls mvElement
        return

    def posn(self):
        """Return the absolute position of the atom in space.
        Public method, should be ok to call for any atom at any time.
        Private implementation note (fyi): this info is sometimes stored
        in the atom, and sometimes in its molecule.
        
        """
        #bruce 041104,041112 revised docstring
        #bruce 041130 made this return copies of its data, using unary '+',
        # to ensure caller's version does not change if the atom's version does,
        # or vice versa. Before this change, some new code to compare successive
        # posns of the same atom was getting a reference to the curpos[index]
        # array element, even though this was part of a longer array, so it
        # always got two refs to the same mutable data (which compared equal)! 
        if self.xyz != 'no':
            return + self.xyz
        else:
            return + self.molecule.curpos[self.index]

    def baseposn(self): #bruce 041107; rewritten 041201 to help fix bug 204; optimized 050513
        """Like posn, but return the mol-relative position.
        Semi-private method -- should always be legal, but assumes you have
        some business knowing about the mol-relative coordinate system, which is
        somewhat private since it's semi-arbitrary and is changed by some
        recomputation methods. Before 041201 that could include this one,
        if it recomputed basepos! But as of that date we'll never compute
        basepos or atpos if they're invalid.
        """
        #comment from 041201:
        #e Does this mean we no longer use basepos for drawing? Does that
        # matter (for speed)? We still use it for things like mol.rot().
        # We could inline the old baseposn into mol.draw, for speed.
        # BTW would checking for basepos here be worth the cost of the check? (guess: yes.) ###e
        # For speed, I'll inline this here: return self.molecule.abs_to_base( self.posn())
        #new code from 050513:
        mol = self.molecule
        basepos = mol.__dict__.get('basepos') #bruce 050513
        if basepos is not None and self.xyz == 'no': #bruce 050516 bugfix: fix sense of comparison to 'no'
            return basepos[self.index]
        # fallback to slower code from 041201:
        return mol.quat.unrot(self.posn() - mol.basecenter)

    def setposn(self, pos):
        """set the atom's absolute position,
        adjusting or invalidating whatever is necessary as a result.
        (public method; ok for atoms in frozen molecules too)
        """
        # fyi: called from depositMode, but not (yet?) from movie-playing. [041110]
        # [bruce 050406: now this is called from movie playing, at least for now.
        #  It's also been called (for awhile) from reading xyz files from Minimize.]
        # bruce 041130 added unary '+' (see atom.posn comment for the reason).
        pos = + pos
        if self.xyz != 'no':
            # bruce 041108 added xyz check, rather than asserting we don't need it;
            # this might never happen
            self.xyz = pos
            # The position being stored in the atom implies it's never been used
            # in the molecule (in curpos or atpos or anything derived from them),
            # so we don't need to invalidate anything in the molecule.
            # [bruce 041207 wonders: not even self.molecule.havelist = 0??
            #  I guess so, since mol.draw recomputes basepos, but not sure.
            #  But I also see no harm in doing it, and it was being done by
            #  deprecated code in setup_invalidate below, so I think I'll do it
            #  just to be safe.]
            self.molecule.havelist = 0
        else:
            # the position is stored in the molecule, so let it figure out the
            # proper way of adjusting it -- this also does the necessary invals.
            self.molecule.setatomposn(self.index, pos, self.element)
                # Warning: if atpos exists, this does lots of work being "incremental" rather than
                # just getting rid of it. Would it be better to always get rid of it completely?
                # At least, callers who'll call us a lot should consider doing that first. [bruce 050513]
        # also invalidate the bonds or jigs which depend on our position.
        #e (should this be a separate method -- does anything else need it?)
        for b in self.bonds:
            b.setup_invalidate()
        ###e we also need to invalidate jigs which care about their atoms' positions
        return

    def setposn_batch(self, pos): #bruce 050513; I wonder if almost all calls of setposn should be this instead? maybe...
        "use this in place of setposn, for speed, if you will run it a lot on atoms in the same chunk"
        mol = self.molecule
        try:
            del mol.atpos
        except:
            pass
        else:
            mol.changed_attr('atpos') #### , skip = ('basepos',) )
                #####@@@@@ this 'skip' probably causes bug 632, but is it needed for speed? [bruce 050516]
                #e not yet perfect, since we'd like to let mol stay frozen, with basepos same as curpos; will it when atpos comes back?
        self.setposn(pos)
    
    def adjSinglets(self, atom, nupos):
        """We're going to move atom, a neighbor of yours, to nupos,
        so adjust the positions of your singlets to match.
        """
        ###k could this be called for atom being itself a singlet, when dragging a singlet? [bruce 050502 question]
        apo = self.posn()
        # find the delta quat for the average real bond and apply
        # it to the singlets
        #bruce 050406 comment: this first averages the bond vectors,
        # old and new, then rotates old to match new. This is not
        # correct, especially if old or new (average) is near V(0,0,0).
        # The real problem is harder -- find a quat which best moves
        # atom as desired without moving the other neighbors.
        # Fixing this might fix some reported bugs with dragging atoms
        # within their chunks in Build mode. Better yet might be to
        # use old singlet posns purely as hints, recomputing new ones
        # from scratch (hints are useful to disambiguate this). ###@@@
        n = self.realNeighbors()
        old = V(0,0,0)
        new = V(0,0,0)
        for at in n:
            old += at.posn()-apo
            if at is atom: new += nupos-apo
            else: new += at.posn()-apo
        if n:
            q=Q(old,new)
            for at in self.singNeighbors():
                at.setposn(q.rot(at.posn()-apo)+apo)

    def __repr__(self):
        return self.element.symbol + str(self.key)

    def __str__(self):
        return self.element.symbol + str(self.key)

    def prin(self):
        """for debugging
        """
        lis = map((lambda b: b.other(self).element.symbol), self.bonds)
        print self.element.name, lis

    def draw(self, glpane, dispdef, col, level):
        """Draw this atom depending on whether it is picked
        and its display mode (possibly inherited from dispdef).
        An atom's display mode overrides the inherited one from
        the molecule or glpane, but a molecule's color overrides the atom's
        element-dependent one. No longer treats glpane.selatom specially
        (caller can draw selatom separately, on top of the regular atom).
           Also draws picked-atom wireframe, but doesn't draw any bonds.
           Return value gives the display mode we used (our own or inherited).
        """
        assert not self.__killed
        disp = default_display_mode # to be returned in case of early exception
        glPushName( self.glname) #bruce 050610 (for comments, see same code in Bond.draw)
            # (Note: these names won't be nested, since this method doesn't draw bonds;
            #  if it did, they would be, and using the last name would be correct,
            #  which is what's done (in GLPane.py) as of 050610.)
        try:
            # note use of basepos (in atom.baseposn) since it's being drawn under
            # rotation/translation of molecule
            pos = self.baseposn()
            disp, drawrad = self.howdraw(dispdef)
            if disp == diTUBES:
                pickedrad = drawrad * 1.8
            else:
                pickedrad = drawrad * 1.1
            color = col or self.element.color
            if disp in [diVDW, diCPK, diTUBES]:
                drawsphere(color, pos, drawrad, level)
            if self.picked:
                #bruce 041217 experiment: show valence errors for picked atoms by
                # using a different color for the wireframe.
                # (Since Transmute operates on picked atoms, and leaves them picked,
                #  this will serve to show whatever valence errors it causes. And
                #  showing it only for picked atoms makes it not mess up any images,
                #  even though there's not yet any way to turn this feature off.)
                if self.bad():
                    color = ErrorPickedColor
                else:
                    color = PickedColor
                drawwiresphere(color, pos, pickedrad)
        except:
            glPopName()
            print_compact_traceback("ignoring exception when drawing atom %r: " % self)
        else:
            glPopName()
        
        return disp # bruce 050513 added retval to help with an optim

    def bad(self): #bruce 041217 experiment
        "is this atom breaking any rules?"
        if self.element is Singlet:
            # should be correct, but this case won't be used as of 041217 [probably no longer needed even if used -- 050511]
            numbonds = 1
        else:
            numbonds = self.atomtype.numbonds
        return numbonds != len(self.bonds) ####@@@@ doesn't check bond valence at all... should it??

    def overdraw_with_special_color(self, color, level = None):
        "Draw this atom slightly larger than usual with the given special color and optional drawlevel, in abs coords."
        #bruce 050324; meant for use in Fuse Chunks mode;
        # also could perhaps speed up Extrude's singlet-coloring #e
        if level is None:
            level = self.molecule.assy.drawLevel
        pos = self.posn() # note, unlike for draw_as_selatom, this is in main model coordinates
        drawrad = self.selatom_radius() # slightly larger than normal drawing radius
        drawsphere(color, pos, drawrad, level) # always draw, regardless of display mode
        return
    
    def draw_in_abs_coords(self, glpane, color): #bruce 050610 ###@@@ needs to be told whether or not to "draw as selatom"; now it does
        """Draw this atom in absolute (world) coordinates,
        using the specified color (ignoring the color it would naturally be drawn with).
        See code comments about radius and display mode (current behavior might not be correct or optimal).
        """
        if self.__killed:
            return # I hope this is always ok...
        level = self.molecule.assy.drawLevel # this doesn't work if atom has been killed!
        pos = self.posn()
        ###@@@ remaining code might or might not be correct (issues: larger radius, display-mode independence)
        drawrad = self.selatom_radius() # slightly larger than normal drawing radius
        drawsphere(color, pos, drawrad, level) # always draw, regardless of display mode
        return
    
    def draw_as_selatom(self, glpane, dispdef, color, level):
        #bruce 041206, to avoid need for changeapp() when selatom changes
        # (fyi, as of 041206 the color arg is not used)
        if self.element is Singlet:
            color = LEDon
        else:
            color = orange
        pos = self.baseposn() # note, this is for use in the mol's coordinate system
        drawrad = self.selatom_radius(dispdef)
        drawsphere(color, pos, drawrad, level) # always draw, regardless of disp

    def selatom_radius(self, dispdef = None): #bruce 041207, should integrate with draw_as_selatom
        if dispdef is None:
            dispdef = self.molecule.get_dispdef()
        disp, drawrad = self.howdraw(dispdef)
        if self.element is Singlet:
            drawrad *= 1.02
                # increased radius might not be needed, if we would modify the
                # OpenGL depth threshhold criterion used by GL_DEPTH_TEST
                # to overwrite when depths are equal [bruce 041206]
        else:
            if disp == diTUBES:
                drawrad *= 1.7
            else:
                drawrad *= 1.02
        return drawrad
        
    def setDisplay(self, disp):
        self.display = disp
        self.molecule.changeapp(1)
        self.changed() # bruce 041206 bugfix (unreported bug); revised, bruce 050509
        # bruce 041109 comment:
        # atom.setDisplay changes appearance of this atom's bonds,
        # so: do we need to invalidate the bonds? No, they don't store display
        # info, and the geometry related to bond.setup_invalidate has not changed.
        # What about the mols on both ends of the bonds? The changeapp() handles
        # that for internal bonds, and external bonds are redrawn every time so
        # no invals are needed if their appearance changes.

    def howdraw(self, dispdef):
        """Tell how to draw the atom depending on its display mode (possibly
        inherited from dispdef, usually the molecule's effective dispdef).
        An atom's display mode overrides the inherited
        one from the molecule or glpane, but a molecule's color overrides the
        atom's element-dependent one (color is handled in atom.draw, not here,
        so this is just FYI).
           Return display mode and radius to use, in a tuple (disp, rad).
        For display modes in which the atom is not drawn, such as diLINES or
        diINVISIBLE, we return the same radius as in diCPK; it's up to the
        caller to check the disp we return and decide whether/how to use this
        radius (e.g. it might be used for atom selection in diLINES mode, even
        though the atoms are not shown).
        """
        #bruce 041206 moved rad *= 1.1 (for TUBES) from atom.draw into this method
        if dispdef == diDEFAULT: #bruce 041129 permanent debug code, re bug 21
            if platform.atom_debug and 0: #bruce 050419 disable this since always happens for Element Color Prefs dialog
                print "bug warning: dispdef == diDEFAULT in atom.howdraw for %r" % self
            dispdef = default_display_mode # silently work around that bug [bruce 041206]
        if self.element is Singlet:
            try:
                disp, rad_unused = self.bonds[0].other(self).howdraw(dispdef)
            except:
                # exceptions here (e.g. from bugs causing unbonded singlets)
                # cause too much trouble in other places to be permitted
                # (e.g. in selradius_squared and recomputing the array of them)
                # [bruce 041215]
                disp = default_display_mode
        else:
            if self.display == diDEFAULT:
                disp = dispdef
            else:
                disp = self.display
        rad = self.element.rvdw
        if disp != diVDW: rad=rad*CPKvdW
        if disp == diTUBES: rad = TubeRadius * 1.1 #bruce 041206 added "* 1.1"
        return (disp, rad)

    def selradius_squared(self):
        """Return square of desired "selection radius",
        or -1.0 if atom should not be selectable (e.g. invisible).
        This might depend on whether atom is selected (and that
        might even override the effect of invisibility); in fact
        this is the case for this initial implem.
        It also depends on the current display mode of
        self, its mol, and its glpane.
        Ignore self.molecule.hidden and whether self == selatom.
        Note: self.visible() should agree with self.selradius_squared() >= 0.0.
        """
        #bruce 041207. Invals for this are subset of those for changeapp/havelist.
        disp, rad = self.howdraw( self.molecule.get_dispdef() )
        if disp == diINVISIBLE and not self.picked:
            return -1.0
        else:
            return rad ** 2

    def visible(self, dispdef = None): #bruce 041214
        """Say whether this atom is currently visible, for purposes of selection.
        Note that this depends on self.picked, and display modes of self, its
        chunk, and its glpane, unless you pass disp (for speed) which is treated
        as the chunk's (defined or inherited) display mode.
        Ignore self.molecule.hidden and whether self == selatom.
        Return a correct value for singlets even though no callers [as of 041214]
        would care what we returned for them.
        Note: self.visible() should agree with self.selradius_squared() >= 0.0.
        """
        if self.picked:
            return True # even for invisible atoms
        if self.element is Singlet:
            disp = self.bonds[0].other(self).display
        else:
            disp = self.display
        if disp == diDEFAULT: # usual case; use dispdef
            # (note that singlets are assumed to reside in same chunks as their
            # real neighbor atoms, so the same dispdef is valid for them)
            if dispdef is None:
                disp = self.molecule.get_dispdef()
            else:
                disp = dispdef
        return not (disp == diINVISIBLE)

    def writemmp(self, mapping): #bruce 050322 revised interface to use mapping
        "[compatible with Node.writemmp, though we're not a subclass of Node]"
        num_str = mapping.encode_next_atom(self) # (note: pre-050322 code used an int here)
        disp = mapping.dispname(self.display) # note: affected by mapping.sim flag
        posn = self.posn() # might be revised below
        eltnum = self.element.eltnum # might be revised below
        if mapping.sim and self.element is Singlet:
            # special case for singlets in mmp files meant only for simulator:
            # pretend we're a Hydrogen, and revise posn and eltnum accordingly
            # (for writing only, not stored in our attrs)
            # [bruce 050404 to help fix bug 254]
            eltnum = Hydrogen.eltnum
            posn = self.ideal_posn_re_neighbor( self.singlet_neighbor(), pretend_I_am = Hydrogen )
            disp = "singlet" # kluge, meant as a comment in the file
        xyz = posn * 1000
            # note, xyz has floats, rounded below (watch out for this
            # if it's used to make a hash) [bruce 050404 comment]
        print_fields = (num_str, eltnum,
           int(xyz[0]), int(xyz[1]), int(xyz[2]), disp)
        mapping.write("atom %s (%d) (%d, %d, %d) %s\n" % print_fields)
        #bruce 050511: also write atomtype if it's not the default
        atype = self.atomtype_iff_set()
        if atype is not None and atype is not self.element.atomtypes[0]:
            mapping.write( "info atom atomtype = %s\n" % atype.name )
        # write only the bonds which have now had both atoms written
        #bruce 050502: write higher-valence bonds using their new mmp records,
        # one line per type of bond (only if we need to write any bonds of that type)
        bldict = {} # maps valence to list of 0 or more atom-encodings for bonds of that valence we need to write
        ## bl = [] # (note: in pre-050322 code bl held ints, not strings)
        for b in self.bonds:
            oa = b.other(self)
            #bruce 050322 revised this:
            oa_code = mapping.encode_atom(oa) # None, or true and prints as "atom number string"
            if oa_code:
                # we'll write this bond, since both atoms have been written
                valence = b.v6
                bl = bldict.setdefault(valence, [])
                bl.append(oa_code)
        bondrecords = bldict.items()
        bondrecords.sort() # by valence
        from bonds import bonds_mmprecord # avoid recursive import problem by doing this at runtime
        for valence, atomcodes in bondrecords:
            assert len(atomcodes) > 0
            mapping.write( bonds_mmprecord( valence, atomcodes ) + "\n")

    def readmmp_info_atom_setitem( self, key, val, interp ): #bruce 050511
        "For documentation, see docstring of an analogous method, such as readmmp_info_leaf_setitem."
        if key == ['atomtype']:
            # val should be the name of one of self.element's atomtypes (not an error if unrecognized)
            try:
                atype = self.element.find_atomtype(val)
            except:
                # didn't find it. (#e We ought to have a different API so a real error could be distinguished from that.)
                if platform.atom_debug:
                    print "atom_debug: fyi: info atom atomtype (in class atom) with unrecognized atomtype %r (not an error)" % (val,)
                pass
            else:
                self.set_atomtype_but_dont_revise_singlets( atype)
                    # don't add singlets, since this mmp record comes before the bonds, including bonds to singlets
        else:
            if platform.atom_debug:
                print "atom_debug: fyi: info atom (in class atom) with unrecognized key %r (not an error)" % (key,)
        return
    
    # write to a povray file:  draw a single atom
    def writepov(self, file, dispdef, col):
        color = col or self.element.color
        disp, rad = self.howdraw(dispdef)
        if disp in [diVDW, diCPK]:
            file.write("atom(" + povpoint(self.posn()) +
                       "," + str(rad) + "," +
                       stringVec(color) + ")\n")
        if disp == diTUBES:
            ###e this should be merged with other case, and should probably
            # just use rad from howdraw [bruce 041206 comment]
            file.write("atom(" + povpoint(self.posn()) +
                       "," + str(rad) + "," +
                       stringVec(color) + ")\n")

    # write to a MDL file.  By Chris Phoenix and Mark for John Burch [04-12-03]
    def writemdl(self, alist, f, dispdef, col):
        color = col or self.element.color
        disp, radius = self.howdraw(dispdef)
        xyz=map(float, A(self.posn()))
        rgb=map(int,A(color)*255)
        atnum = len(alist) # current atom number        
        alist.append([xyz, radius, rgb])
        
        # Write spline info for this atom
        atomOffset = 80*atnum
        (x,y,z) = xyz
        for spline in range(5):
            f.write("CPs=8\n")
            for point in range(8):
                index = point+spline*8
                (px,py,pz)=marks[index]
                px = px*radius + x; py = py*radius + y; pz = pz*radius + z
                if point == 7:
                    flag = "3825467397"
                else:
                    flag = "3825467393"
                f.write("%s 0 %d\n%f %f %f\n%s%s"%
                           (flag, index+19+atomOffset, px, py, pz,
                            filler, filler))
        
        for spline in range(8):
            f.write("CPs=5\n")
            for point in range(5):
                index = point+spline*5
                f.write("3825467393 1 %d\n%d\n%s%s"%
                           (index+59+atomOffset, links[index]+atomOffset,
                            filler, filler))
        return

    def checkpick(self, p1, v1, disp, r=None, iPic=None):
        """Selection function for atoms: [Deprecated! bruce 041214]
        Check if the line through point p1 in direction v1 goes through the
        atom (treated as a sphere with the same radius it would be drawn with,
        which might depend on disp, or with the passed-in radius r if that's
        supplied). If not, or if the atom is a singlet, or if not iPic and the
        atom is already picked, return None. If so, return the distance along
        the ray (from p1 towards v1) of the point closest to the atom center
        (which might be 0.0, which is false!), or None if that distance is < 0.
        """
        #bruce 041206 revised docstring to match code
        #bruce 041207 comment: the only call of checkpick is from assy.findpick
        if self.element is Singlet: return None
        if not r:
            disp, r = self.howdraw(disp)
        # bruce 041214:
        # this is surely bad in only remaining use (depositMode.getCoords):
        ## if self.picked and not iPic: return None 
        dist, wid = orthodist(p1, v1, self.posn())
        if wid > r: return None
        if dist<0: return None
        return dist

    def getinfo(self):
        # Return information about the selected atom for the msgbar
        # [mark 2004-10-14]
        # bruce 041217 revised XYZ format to %.2f, added bad-valence info
        # (for the same atoms as self.bad(), but in case conditions are added to
        #  that, using independent code).
        # bruce 050218 changing XYZ format to %.3f (after earlier discussion with Josh).
        
        if self is self.molecule.assy.ppa2: return
            
        xyz = self.posn()

        atype_string = ""
        if len(self.element.atomtypes) > 1: #bruce 050511
            atype_string = "(%s) " % self.atomtype.name

        ainfo = ("Atom %s %s[%s] [X = %.3f] [Y = %.3f] [Z = %.3f]" % \
            ( self, atype_string, self.element.name, xyz[0], xyz[1], xyz[2] ))
        
        # ppa2 is the previously picked atom.  ppa3 is the atom picked before ppa2.
        # They are both reset to None when entering SELATOMS mode.
        # Include the distance between self and ppa2 in the info string.
        if self.molecule.assy.ppa2:
            try:
                ainfo += (". Distance between %s-%s is %.3f." % \
                    (self, self.molecule.assy.ppa2, vlen(self.posn()-self.molecule.assy.ppa2.posn())))
            except:
                print_compact_traceback("bug, fyi: ignoring exception in atom distance computation: ") #bruce 050218
                pass
            
            # Include the angle between self, ppa2 and ppa3 in the info string.
            if self.molecule.assy.ppa3:
                try:
                    # bruce 050218 protecting angle computation from exceptions
                    # (to reduce severity of undiagnosed bug 361).
                    v1 = norm(self.posn()-self.molecule.assy.ppa2.posn())
                    v2 = norm(self.molecule.assy.ppa3.posn()-self.molecule.assy.ppa2.posn())
                    dotprod = dot(v1,v2)
                    if dotprod > 1.0:
                        #bruce 050414 investigating bugs 361 and 498 (probably the same underlying bug);
                        # though (btw) it would probably be better to skip this angle-printing entirely ###e
                        # if angle obviously 0 since atoms 1 and 3 are the same.
                        # This case (dotprod > 1.0) can happen due to numeric roundoff in norm();
                        # e.g. I've seen this be 1.0000000000000002 (as printed by '%r').
                        # If not corrected, it can make acos() return nan or have an exception!
                        dotprod = 1.0
                    elif dotprod < -1.0:
                        dotprod = -1.0
                    ang = acos(dotprod) * 180/pi
                    ainfo += (" Angle for %s-%s-%s is %.2f degrees." %\
                        (self, self.molecule.assy.ppa2, self.molecule.assy.ppa3, ang))
                except:
                    print_compact_traceback("bug, fyi: ignoring exception in atom angle computation: ") #bruce 050218
                    pass
            
            # ppa3 is ppa2 for next atom picked.
            self.molecule.assy.ppa3 = self.molecule.assy.ppa2 
        
        # ppa2 is self for next atom picked.
        self.molecule.assy.ppa2 = self
            
        if len(self.bonds) != self.atomtype.numbonds:
            # I hope this can't be called for singlets! [bruce 041217]
            ainfo += platform.fix_plurals(" (has %d bond(s), should have %d)" % \
                                          (len(self.bonds), self.atomtype.numbonds))
        return ainfo

    def pick(self):
        """make the atom selected
        """
        if self.element is Singlet: return
        # If select atoms filter is on, only pick element type in the filter combobox
        if self.molecule.assy.w.SAFilter.isChecked() and \
            self.element.name != self.molecule.assy.w.SAFilterList.currentText(): return
        if not self.picked:
            self.picked = 1
            self.molecule.assy.selatoms[self.key] = self
                #bruce comment 050308: should be ok even if selatoms recomputed for assy.part
            self.molecule.changeapp(1)
            # bruce 041227 moved message from here to one caller, pick_at_event
            #bruce 050308 comment: we also need to ensure that it's ok to pick atoms
            # (wrt selwhat), and change current selection group to include self.molecule
            # if it doesn't already. But in practice, all callers might be ensuring these
            # conditions already (this is likely to be true if pre-assy/part code was correct).
            # In particular, atoms are only picked by user in glpane or perhaps by operations
            # on current part, and in both cases the picked atom would be in the current part.
            # If atoms can someday be picked from the mtree (directly or by selecting a jig that
            # connects to them), this will need review.
        return
    
    def unpick(self):
        """make the atom unselected
        """
        # note: this is inlined into assembly.unpickatoms
        # bruce 041214: should never be picked, so Singlet test is not needed,
        # and besides if it ever *does* get picked (due to a bug) you should let
        # the user unpick it!
        ## if self.element is Singlet: return 
        if self.picked:
            try:
                #bruce 050309 catch exceptions, and do this before picked=0
                # so that if selatoms is recomputed now, the del will still work
                # (required by upcoming "assy/part split")
                del self.molecule.assy.selatoms[self.key]
            except:
                if platform.atom_debug:
                    print_compact_traceback("atom_debug: atom.unpick finds atom not in selatoms: ")
            self.picked = 0
            self.molecule.changeapp(1)

    def copy_for_mol_copy(self, numol):
        # bruce 041113 changed semantics, and renamed from copy()
        # to ensure only one caller, which is mol.copy()
        """create a copy of the atom (to go in numol, a copy of its molecule),
        with .xyz == 'no' and .index the same as in self;
        caller must also call numol.invalidate_atom_lists() at least once
        [private method, only suitable for use from mol.copy(), since use of
         same .index assumes numol will be given copied curpos/basepos arrays.]
        """
        nuat = atom(self, 'no', None) #bruce 050524: pass self so its atomtype is copied
        numol.addcopiedatom(nuat)
        ## numol.invalidate_atom_lists() -- done in caller now
        nuat.index = self.index
        nuat.display = self.display #bruce 041109 new feature, seems best
        nuat.info = self.info # bruce 041109, needed by extrude and other future things; revised 050524
        return nuat

    def copy(self): # bruce 041116, new method (has same name as an older method, now named copy_for_mol_copy)
        """Public method: copy an atom, with no special assumptions;
        new atom is not in any mol but could be added to one using mol.addatom.
        """
        nuat = atom(self, self.posn(), None) #bruce 050524: pass self so its atomtype is copied
        nuat.display = self.display
        nuat.info = self.info # bruce 041109, needed by extrude and other future things; revised 050524
        return nuat

    def break_unmade_bond(self, origbond, origatom): #bruce 050524
        """Add singlets (or do equivalent invals) as if origbond was copied from origatom
        onto self (a copy of origatom), then broken; uses origatom
        so it can find the other atom and know bond direction
        (it assumes self might be translated but not rotated, wrt origatom).
        For now this works like mol.copy used to, but later it might "inval singlets" instead.
        """
        # compare to code in Bond.unbond() (maybe merge it? ####@@@@ need to inval things to redo singlets sometimes?)
        a = origatom
        b = origbond
        numol = self.molecule
        x = atom('X', b.ubp(a), numol) ###k verify atom.__init__ makes copy of posn, not stores original (tho orig ok if never mods it)
        na = self ## na = ndix[a.key]
        from bonds import bond_copied_atoms # can't do at start of module -- recursive import
        bond_copied_atoms(na, x, origbond) # same properties as origbond... sensible in all cases?? ##k
        return
        
    def unbond(self, b):
        """Private method (for use mainly by bonds); remove b from self and
        usually replace it with a singlet (which is returned). Details:
           Remove bond b from self (error if b not in self.bonds).
        Note that bonds are compared with __eq__, not 'is', by 'in' and 'remove'.
        Only call this when b will be destroyed, or "recycled" (by bond.rebond);
        thus no need to invalidate the bond b itself -- caller must do whatever
        inval of bond b is needed (which is nothing, if it will be destroyed).
           Then replace bond b in self.bonds with a new bond to a new singlet,
        unless self or the old neighbor atom is a singlet. Return the new
        singlet, or None if one was not created. Do all necessary invalidations
        of molecules, BUT NOT OF b (see above).
           If self is a singlet, kill it (singlets must always have one bond).
           As of 041109, this is called from atom.kill of the other atom,
        and from bond.bust, and [added by bruce 041109] from bond.rebond.
        """
        # [obsolete comment: Caller is responsible for shakedown
        #  or kill (after clearing externs) of affected molecules.]
        
        # code and docstring revised by bruce 041029, 041105-12
        
        b.invalidate_bonded_mols() #e more efficient if callers did this
        
        try:
            self.bonds.remove(b)
        except ValueError: # list.remove(x): x not in list
            # this is always a bug in the caller, but we catch it here to
            # prevent turning it into a worse bug [bruce 041028]
            msg = "fyi: atom.unbond: bond %r should be in bonds %r\n of atom %r, " \
                  "but is not:\n " % (b, self.bonds, self)
            print_compact_traceback(msg)
        # normally replace an atom (bonded to self) with a singlet,
        # but don't replace a singlet (at2) with a singlet,
        # and don't add a singlet to another singlet (self).
        if self.element is Singlet:
            if not self.bonds:
                self.kill() # bruce 041115 added this and revised all callers
            else:
                print "fyi: bug: unbond on a singlet %r finds unexpected bonds left over in it, %r" % (self,self.bonds)
                # don't kill it, in this case [bruce 041115; I don't know if this ever happens]
            return None
        at2 = b.other(self)
        if at2.element is Singlet:
            return None
        x = atom('X', b.ubp(self), self.molecule) # invals mol as needed
        self.molecule.bond(self, x) # invals mol as needed
        return x # new feature, bruce 041222

    def get_neighbor_bond(self, neighbor):
        '''Return the bond to a neighboring atom, or None if none exists.
        '''
        for b in self.bonds:
            ## if b.other(self) == neighbor: could be faster [bruce 050513]:
            if b.atom1 is neighbor or b.atom2 is neighbor:
               return b
        return None
            
    def hopmol(self, numol): #bruce 041105-041109 extensively revised this
        """If this atom is not already in molecule numol, move it
        to molecule numol. (This only changes the owning molecule -- it doesn't
        change this atom's position in space!) Also move its singlet-neighbors.
        Do all necessary invalidations of old and new molecules,
        including for this atom's bonds (both internal and external),
        since some of those bonds might change from internal to external
        or vice versa, which changes how they need to be drawn.
        """
        # bruce 041222 removed side effect on self.picked
        if self.molecule is numol:
            return
        self.molecule.delatom(self) # this also invalidates our bonds
        numol.addatom(self)
        for atm in self.singNeighbors():
            assert self.element is not Singlet # (only if we have singNeighbors!)
                # (since hopmol would infrecur if two singlets were bonded)
            atm.hopmol(numol)
        return
    
    def neighbors(self):
        """return a list of the atoms bonded to this one
        """
        return map((lambda b: b.other(self)), self.bonds)
    
    def realNeighbors(self):
        """return a list of the atoms not singlets bonded to this one
        """
        return filter(lambda atm: atm.element is not Singlet, self.neighbors())
    
    def singNeighbors(self):
        """return a list of the singlets bonded to this atom
        """
        return filter(lambda atm: atm.element is Singlet, self.neighbors())

    def mvElement(self, elt, atomtype = None): #bruce 050511 added atomtype arg
        """[Public low-level method:]
        Change the element type of this atom to element elt
        (an element object for a real element, not Singlet),
        and its atomtype to atomtype (which if provided must be an atomtype for elt),
        and do the necessary invalidations (including if the
        *prior* element type was Singlet).
           Note: this does not change any atom or singlet positions, so callers
        wanting to correct the bond lengths need to do that themselves.
        It does not even delete or add extra singlets to match the new element
        type; for that, use atom.Transmute.
        """
        if atomtype is None:
            atomtype = elt.atomtypes[0]
            # Note: we do this even if self.element is elt and self.atomtype is not elt.atomtypes[0] !
            # That is, passing no atomtype is *always* equivalent to passing elt's default atomtype,
            # even if this results in changing this atom's atomtype but not its element.
        assert atomtype.element is elt
        if platform.atom_debug:
            if elt is Singlet: #bruce 041118
                # this is unsupported; if we support it it would require
                # moving this atom to its neighbor atom's chunk, too
                # [btw we *do* permit self.element is Singlet before we change it]
                print "atom_debug: fyi, bug?: mvElement changing %r to a singlet" % self
        if self.atomtype_iff_set() is atomtype:
            assert self.element is elt # i.e. assert that self.element and self.atomtype were consistent
            if platform.atom_debug: #bruce 050509
                print_compact_stack( "atom_debug: fyi, bug?: mvElement changing %r to its existing element and atomtype" % self )
            return #bruce 050509, not 100% sure it's correct, but if not, caller probably has a bug (eg relies on our invals)
        # now we're committed to doing the change
        if (self.element is Singlet) != (elt is Singlet):
            # set of singlets is changing
            #bruce 050224: fix bug 372 by invalidating singlets
            self.molecule.invalidate_attr('singlets')
        self.changed() #bruce 050509
        self.element = elt
        self.atomtype = atomtype
            # note: we have to set self.atomtype directly -- if we used set_atomtype,
            # we'd have infrecur since it calls *us*! [#e maybe this should be revised??]
            # (would it be ok to call set_atomtype_but_dont_revise_singlets?? #k)
        for b in self.bonds:
            b.setup_invalidate()
        self.molecule.changeapp(1)
        # no need to invalidate shakedown-related things, I think [bruce 041112]
        self._changed_structure() #bruce 050627
        return

    def changed(self): #bruce 050509; perhaps should use more widely
        mol = self.molecule
        if mol is None: return #k needed??
        part = mol.part
        if part is None: return # (might well be needed, tho not sure)
        part.changed()

##    def invalidate_bonds(self): # also often inlined
##        for b in self.bonds:
##            b.setup_invalidate()
        
    def killed(self): #bruce 041029
        """(Public method) Report whether an atom has been killed.
        Details: For an ordinary atom, return False.
        For an atom which has been properly killed, return True.
        For an atom which has something clearly wrong with it,
        print an error message, try to fix the problem,
        effectively kill it, and return True.
        Don't call this on an atom still being initialized.
        """
        try:
            killed = not (self.key in self.molecule.atoms)
            if killed:
                assert self.__killed == 1
                assert not self.picked
                from chunk import _nullMol
                assert self.molecule is _nullMol or self.molecule is None
                # thus don't do this: assert not self.key in self.molecule.assy.selatoms
                assert not self.bonds
                assert not self.jigs
            else:
                assert self.__killed == 0
            return killed
        except:
            print_compact_traceback("fyi: atom.killed detects some problem" \
                " in atom %r, trying to work around it:\n " % self )
            try:
                self.__killed = 0 # make sure kill tries to do something
                self.kill()
            except:
                print_compact_traceback("fyi: atom.killed: ignoring" \
                    " exception when killing atom %r:\n " % self )
            return True
        pass # end of atom.killed()

    def kill(self):
        """Public method:
        kill an atom: unpick it, remove it from its jigs, remove its bonds,
        then remove it from its molecule. Do all necessary invalidations.
        (Note that molecules left with no atoms, by this or any other op,
        will themselves be killed.)
        """
        if self.__killed:
            if not self.element is Singlet:
                print_compact_stack("fyi: atom %r killed twice; ignoring:\n" % self)
            else:
                # Note: killing a selected mol, using Delete key, kills a lot of
                # singlets twice; I guess it's because we kill every atom
                # and singlet in mol, but also kill singlets of killed atoms.
                # So I'll declare this legal, for singlets only. [bruce 041115]
                pass
            return
        self.__killed = 1 # do this now, to reduce repeated exceptions (works??)
        # unpick
        try:
            self.unpick() #bruce 041029
        except:
            print_compact_traceback("fyi: atom.kill: ignoring error in unpick: ")
            pass
        # bruce 041115 reordered everything that follows, so it's safe to use
        # delatom (now at the end, after things which depend on self.molecule),
        # since delatom resets self.molecule to None.
        
        # josh 10/26 to fix bug 85 - remove from jigs
        for j in self.jigs[:]: #bruce 050214 copy list as a precaution
            try:
                j.rematom(self)
                # [bruce 050215 comment: this might kill the jig (if it has no
                #  atoms left), and/or it might remove j from self.jigs, but it
                #  will never recursively kill this atom, so it should be ok]
            except:
                print_compact_traceback("fyi: atom.kill: ignoring error in rematom %r from jig %r: " % (self,j) )
        self.jigs = [] #bruce 041029 mitigate repeated kills
            # [bruce 050215 comment: this should soon no longer be needed, but will be kept as a precaution]
        
        # remove bonds
        for b in self.bonds[:]: #bruce 050214 copy list as a precaution
            n = b.other(self)
            n.unbond(b) # note: this can create a new singlet on n, if n is real,
                        # which requires computing b.ubp which uses self.posn()
                        # or self.baseposn(); or it can kill n if it's a singlet.
                        #e We should optim this for killing lots of atoms at once,
                        # eg when killing a chunk, since these new singlets are
                        # wasted then. [bruce 041201]
            # note: as of 041029 unbond also invalidates externs if necessary
            ## if n.element is Singlet: n.kill() -- done in unbond as of 041115
        self.bonds = [] #bruce 041029 mitigate repeated kills

        # only after disconnected from everything else, remove it from its molecule
        try:
            ## del self.molecule.atoms[self.key]
            self.molecule.delatom(self) # bruce 041115
            # delatom also kills the mol if it becomes empty (as of bruce 041116)
        except KeyError:
            print "fyi: atom.kill: atom %r not in its molecule (killed twice?)" % self
            pass
        return # from atom.kill

    def Hydrogenate(self):
        """[Public method; does all needed invalidations:]
        If this atom is a singlet, change it to a hydrogen,
        and move it so its distance from its neighbor is correct
        (regardless of prior distance, but preserving prior direction).
        [#e sometimes it might be better to fix the direction too, like in depositMode...]
           If hydrogenate succeeds return number 1, otherwise, 0.
        """
        # Huaicai 1/19/05 added return value.
        if not self.element is Singlet: return 0
        other = self.bonds[0].other(self)
        self.mvElement(Hydrogen)
        #bruce 050406 rewrote the following, so it no longer depends
        # on old pos being correct for self being a Singlet.
        newpos = self.ideal_posn_re_neighbor( other)
        self.setposn(newpos)
        return 1
        
    def ideal_posn_re_neighbor(self, neighbor, pretend_I_am = None): # see also snuggle
        #bruce 050404 to help with bug 254 and maybe Hydrogenate
        """Given one of our neighbor atoms (real or singlet)
        [neighborness not verified! only posn is used, not the bond --
         this might change when we have bond-types #e]
        and assuming it should remain fixed and our bond to it should
        remain in the same direction, and pretending (with no side effects)
        that our element is pretend_I_am if this is given,
        what position should we ideally have
        so that our bond to neighbor has the correct length?
        """
        me = self.posn()
        it = neighbor.posn()
        length = vlen( me - it )
        if not length:
            #e atom_debug warning?
            # choose a better direction? only caller knows what to do, i guess...
            # but [050406] I think an arbitrary one is safer than none!
            ## return me # not great...
            it_to_me_direction = V(1,0,0)
        else:
            it_to_me_direction = norm( me - it )
            it_to_me_direction = norm( it_to_me_direction )
                # for original len close to 0, this might help make new len 1 [bruce 050404]
        if pretend_I_am: #bruce 050511 revised for atomtype
            ## my_elem = pretend_I_am # not needed
            my_atype = pretend_I_am.atomtypes[0] # even if self.element is pretend_I_am
        else:
            ## my_elem = self.element
            my_atype = self.atomtype
        ## its_elem = neighbor.element # not needed
        its_atype = neighbor.atomtype
            # presently we ignore the bond-valence between us and that neighbor atom,
            # even if this can vary for different bonds to it (for the atomtype it has)
        newlen = my_atype.rcovalent + its_atype.rcovalent #k Singlet.atomtypes[0].rcovalent better be 0, check this
        return it + newlen * it_to_me_direction
        
    def Dehydrogenate(self):
        """[Public method; does all needed invalidations:]
        If this is a hydrogen atom (and if it was not already killed),
        kill it and return 1 (int, not boolean), otherwise return 0.
        (Killing it should produce a singlet unless it was bonded to one.)
        """
        # [fyi: some new features were added by bruce, 041018 and 041029;
        #  need for callers to shakedown or kill mols removed, bruce 041116]
        if self.element is Hydrogen and not self.killed():
            #bruce 041029 added self.killed() check above to fix bug 152
            self.kill()
            # note that the new singlet produced by killing self might be in a
            # different mol (since it needs to be in our neighbor atom's mol)
            #bruce 050406 comment: if we reused the same atom (as in Hydrogenate)
            # we'd be better for movies... just reusing its .key is not enough
            # if we've internally stored alists. But, we'd like to fix the direction
            # just like this does for its new singlet... so I'm not changing this for now.
            # Best solution would be a new method for H or X to fix their direction
            # as well as their distance. ###@@@
            return 1
        else:
            return 0
        pass

    def snuggle(self):
        """self is a singlet and the simulator has moved it out to the
        radius of an H. move it back. the molecule may or may not be still
        in frozen mode. Do all needed invals.
        """
        if not self.bonds:
            #bruce 050428: a bug, but probably just means we're a killed singlet.
            # The caller should be fixed, and maybe is_singlet should check this too,
            # but for now let's also make it harmless here:
            if platform.atom_debug:
                print_compact_stack( "atom_debug: bug (ignored): snuggling a killed singlet: ")
            return
        #bruce 050406 revised docstring to say mol needn't be frozen.
        # note that this could be rewritten to call ideal_posn_re_neighbor,
        # but we'll still use it since it's better tested and faster.
        o = self.bonds[0].other(self)
        op = o.posn()
        np = norm(self.posn()-op)*o.atomtype.rcovalent + op
        self.setposn(np) # bruce 041112 rewrote last line

    def Passivate(self): ###@@@ not yet modified for atomtypes since it's not obvious what it should do! [bruce 050511]
        """[Public method, does all needed invalidations:]
        Change the element type of this atom to match the number of
        bonds with other real atoms, and delete singlets.
        """
        # bruce 041215 modified docstring, added comments, capitalized name
        el = self.element
        PTsenil = PeriodicTable.getPTsenil()
        line = len(PTsenil)
        for i in range(line):
            if el in PTsenil[i]:
                line = i
                break
        if line == len(PTsenil): return #not in table
        # (note: we depend on singlets not being in the table)
        nrn = len(self.realNeighbors())
        for atm in self.singNeighbors():
            atm.kill()
        try:
            newelt = PTsenil[line][nrn]
        except IndexError:
            pass # bad place for status msg, since called on many atoms at once
        else:
            self.mvElement(newelt)
        # note that if an atom has too many bonds we'll delete the
        # singlets anyway -- which is fine

    def is_singlet(self):
        return self.element is Singlet # [bruce 050502 comment: it's possible self is killed and len(self.bonds) is 0]
    
    def singlet_neighbor(self): #bruce 041109 moved here from extrudeMode.py
        "return the atom self (a known singlet) is bonded to, checking assertions"
        assert self.element is Singlet, "%r should be a singlet but is %s" % (self, self.element.name)
            #bruce 050221 added data to the assert, hoping to track down bug 372 when it's next seen
        obond = self.bonds[0]
        atom = obond.other(self)
        assert atom.element is not Singlet, "bug: a singlet %r is bonded to another singlet %r!!" % (self,atom)
        return atom

    # higher-valence bonds methods [bruce 050502] [bruce 050627 comment: a lot of this might be obsolete. ###@@@]
    
    def singlet_v6(self):
        assert self.element is Singlet, "%r should be a singlet but is %s" % (self, self.element.name)
        assert len(self.bonds) == 1, "%r should have exactly 1 bond but has %d" % (self, len(self.bonds))
        return self.bonds[0].v6

    singlet_valence = singlet_v6 ###@@@ need to decide which name to keep! probably this one, singlet_valence. [050502 430pm]

    def singlet_reduce_valence_noupdate(self, vdelta):
            # this might or might not kill it;
            # it might even reduce valence to 0 but not kill it,
            # letting base atom worry about that
            # (and letting it take advantage of the singlet's position, when it updates things)
        assert self.element is Singlet, "%r should be a singlet but is %s" % (self, self.element.name)
        assert len(self.bonds) == 1, "%r should have exactly 1 bond but has %d" % (self, len(self.bonds))
        self.bonds[0].reduce_valence_noupdate(vdelta, permit_illegal_valence = True) # permits in-between, 0, or negative(?) valence
        return

    def update_valence(self):
            # repositions/alters existing singlets, updates bonding pattern, valence errors, etc;
            # might reorder bonds, kill singlets; but doesn't move the atom and doesn't alter
            # existing real bonds or other atoms; it might let atom record how it wants to move,
            # when it has a chance and wants to clean up structure, if this can ever be ambiguous
            # later, when the current state (including positions of old singlets) is gone.
        from bonds import V_ZERO_VALENCE, BOND_VALENCES # this might not work at top of file (recursive import); fix later ###@@@
        if self._modified_valence:
            self._modified_valence = False # do this first, so exceptions in the following only happen once
            if platform.atom_debug:
                print "atom_debug: update_valence starting to updating it for",self
            ## assert 0, "nim"###@@@
            # the only easy part is to kill singlets with illegal valences, and warn if those were not 0.
            zerokilled = badkilled = 0
            for sing in self.singNeighbors(): ###@@@ check out the other calls of this for code that might help us here...
                sv = sing.singlet_valence()
                if sv == V_ZERO_VALENCE:
                    sing.kill()
                    zerokilled += 1
                elif sv not in BOND_VALENCES:
                    # hmm... best to kill it and start over, I think, at least for now
                    sing.kill()
                    badkilled += 1
            if platform.atom_debug:
                print "atom_debug: update_valence %r killed %d zero-valence and %d bad-valence singlets" % \
                      (self, zerokilled, badkilled)
            ###e now fix things up... not sure exactly under what conds, or using what code (but see existing code mentioned above)
        elif platform.atom_debug:
            print "atom_debug: update_valence thinks it doesn't need to update it for",self
        return

    # ==

    def _changed_structure(self): #bruce 050627
        """[private method]
           This must be called by all low-level methods which change this atom's or singlet's element, atomtype,
        or set of bonds. It doesn't need to be called for changes to neighbor atoms, or for position changes,
        or for changes to chunk membership of this atom, or when this atom is killed. Calling it when not needed
        is ok, but might slow down later update functions by making them inspect this atom for important changes.
           All user events which can call this (indirectly) should also call env.post_event_updates() when they're done.
        """
        from env import _changed_structure_atoms # a dict
        _changed_structure_atoms[ id(self) ] = self
    
    # debugging methods (not yet fully tested; use at your own risk)
    
    def invalidate_everything(self): # for an atom, remove it and then readd it to its mol
        "debugging method"
        if len(self.molecule.atoms) == 1:
            print "warning: invalidate_everything on the only atom in mol %r\n" \
                  " might kill mol as a side effect!" % self.molecule
        # note: delatom invals self.bonds
        self.molecule.delatom(self) # note: this kills the mol if it becomes empty!
        self.molecule.addatom(self)
        return

    def update_everything(self):
        print "atom.update_everything() does nothing"
        return

    def Transmute(self, elt, force = False, atomtype = None): #bruce 050511 added atomtype arg  ###@@@ callers should pass atomtype
        ###@@@ review semantics/docstring for atomtype
        """[Public method, does all needed invalidations:]
        If this is a real atom, change its element type to elt (not Singlet),
        and its atomtype to the atomtype object passed,
        or if none is passed to elt's default atomtype or self's existing one (not sure which!###@@@),
        and replace its singlets (if any) with new ones (if any are needed)
        to match the desired number of bonds for the new element/atomtype.
        [As of 050511 before atomtype arg added, new atom type is old one if elt is same and
         old one already correct, else is default atom type. This needs improvement. ###@@@]
        Never remove real bonds, even if there are too many. Don't change
        bond lengths (except to replaced singlets) or atom positions.
        If there are too many real bonds for the new element type, refuse
        to transmute unless force is True.
        """
        ##print "transmute called, self.atomtype_iff_set is %r" % self.atomtype_iff_set()
        ##print "transmute called, elt atomtype = %r %r, self attrs for those are %r, %r" % (elt, atomtype, self.element, self.atomtype) 
        if self.element is Singlet:
            # does this ever happen? #k
            return
        if atomtype is None:
            if self.element is elt and len(self.bonds) == self.atomtype.numbonds:
                ## this code might be used if we don't always return due to bond valence: ###@@@
                ## atomtype = self.atomtype # use current atomtype if we're correct for it now, even if it's not default atomtype
                return # since elt and desired atomtype are same as now and we're correct
            else:
                atomtype = elt.atomtypes[0] # use default atomtype of elt
                ##print "transmute picking this dflt atomtype", atomtype 
        assert atomtype.element is elt
        # in case a specific atomtype was passed or the default one was chosen,
        # do another check to return early if requested change is a noop and our bond count is correct
        if self.element is elt and self.atomtype is atomtype and len(self.bonds) == atomtype.numbonds:
            # leave existing singlet positions alone in this case -- not sure this is best! ###@@@ #e review
            ##print "transmute returning since noop to change to these: %r %r" % (elt, atomtype)
            return
        # now we're committed to changing things
        nbonds = len(self.realNeighbors()) ###@@@ should also consider the bond-valence to them...
        if nbonds > atomtype.numbonds:
            # transmuting would break valence rules [###@@@ should instead use a different atomtype, if possible!]
            ###@@@ but a more normal case for using different one is if existing bond *valence* is too high...
            # note: this msg (or msg-class, exact text can vary) can get emitted too many times in a row.
            name = atomtype.fullname_for_msg()
            if force:
                msg = "warning: Transmute broke valence rules, made (e.g.) %s with %d bonds" % (name, nbonds)
                self.molecule.assy.w.history.message( orangemsg(msg) )
                # fall through
            else:
                msg = "warning: Transmute refused to make (e.g.) a %s with %d bonds" % (name, nbonds)
                self.molecule.assy.w.history.message( orangemsg(msg) )
                return
        # in all other cases, do the change (even if it's a noop) and also replace all singlets with 0 or more new ones
        self.direct_Transmute( elt, atomtype)
        return

    def direct_Transmute(self, elt, atomtype): #bruce 050511 split this out of Transmute
        """[Public method, does all needed invalidations:]
        With no checks except that the operation is legal,
        kill all singlets, change elt and atomtype
        (both must be provided and must match), and make new singlets.
        """
        for atm in self.singNeighbors():
            atm.kill() # (since atm is a singlet, this kill doesn't replace it with a singlet)
        self.mvElement(elt, atomtype)
        self.make_enough_singlets()
        return # from direct_Transmute

    def remake_singlets(self): #bruce 050511
        for atm in self.singNeighbors():
            atm.kill() # (since atm is a singlet, this kill doesn't replace it with a singlet)
        self.make_enough_singlets()
        return # from remake_singlets

    def make_enough_singlets(self): #bruce 050510 extending this to use atomtypes; all subrs still need to set singlet valence ####@@@@
        """[Public method, does all needed invalidations:]
        Add 0 or more singlets to this real atom, until it has as many bonds
        as its element and atom type prefers (but at most 4, since we use special-case
        code whose knowledge only goes that high). Add them in good positions
        relative to existing bonds (if any) (which are not changed, whether
        they are real or open bonds).
        """
        if len(self.bonds) >= self.atomtype.numbonds:
            return # don't want any more bonds
        # number of existing bonds tells how to position new open bonds
        # (for some n we can't make arbitrarily high numbers of wanted open
        # bonds; for other n we can; we can always handle numbonds <= 4)
        n = len(self.bonds)
        if n == 0:
            self.make_singlets_when_no_bonds()
        elif n == 1:
            self.make_singlets_when_1_bond()
        elif n == 2:
            self.make_singlets_when_2_bonds()
        elif n == 3:
            self.make_singlets_when_3_bonds() # (makes at most one open bond)
        else:
            pass # no code for adding open bonds to 4 or more existing bonds
        return

    # the make_singlets methods were split out of the private depositMode methods
    # (formerly called bond1 - bond4), to help implement atom.Transmute [bruce 041215]

    def make_singlets_when_no_bonds(self): #bruce 050511 partly revised this for atomtypes
        "[private method; see docstring for make_singlets_when_2_bonds]"
        # unlike the others, this was split out of oneUnbonded [bruce 041215]
        atype = self.atomtype
        if atype.bondvectors:
            r = atype.rcovalent
            pos = self.posn()
            mol = self.molecule
            for dp in atype.bondvectors:
                x = atom('X', pos+r*dp, mol)
                bond_atoms(self,x) ###@@@ set valence? or update it later?
        return
    
    def make_singlets_when_1_bond(self): # by josh, with some comments and mods by bruce
        "[private method; see docstring for make_singlets_when_2_bonds]"
        ## print "what the heck is this global variable named a doing here? %r" % (a,)
        ## its value is 0.85065080835203999; where does it come from? it hide bugs. ###@@@
        assert len(self.bonds) == 1
        assert not self.is_singlet()
        atype = self.atomtype
        if len(atype.quats): #bruce 041119 revised to support "onebond" elements
            # There is at least one other bond we should make (as open bond);
            # compute rq, which rotates this atom's bonding pattern (base and quats)
            # to match the existing bond. (If q is a quat that rotates base to another
            # bond vector (in std position), then rq + q - rq rotates r to another
            # bond vector in actual position.) [comments revised/extended by bruce 050614]
            pos = self.posn()
            s1pos = self.bonds[0].ubp(self)
            r = s1pos - pos # this points towards our real neighbor
            del s1pos # same varname used differently below
            rq = Q(r,atype.base)
            # if the other atom has any other bonds, align 60 deg off them
            # [new feature, bruce 050531: or 0 degrees, for both atomtypes sp2;
            #  should also look through sequences of sp atoms, but we don't yet do so]
            # [bruce 041215 comment: might need revision if numbonds > 4]
            a1 = self.bonds[0].other(self) # our real neighbor
            if len(a1.bonds)>1:
                # figure out how to line up one arbitrary bond from each of self and a1.
                # a2 = a neighbor of a1 other than self
                if self is a1.bonds[0].other(a1):
                    a2 = a1.bonds[1].other(a1)
                else:
                    a2 = a1.bonds[0].other(a1)
                a2pos = a2.posn()
                s1pos = pos+(rq + atype.quats[0] - rq).rot(r) # un-spun posn of one of our new singlets
                spin = twistor(r,s1pos-pos, a2pos-a1.posn())
                    # [bruce 050614 comments]
                    # spin is a quat that says how to twist self along r to line up
                    # the representative bonds perfectly (as projected into a plane perpendicular to r).
                    # I believe we'd get the same answer for either r or -r (since it's a quat, not an angle!).
                    # This won't work if a1 is sp (and a2 therefore projects right on top of a1 as seen along r);
                    # I don't know if it will have an exception or just give an arbitrary result. ##k
                    ##e This should be fixed to look through a chain of sp atoms to the next sp2 atom (if it finds one)
                    # and to know about pi system alignments even if that chain bends
                    # (though for long chains this won't matter much in practice).
                    # Note that we presently don't plan to store pi system alignment in the mmp file,
                    # which means it will be arbitrarily re-guessed for chains of sp atoms as needed.
                    # (I'm hoping other people will be as annoyed by that as I will be, and come to favor fixing it.)
                if atype.spX < 3 and a1.atomtype.spX < 3: # for now, same behavior for sp2 or sp atoms [revised 050630]
                    pass # no extra spin
                else:
                    spin = spin + Q(r, pi/3.0) # 60 degrees of extra spin
            else: spin = Q(1,0,0,0)
            mol = self.molecule
            if 1: # see comment below
                from debug_prefs import debug_pref, Choice # bruce 050614
                spinsign = debug_pref("spinsign", Choice([1,-1]))
            for q in atype.quats:
                # the following old code has the wrong sign on spin, thus causing bug 661: [fixed by bruce 050614]
                ##  q = rq + q - rq - spin
                # this would be the correct code:
                ##  q = rq + q - rq + spin
                # but as an example of how to use debug_pref, I'll put in code that can do it either way,
                # with the default pref value giving the correct behavior (moved just above, outside of this loop).
                q = rq + q - rq + spin * spinsign
                xpos = pos + q.rot(r)
                x = atom('X', xpos, mol)
                bond_atoms(self,x)
        return
        
    def make_singlets_when_2_bonds(self): #bruce 050511 updating this (and sister methods) for atom types
        """[private method for make_enough_singlets:]
        Given an atom with exactly 2 real bonds (and no singlets),
        see if it wants more bonds (due to its atom type),
        and make extra singlets if so, [###@@@ with what valence?]
        in good positions relative to the existing real bonds.
        Precise result might depend on order of existing bonds in self.bonds.
        """
        assert len(self.bonds) == 2 # usually both real bonds; doesn't matter
        atype = self.atomtype
        if atype.numbonds <= 2: return # optimization
        # rotate the atom to match the 2 bonds it already has
        # (i.e. figure out a suitable quat -- no effect on atom itself)
        pos = self.posn()
        s1pos = self.bonds[0].ubp(self)
        s2pos = self.bonds[1].ubp(self)
        r = s1pos - pos
        rq = Q(r,atype.base)
        # this moves the second bond to a possible position;
        # note that it doesn't matter which bond goes where
        q1 = rq + atype.quats[0] - rq
        b2p = q1.rot(r)
        # rotate it into place
        tw = twistor(r, b2p, s2pos - pos)
        # now for all the rest
        # (I think this should work for any number of new bonds [bruce 041215])
        mol = self.molecule
        for q in atype.quats[1:]:
            q = rq + q - rq + tw
            x = atom('X', pos+q.rot(r), mol)
            bond_atoms(self,x)
        return

    def make_singlets_when_3_bonds(self):
        "[private method; see docstring for make_singlets_when_2_bonds]"
        assert len(self.bonds) == 3
        atype = self.atomtype
        if atype.numbonds > 3:
            # bruce 041215 to fix a bug (just reported in email, no bug number):
            # Only do this if we want more bonds.
            # (But nothing is done to handle more than 4 desired bonds.
            #  Our element table has a comment claiming that its elements with
            #  numbonds > 4 are not yet used, but nothing makes me confident
            #  that comment is up-to-date.)
            pos = self.posn()
            s1pos = self.bonds[0].ubp(self)
            s2pos = self.bonds[1].ubp(self)
            s3pos = self.bonds[2].ubp(self)
            opos = (s1pos + s2pos + s3pos)/3.0
            try:
                assert vlen(pos-opos) > 0.001
                dir = norm(pos-opos)
            except:
                # [bruce 041215:]
                # fix unreported unverified bug (self at center of its neighbors):
                if platform.atom_debug:
                    print "atom_debug: fyi: self at center of its neighbors (more or less)",self,self.bonds
                dir = norm(cross(s1pos-pos,s2pos-pos)) ###@@@ need to test this!
            opos = pos + atype.rcovalent*dir
            mol = self.molecule
            x = atom('X', opos, mol)
            bond_atoms(self,x)
        return

    pass # end of class atom

atom = Atom # old name of that class -- must remain here until all code has been revised [bruce 050610]

def singlet_atom(singlet):
    "return the atom a singlet is bonded to, checking assertions"
    return singlet.singlet_neighbor()

def oneUnbonded(elem, assy, pos, atomtype = None): #bruce 050510 added atomtype option
    """Create one unbonded atom, of element elem
    and (if supplied) the given atomtype (otherwise the default atomtype for elem),
    at position pos, in its own new chunk.
    """
    # bruce 041215 moved this from chunk.py to chem.py, and split part of it
    # into the new atom method make_singlets_when_no_bonds, to help fix bug 131.
    mol = molecule(assy, 'bug') # name is reset below!
    atm = atom(elem.symbol, pos, mol)
    # bruce 041124 revised name of new mol, was gensym('Chunk.');
    # no need for gensym since atom key makes the name unique, e.g. C1.
    atm.set_atomtype_but_dont_revise_singlets(atomtype) # ok to pass None, type name, or type object; this verifies no change in elem
        # note, atomtype might well already be the value we're setting; if it is, this should do nothing
    mol.name = "Chunk-%s" % str(atm)
    atm.make_singlets_when_no_bonds() # notices atomtype
    assy.addmol(mol)
    return atm

# ==

# class Bond (etc) used to be defined here, but now it's in bonds.py. [bruce 050502]

from bonds import *  # only for the sake of other files which still import bond-related symbols from this file

# ==

# class molecule used to be defined here, but now it's in chunk.py. [bruce 041118]

# for the sake of other files which still look for class molecule in this file,
# we'll import it here (this might not work if done at the top of this file):

from chunk import *

# end of chem.py
