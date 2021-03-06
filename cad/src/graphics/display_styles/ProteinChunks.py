# Copyright 2008-2009 Nanorex, Inc.  See LICENSE file for details. 
"""
ProteinChunks.py -- defines I{Reduced Protein} display modes.

@author: Piotr
@version: $Id$ 
@copyright: 2008-2009 Nanorex, Inc.  See LICENSE file for details. 

History:

piotr 080623: First preliminary version of the protein display style.

piotr 080702: Implemented ribbons and cartoons.

piotr 080709: Making the file compliant with a Protein class.

piotr 080710: Minor fixes.

piotr 080723: Improved rotamer rendering speed.

piotr 080729: Code cleanup.

piotr 080804: Further code cleanup, adding docstrings.

piotr 080904: Added missing docstrings, prepared for review.

"""

import foundation.env as env

from geometry.VQT import V, norm, cross

from graphics.display_styles.displaymodes import ChunkDisplayMode

from graphics.drawing.CS_draw_primitives import drawcylinder
from graphics.drawing.CS_draw_primitives import drawpolycone_multicolor
from graphics.drawing.CS_draw_primitives import drawsphere
from graphics.drawing.CS_draw_primitives import drawline
from graphics.drawing.CS_draw_primitives import drawtriangle_strip

from Numeric import dot

from OpenGL.GL import glMaterialfv
from OpenGL.GL import GL_FRONT_AND_BACK
from OpenGL.GL import GL_AMBIENT_AND_DIFFUSE
from OpenGL.GL import glCallList
from OpenGL.GL import glGenLists
from OpenGL.GL import glNewList
from OpenGL.GL import glEndList
from OpenGL.GL import GL_COMPILE

import colorsys

from utilities.constants import blue, cyan, green, orange, red, white, gray

from utilities.constants import yellow

##### TODO: FIX: The *_worker functions are an internal part of the drawing code
# and should never be called directly from outside it. Doing so makes it
# difficult to modify the drawing code internally. All calls herein to
# drawsphere_worker or drawcylinder_worker should be replaced
# with equivalent calls to drawsphere or drawcylinder (and then if
# that's too much slower, those should be optimized in the drawing
# code, not here). [bruce 090304 comment]

from graphics.drawing.CS_workers import drawcylinder_worker
from graphics.drawing.CS_workers import drawsphere_worker

# Protein display style preferences
from utilities.prefs_constants import proteinStyle_prefs_key
from utilities.prefs_constants import proteinStyleColors_prefs_key
from utilities.prefs_constants import proteinStyleQuality_prefs_key
from utilities.prefs_constants import proteinStyleScaleFactor_prefs_key
from utilities.prefs_constants import proteinStyleScaling_prefs_key
from utilities.prefs_constants import proteinStyleHelixColor_prefs_key
from utilities.prefs_constants import proteinStyleStrandColor_prefs_key
from utilities.prefs_constants import proteinStyleCoilColor_prefs_key
from utilities.prefs_constants import proteinStyleSmooth_prefs_key

try:
    from OpenGL.GLE import gleSetJoinStyle
    from OpenGL.GLE import TUBE_NORM_PATH_EDGE 
    from OpenGL.GLE import TUBE_JN_ANGLE
    from OpenGL.GLE import TUBE_CONTOUR_CLOSED 
    from OpenGL.GLE import TUBE_JN_CAP 
except:
    print "Protein Chunks: GLE module can't be imported. Now trying _GLE"
    from OpenGL._GLE import gleSetJoinStyle
    from OpenGL._GLE import TUBE_NORM_PATH_EDGE 
    from OpenGL._GLE import TUBE_JN_ANGLE
    from OpenGL._GLE import TUBE_CONTOUR_CLOSED 
    from OpenGL._GLE import TUBE_JN_CAP 


# protein coloring styles    
PROTEIN_COLOR_SAME        = -1
PROTEIN_COLOR_CHUNK       = 0
PROTEIN_COLOR_CHAIN       = 1
PROTEIN_COLOR_ORDER       = 2
PROTEIN_COLOR_HYDROPATHY  = 3
PROTEIN_COLOR_POLARITY    = 4
PROTEIN_COLOR_ACIDITY     = 5
PROTEIN_COLOR_SIZE        = 6
PROTEIN_COLOR_CHARACTER   = 7
PROTEIN_COLOR_NOC         = 8
PROTEIN_COLOR_SECONDARY   = 9
PROTEIN_COLOR_SS_ORDER    = 10
PROTEIN_COLOR_BFACTOR     = 11
PROTEIN_COLOR_OCCUPANCY   = 12
PROTEIN_COLOR_ENERGY      = 13
PROTEIN_COLOR_CUSTOM      = 14

# protein display styles
PROTEIN_STYLE_CA_WIRE         = 1
PROTEIN_STYLE_CA_CYLINDER     = 2
PROTEIN_STYLE_CA_BALL_STICK   = 3
PROTEIN_STYLE_TUBE            = 4
PROTEIN_STYLE_LADDER          = 5
PROTEIN_STYLE_ZIGZAG          = 6
PROTEIN_STYLE_FLAT_RIBBON     = 7
PROTEIN_STYLE_SOLID_RIBBON    = 8
PROTEIN_STYLE_SIMPLE_CARTOONS = 9
PROTEIN_STYLE_FANCY_CARTOONS  = 10
PROTEIN_STYLE_PEPTIDE_TILES   = 11

# I plan to change the following color schemes so they use less
# intrusive colors (maybe just blue-to-white-to-red scale instad
# of red-green-blue spectrum). piotr 080902

# coloring according to amino acid hydropathy scale (Kyte-Doolittle)
AA_COLORS_HYDROPATHY = { 
    "ALA" : orange,
    "ARG" : blue,
    "ASN" : blue,
    "ASP" : blue,
    "CYS" : orange,
    "GLN" : blue,
    "GLU" : blue,
    "GLY" : green,
    "HIS" : blue,
    "ILE" : red,
    "LEU" : red,
    "LYS" : blue,
    "MET" : orange,
    "PHE" : orange,
    "PRO" : cyan,
    "SER" : green,
    "THR" : green,
    "TRP" : green,
    "TYR" : cyan,
    "VAL" : red }

# coloring according to amino acid polarity
AA_COLORS_POLARITY = { 
    "ALA" : red,
    "ARG" : green,
    "ASN" : green,
    "ASP" : green,
    "CYS" : green,
    "GLN" : green,
    "GLU" : green,
    "GLY" : red,
    "HIS" : green,
    "ILE" : red,
    "LEU" : red,
    "LYS" : green,
    "MET" : red,
    "PHE" : red,
    "PRO" : red,
    "SER" : green,
    "THR" : green,
    "TRP" : red,
    "TYR" : red,
    "VAL" : red }

# coloring according to amino acid acidity

AA_COLORS_ACIDITY = { 
    "ALA" : green,
    "ARG" : blue,
    "ASN" : green,
    "ASP" : red,
    "CYS" : green,
    "GLN" : green,
    "GLU" : red,
    "GLY" : green,
    "HIS" : blue,
    "ILE" : green,
    "LEU" : green,
    "LYS" : blue,
    "MET" : green,
    "PHE" : green,
    "PRO" : green,
    "SER" : green,
    "THR" : green,
    "TRP" : green,
    "TYR" : green,
    "VAL" : green }

def compute_spline(data, idx, t):
    """
    Implements a Catmull-Rom spline. Interpolates between data[idx] and 
    data[idx+1] using data[idx-1], data[idx], data[idx+1] and data[idx+2]
    points. 

    @param data: list of data points to interpolate. it needs to have at least
    data points, otherwise will cause an exception
    
    @param idx: index of data points to be interpolated between
    @type idx: int
    
    @param t: interpolation ratio (0.0 <= t <= 1.0)
    @type t: float 
    
    @note: this method is basically identical to the one in DnaCylinderChunks,
    so it should be splitted out from here and moved to another, more general
    file
    
    """
    t2 = t*t
    t3 = t2*t
    x0 = data[idx-1]
    x1 = data[idx]
    x2 = data[idx+1]
    x3 = data[idx+2]
    res = 0.5 * ((2.0 * x1) +
                 t * (-x0 + x2) +
                 t2 * (2.0 * x0 - 5.0 * x1 + 4.0 * x2 - x3) +
                 t3 * (-x0 + 3.0 * x1 - 3.0 * x2 + x3))
    return res

def make_tube(points, colors, radii, dpos, resolution=3):
    """
    Converts a polycylinder tube into a smooth, curved tube using spline 
    interpolation of points, colors and radii.
    
    If there is not enough data points, returns the original lists.
    Thus, it can be used in the following way:
    
    pos, col, rad, dpos = make_tube(pos, col, rad, dpos, resolution)

    Assumes that len(points) == len(colors) == len(radii)
    
    @param points: consecutive points to be interpolated
    @type points: list of V or list of float[3]
    
    @param colors: colors corresponding to the points
    @type colors: list of colors
    
    @param radii: radii correspoding to individual points
    @type radii: list of radii
    
    @param dpos: dpos vectors correspoding to individual points
    @type dpos: list of dpos vectors
    
    @param resolution: specifies a number of points intepolated in-between
    two consecutive input points
    @type resolution: integer
    
    @return: tuple of interpolated (points, colors, radii, dpos)
    """
    n = len(points)
    if n > 3:
        new_points = []
        new_colors = []
        new_radii = []
        new_dpos = []
        o = 1
        ir = 1.0/float(resolution)
        for p in range (1, n-2):
            start_spline = 0
            end_spline = int(resolution) #@@@
            if p == 1:
                start_spline = int(resolution / 2 - 1)
            if p == n-3:
                end_spline = int(resolution / 2 + 1)
            for m in range (start_spline, end_spline):
                t = ir * m
                sp = compute_spline(points, p, t)
                sc = compute_spline(colors, p, t)
                sr = compute_spline(radii, p, t)
                sd = compute_spline(dpos, p, t)
                new_points.append(sp)
                new_colors.append(sc)
                new_radii.append(sr)
                new_dpos.append(sd)

        t = ir * (m + 1)
        sp = compute_spline(points, p, t)
        sc = compute_spline(colors, p, t)
        sr = compute_spline(radii, p, t)
        sd = compute_spline(dpos, p, t)

        new_points.append(sp)
        new_colors.append(sc)
        new_radii.append(sr)
        new_dpos.append(sd)
        return (new_points, new_colors, new_radii, new_dpos)
    else:
        return (points, colors, radii, dpos)

# These two methods are identical to these found in DnaCylinderChunks.

def get_rainbow_color(hue, saturation, value):
    """
    Gets a color of a hue range limited to 0 - 0.667 (red - blue)
    
    @param hue: color hue (0..1)
    @type hue: float
    
    @param saturation: color saturation (0..1)
    @type saturation: float
    
    @param value: color value (0..1)
    @type value: float
    
    @return: color for given (h,s,v) 
    
    """

    hue = 0.666 * (1.0 - hue)
    if hue < 0.0: 
        hue = 0.0
    if hue > 0.666: 
        hue = 0.666
    return colorsys.hsv_to_rgb(hue, saturation, value)

def get_rainbow_color_in_range(pos, count, saturation, value):
    """
    Gets a color of a hue range limited to 0 - 0.667 (red - blue color range)
    correspoding to a "pos" value from (0..count) range.
    
    @param pos: position in (0..count range) 
    @type pos: integer
    
    @param count: limits the range of allowable values
    @type count: integer
    
    @param saturation: color saturation (0..1)
    @type saturation: float
    
    @param value: color value (0..1)
    @type value: float
    
    @return: color for given (pos, s, v) 
    """
    if count > 1: 
        count -= 1
    hue = float(pos)/float(count)        
    if hue < 0.0: 
        hue = 0.0
    if hue > 1.0: 
        hue = 1.0
    return get_rainbow_color(hue, saturation, value)

class ProteinChunks(ChunkDisplayMode):
    """
    This class implements drawing of reduced representations of protein 
    structures. General class structure is copied from DnaCylinderChunks.py
    """

    # mmp_code must be a unique 3-letter code, distinct from the values in 
    # constants.dispNames or in other display modes
    mmp_code = 'pro'  
    disp_label = 'Protein' # label for statusbar fields, menu text, etc.
    featurename = "Set Display Protein"

    # Pretty sure Bruce's intention is to define icons for subclasses
    # of ChunkDisplayMode here, not in mticon_names[] and hideicon_names[] 
    # in chunks.py. Ask him to be sure. Mark 2008-02-12
    icon_name = "modeltree/Protein.png"
    hide_icon_name = "modeltree/Protein-hide.png"

    def _get_aa_color(self, chunk, pos, n_pos, sec, aa, c_sec, n_sec):
        """
        Returns an amino acid color according to the current color mode.

        @param chunk: Protein chunk
        @type chunk: Chunk with protein attribute available
        
        @param pos: residue sequence position
        @type pos: int
        
        @param n_pos: length of the protein sequence
        @type n_pos: int
        
        @param sec: secondary structure type (SS_HELIX, SS_STRAND, or SS_COIL)
        @type sec: int
        
        @param aa: amino acid name (3-letter code)
        @type aa: string 
        
        @param c_sec: index of secondary structure element
        @type c_sec: int
        
        @param n_sec: number of secondary structure elements
        @type n_sec: int
        
        @return: residue color according to curreny color mode, or gray
        if wrong parameters were specified
        """
        color = gray

        if self.proteinStyleColors == PROTEIN_COLOR_ORDER:
            # Color according to order of amino acids.
            color = get_rainbow_color_in_range(pos, n_pos, 1.0, 1.0)
        elif self.proteinStyleColors == PROTEIN_COLOR_CHUNK:
            # Assign chunk color
            if chunk.color:
                color = chunk.color
            pass
        elif self.proteinStyleColors == PROTEIN_COLOR_POLARITY:         
            # Color according to amino acid polarity.
            if aa in AA_COLORS_POLARITY:
                color = AA_COLORS_POLARITY[aa]
        elif self.proteinStyleColors == PROTEIN_COLOR_ACIDITY:  
            # Color according to amino acid acidity.
            if aa in AA_COLORS_ACIDITY:
                color = AA_COLORS_ACIDITY[aa]
        elif self.proteinStyleColors == PROTEIN_COLOR_HYDROPATHY:
            # Color according to amino acid hydropathy index.
            if aa in AA_COLORS_HYDROPATHY:
                color = AA_COLORS_HYDROPATHY[aa]
        elif self.proteinStyleColors == PROTEIN_COLOR_SECONDARY:
            # Color according to protein secondary structure.
            if sec == 1:
                color = self.proteinStyleHelixColor
            elif sec == 2:
                color = self.proteinStyleStrandColor
            else:
                color = self.proteinStyleCoilColor
        elif self.proteinStyleColors == PROTEIN_COLOR_SS_ORDER:
            # Color according to the order of secondary structure elements.
            if sec > 0:
                color = get_rainbow_color_in_range(c_sec, n_sec-1, 1.0, 1.0)
            else:
                color = self.proteinStyleCoilColor

        return color

    def drawchunk(self, glpane, chunk, memo, highlighted):
        """
        Draws a reduced representation of a protein chunk. This method is called
        per chunk, but in fact it draws individual secondary structure elements, 
        i.e. consecutive part of the protein chain composed of a single type 
        of secondary structure.        
        """

        # Note: If the protein model is going to be re-factored in the future
        # so that every individual chunk corresponds to a single, homogenoeous
        # secondary structure element, this method could be used without 
        # much changes.
        
        # Retrieve parameters from memo
        structure, total_length, ca_list, n_sec = memo

        # Get display style settings
        style = self.proteinStyle
        scaleFactor = self.proteinStyleScaleFactor
        resolution = self.proteinStyleQuality
        scaling = self.proteinStyleScaling
        smooth = self.proteinStyleSmooth

        # Set nice joint style for gle Polycone primitives.
        gleSetJoinStyle(TUBE_JN_ANGLE | TUBE_NORM_PATH_EDGE \
                        | TUBE_JN_CAP | TUBE_CONTOUR_CLOSED ) 

        # Iterate over consecutive secondary structure elements.
        current_sec = 0
        for sec, secondary in structure:
            # Number of atoms in SS element including dummy atoms.
            n_atoms = len(sec) 
            # The length should be at least 3.
            if n_atoms >= 3:
                # Alpha carbon trace styles. Simple but fast.
                # Use either lines or cylinder to connect consecutive alpha carbons.
                if style == PROTEIN_STYLE_CA_WIRE or \
                   style == PROTEIN_STYLE_CA_CYLINDER or \
                   style == PROTEIN_STYLE_CA_BALL_STICK:
                    for n in range( 1, n_atoms-1 ):
                        pos0, ss0, aa0, idx0, dpos0, cbpos0 = sec[n - 1]
                        pos1, ss1, aa1, idx1, dpos1, cbpos1 = sec[n]
                        pos2, ss2, aa2, idx2, dpos2, cbpos2 = sec[n + 1]
                        color = self._get_aa_color(chunk, 
                                                   idx1, 
                                                   total_length, 
                                                   ss1, 
                                                   aa1,
                                                   current_sec,
                                                   n_sec)
                        if style == PROTEIN_STYLE_CA_WIRE:
                            # Wire - use line.
                            if pos0:
                                drawline(color, 
                                         pos1 + 0.5 * (pos0 - pos1), 
                                         pos1,
                                         width=5,
                                         isSmooth=True)
                                
                            if pos2:
                                drawline(color, 
                                         pos1, 
                                         pos1 + 0.5 * (pos2 - pos1),
                                         width=5, 
                                         isSmooth=True)
                        else:
                            # Cylinder and B&S - use cylinders.
                            if pos0:
                                drawcylinder(color, 
                                             pos1 + 0.5 * (pos0 - pos1), 
                                             pos1,
                                             0.25 * scaleFactor, 
                                             capped=1)

                            if style == PROTEIN_STYLE_CA_BALL_STICK:
                                drawsphere(color, pos1, 0.5 * scaleFactor, 2)
                            else:
                                drawsphere(color, pos1, 0.25 * scaleFactor, 2)

                            if pos2:
                                drawcylinder(color, 
                                             pos1, 
                                             pos1 + 0.5 * (pos2 - pos1),
                                             0.25 * scaleFactor, 
                                             capped=1)

                elif style == PROTEIN_STYLE_PEPTIDE_TILES:
                    # Peptide tiles: not implemented yet.
                    # piotr 080903: this option should be removed
                    # from Protein Display Style PM. 
                    """
                    for n in range( 1, n_atoms-2 ):
                        pos0, ss0, aa0, idx0, dpos0, cbpos0 = sec[n - 1]
                        pos1, ss1, aa1, idx1, dpos1, cbpos1 = sec[n]
                        color = self._get_aa_color(chunk, 
                                                   idx1, 
                                                   total_length, 
                                                   ss1, 
                                                   aa1,
                                                   current_sec,
                                                   n_sec)
                        tri = []
                        nor = []
                        col = []
                    """

                elif style == PROTEIN_STYLE_TUBE or \
                     style == PROTEIN_STYLE_LADDER or \
                     style == PROTEIN_STYLE_ZIGZAG or \
                     style == PROTEIN_STYLE_FLAT_RIBBON or \
                     style == PROTEIN_STYLE_SOLID_RIBBON or \
                     style == PROTEIN_STYLE_SIMPLE_CARTOONS or \
                     style == PROTEIN_STYLE_FANCY_CARTOONS:
                    
                    # All of these styles use the same interpolated cubic spline
                    # that connects alpha carbon atoms.

                    # The following lists store positions, colors, radii and 
                    # peptide bond vectors for consecutive main chain 
                    # positions.
                    
                    tube_pos = []
                    tube_col = []
                    tube_rad = []
                    tube_dpos = []

                    # Fill-in the position, color, radius and peptide position
                    # lists.
                    
                    for n in range( 2, n_atoms-2 ):
                        pos00, ss00, a00, idx00, dpos00, cbpos00 = sec[n - 2]
                        pos0, ss0, aa0, idx0, dpos0, cbpos0 = sec[n - 1]
                        pos1, ss1, aa1, idx1, dpos1, cbpos1 = sec[n]
                        pos2, ss2, aa2, idx2, dpos2, cbpos2 = sec[n + 1]
                        pos22, ss22, aa22, idx22, dpos22, cbpos22 = sec[n + 2]

                        color = self._get_aa_color(chunk, 
                                                   idx1, 
                                                   total_length, 
                                                   ss1, 
                                                   aa1,
                                                   current_sec,
                                                   n_sec)

                        rad = 0.25 * scaleFactor
                        if style == PROTEIN_STYLE_TUBE and \
                           scaling == 1:
                            if secondary > 0: 
                                rad *= 2.0

                        if n == 2:
                            if pos0:
                                tube_pos.append(pos00)
                                tube_col.append(V(color))
                                tube_rad.append(rad)
                                tube_dpos.append(dpos1)
                                tube_pos.append(pos0)
                                tube_col.append(V(color))
                                tube_rad.append(rad)
                                tube_dpos.append(dpos1)

                        if style == PROTEIN_STYLE_LADDER:
                            drawcylinder(color, pos1, cbpos1, rad * 0.75)
                            drawsphere(color, cbpos1, rad * 1.5, 2)

                        if pos1:
                            tube_pos.append(pos1)
                            tube_col.append(V(color))
                            tube_rad.append(rad)
                            tube_dpos.append(dpos1)

                        if n == n_atoms - 3:
                            if pos2:
                                tube_pos.append(pos2)
                                tube_col.append(V(color))
                                tube_rad.append(rad)
                                tube_dpos.append(dpos1)
                                tube_pos.append(pos22)
                                tube_col.append(V(color))
                                tube_rad.append(rad)
                                tube_dpos.append(dpos1)

                    # For smoothed helices we need to add virtual atoms
                    # located approximately at the centers of peptide bonds
                    # but slightly moved away from the helix axis.

                    new_tube_pos = []
                    new_tube_col = []
                    new_tube_rad = []
                    new_tube_dpos = []
                    if smooth and \
                       secondary == 1:
                        for p in range(len(tube_pos)):
                            new_tube_pos.append(tube_pos[p])
                            new_tube_col.append(tube_col[p])
                            new_tube_rad.append(tube_rad[p])                        
                            new_tube_dpos.append(tube_dpos[p])

                            if p > 1 and p < len(tube_pos) - 3:
                                pv = tube_pos[p-1] - tube_pos[p]
                                nv = tube_pos[p+2] - tube_pos[p+1]
                                mi = 0.5 * (tube_pos[p+1] + tube_pos[p])
                                # The coefficient below was handpicked to make  
                                # the helices approximately round.
                                mi -= 0.75 * norm(nv+pv)                            
                                new_tube_pos.append(mi)
                                new_tube_col.append(0.5*(tube_col[p]+tube_col[p+1]))
                                new_tube_rad.append(0.5*(tube_rad[p]+tube_rad[p+1]))                        
                                new_tube_dpos.append(0.5*(tube_dpos[p]+tube_dpos[p+1]))

                        tube_pos = new_tube_pos
                        tube_col = new_tube_col
                        tube_rad = new_tube_rad
                        tube_dpos = new_tube_dpos

                    if secondary != 1 or \
                       style != PROTEIN_STYLE_SIMPLE_CARTOONS:
                        tube_pos, tube_col, tube_rad, tube_dpos = make_tube(
                            tube_pos, 
                            tube_col, 
                            tube_rad, 
                            tube_dpos, 
                            resolution=resolution)

                        if style == PROTEIN_STYLE_ZIGZAG or \
                           style == PROTEIN_STYLE_FLAT_RIBBON or \
                           style == PROTEIN_STYLE_SOLID_RIBBON or \
                           style == PROTEIN_STYLE_SIMPLE_CARTOONS or \
                           style == PROTEIN_STYLE_FANCY_CARTOONS:

                            last_pos = None
                            last_width = 1.0
                            reset = False

                            # Find SS element widths and determine width increment.
                            if secondary == 0:
                                # Coils have a constant width.
                                width = scaleFactor * 0.1
                                dw = 0.0
                            elif secondary == 1:
                                # Helices expand and shrink at the ends.
                                width = scaleFactor * 0.1
                                dw = (1.0 * scaleFactor) / (resolution - 3)
                            else:
                                # Strands just shrink at the C-terminal end.
                                width = scaleFactor * 1.0
                                dw = (1.5 * scaleFactor) / ((1.5 * resolution) - 3)
                                
                            if style == PROTEIN_STYLE_FLAT_RIBBON or \
                               style == PROTEIN_STYLE_SOLID_RIBBON or \
                               style == PROTEIN_STYLE_SIMPLE_CARTOONS or \
                               style == PROTEIN_STYLE_FANCY_CARTOONS:

                                tri_arr0 = []
                                nor_arr0 = []
                                col_arr0 = []

                                if style == PROTEIN_STYLE_SOLID_RIBBON or \
                                   style == PROTEIN_STYLE_SIMPLE_CARTOONS or \
                                   style == PROTEIN_STYLE_FANCY_CARTOONS: 

                                    tri_arr1 = []
                                    nor_arr1 = []
                                    col_arr1 = []

                                    tri_arr2 = []
                                    nor_arr2 = []
                                    col_arr2 = []

                                    tri_arr3 = []
                                    nor_arr3 = []
                                    col_arr3 = []

                            # This should be done faster... are individual 
                            # copies of the tube positions really necessary?
                            
                            ###from copy import copy
                            ###new_tube_dpos = [dpos for dpos in tube_dpos]

                            # Auxiliary tube positions for FANCY_CARTOON helices.
                            tube_pos_left = [tube_pos[0]]
                            tube_pos_right = [tube_pos[0]]

                            for n in range(1, len(tube_pos)-1):
                                pos = tube_pos[n]

                                col = tube_col[n][0]
                                col2 = tube_col[n+1][0]
                                if last_pos:
                                    next_pos = tube_pos[n+1]
                                    dpos1 = last_width * tube_dpos[n-1]
                                    dpos2 = width * tube_dpos[n]
                                    ddpos = dpos1-dpos2
                                    if reset:
                                        dpos1 = dpos2
                                        reset = False

                                    if self.proteinStyle == PROTEIN_STYLE_ZIGZAG:
                                        # The line calls below draw an outline 
                                        # of ribbon triangles. 
                                        drawline(col, 
                                                 last_pos-dpos1, 
                                                 pos-dpos2, 
                                                 width=3)
                                        drawline(col, 
                                                 last_pos+dpos1, 
                                                 pos+dpos2, 
                                                 width=3)
                                        drawline(col, 
                                                 last_pos-dpos1, 
                                                 pos+dpos2, 
                                                 width=1)
                                        drawline(col, 
                                                 pos-dpos2, 
                                                 pos+dpos2, 
                                                 width=1)
                                        drawline(col, 
                                                 last_pos-dpos1, 
                                                 last_pos+dpos1, 
                                                 width=1)

                                    if self.proteinStyle == PROTEIN_STYLE_FLAT_RIBBON:
                                        # Flat ribbon only draws a single 
                                        # layer of triangles.
                                        if pos != last_pos:

                                            nvec1 = norm(cross(dpos1, pos-last_pos))
                                            if next_pos != pos:
                                                nvec2 = norm(cross(dpos2, next_pos-pos))
                                            else:
                                                nvec2 = nvec1

                                            nor_arr0.append(nvec1)
                                            nor_arr0.append(nvec1)
                                            nor_arr0.append(nvec2)
                                            nor_arr0.append(nvec2)

                                            tri_arr0.append(last_pos-dpos1) 
                                            tri_arr0.append(last_pos+dpos1)
                                            tri_arr0.append(pos-dpos2) 
                                            tri_arr0.append(pos+dpos2)

                                            col_arr0.append(col)
                                            col_arr0.append(col)
                                            col_arr0.append(col2)
                                            col_arr0.append(col2)

                                    if self.proteinStyle == PROTEIN_STYLE_SOLID_RIBBON or \
                                       self.proteinStyle == PROTEIN_STYLE_SIMPLE_CARTOONS or \
                                       self.proteinStyle == PROTEIN_STYLE_FANCY_CARTOONS:
                                        # These three styles are similar. 
                                        # The difference between "solid ribbon" 
                                        # and "fancy cartoons" is that the 
                                        # cartoons mode uses rounded edges
                                        # on helices, while solid ribbon uses
                                        # just a flat edge. The difference between
                                        # simple cartoons and fancy cartoons or
                                        # solid ribbon is that the simple cartoons
                                        # mode use simple straight cylinders to
                                        # represent alpha helices.
                                        if secondary > 0:
                                            
                                            # Prepare triangle strips positioned
                                            # along interpolated curve connecting
                                            # consecutive alpha carbon atoms
                                            
                                            col3 = col4 = V(gray)

                                            if pos != last_pos:

                                                nvec1 = norm(cross(dpos1, pos-last_pos))
                                                if next_pos != pos:
                                                    nvec2 = norm(cross(dpos2, next_pos-pos))
                                                else:
                                                    nvec2 = nvec1

                                                nor_arr0.append(nvec1)
                                                nor_arr0.append(nvec1)
                                                nor_arr0.append(nvec2)
                                                nor_arr0.append(nvec2)

                                                if self.proteinStyle == PROTEIN_STYLE_FANCY_CARTOONS:
                                                    dn1 = 0.15 * nvec1 * scaleFactor
                                                    dn2 = 0.15 * nvec2 * scaleFactor
                                                else:
                                                    dn1 = 0.15 * nvec1 * scaleFactor
                                                    dn2 = 0.15 * nvec2 * scaleFactor

                                                tri_arr0.append(last_pos - dpos1 - dn1) 
                                                tri_arr0.append(last_pos + dpos1 - dn1)
                                                tri_arr0.append(pos - dpos2 - dn2) 
                                                tri_arr0.append(pos + dpos2 - dn2)

                                                tube_pos_left.append(last_pos - dpos1)
                                                tube_pos_right.append(last_pos + dpos1)
                                                
                                                col_arr0.append(col)
                                                col_arr0.append(col)
                                                col_arr0.append(col2)
                                                col_arr0.append(col2)

                                                nor_arr1.append(nvec1)
                                                nor_arr1.append(nvec1)
                                                nor_arr1.append(nvec2)
                                                nor_arr1.append(nvec2)

                                                tri_arr1.append(last_pos - dpos1 + dn1) 
                                                tri_arr1.append(last_pos + dpos1 + dn1)
                                                tri_arr1.append(pos - dpos2 + dn2) 
                                                tri_arr1.append(pos + dpos2 + dn2)

                                                if secondary == 1:
                                                    col_arr1.append(
                                                        0.5 * col + 0.5 * V(white))
                                                    col_arr1.append(
                                                        0.5 * col + 0.5 * V(white))
                                                    col_arr1.append(
                                                        0.5 * col2 + 0.5 * V(white))
                                                    col_arr1.append(
                                                        0.5 * col2 + 0.5 * V(white))

                                                else:
                                                    col_arr1.append(col)
                                                    col_arr1.append(col)
                                                    col_arr1.append(col2)
                                                    col_arr1.append(col2)

                                                nor_arr2.append(-dpos1)
                                                nor_arr2.append(-dpos1)
                                                nor_arr2.append(-dpos2)
                                                nor_arr2.append(-dpos2)

                                                tri_arr2.append(last_pos - dpos1 - dn1) 
                                                tri_arr2.append(last_pos - dpos1 + dn1)
                                                tri_arr2.append(pos - dpos2 - dn2) 
                                                tri_arr2.append(pos - dpos2 + dn2)

                                                col_arr2.append(col3)
                                                col_arr2.append(col3)
                                                col_arr2.append(col4)
                                                col_arr2.append(col4)

                                                nor_arr3.append(-dpos1)
                                                nor_arr3.append(-dpos1)
                                                nor_arr3.append(-dpos2)
                                                nor_arr3.append(-dpos2)

                                                tri_arr3.append(last_pos + dpos1 - dn1) 
                                                tri_arr3.append(last_pos + dpos1 + dn1)
                                                tri_arr3.append(pos + dpos2 - dn2) 
                                                tri_arr3.append(pos + dpos2 + dn2)

                                                col_arr3.append(col3)
                                                col_arr3.append(col3)
                                                col_arr3.append(col4)
                                                col_arr3.append(col4)


                                last_pos = pos
                                last_width = width

                                if secondary == 1:
                                    if n > len(tube_pos) - resolution:
                                        width -= dw 
                                    elif width < 1.0 * scaleFactor:
                                        width += dw

                                if secondary == 2:
                                    if n == len(tube_pos) - 1.5 * resolution:
                                        width = scaleFactor * 1.6
                                        reset = True
                                    if n > len(tube_pos) - 1.5 * resolution:
                                        width -= dw 

                                ###new_tube_dpos[n] = dpos1
                            # Append dummy positions at both ends for
                            # GLE polycone rendering.
                            tube_pos_left.append(tube_pos[-2])
                            tube_pos_right.append(tube_pos[-2])
                            tube_pos_left.append(tube_pos[-1])
                            tube_pos_right.append(tube_pos[-1])
                        
                        if self.proteinStyle == PROTEIN_STYLE_FLAT_RIBBON:
                            # Note: the "-2" opacity component in the color list
                            # tells the ColorSorter that this is a multi color
                            # object and "color material" should be enabled
                            # while rendering it.
                            drawtriangle_strip(
                                [1.0,1.0,0.0,-2.0], tri_arr0, nor_arr0, col_arr0)

                        if self.proteinStyle == PROTEIN_STYLE_SOLID_RIBBON or \
                           self.proteinStyle == PROTEIN_STYLE_SIMPLE_CARTOONS or \
                           self.proteinStyle == PROTEIN_STYLE_FANCY_CARTOONS:
                            if secondary == 0:
                                drawpolycone_multicolor(
                                    [0,0,0,-2], tube_pos, tube_col, tube_rad)
                            else:
                                if (secondary == 1 and 
                                    self.proteinStyle == PROTEIN_STYLE_SOLID_RIBBON) or \
                                   secondary == 2:
                                    drawtriangle_strip(
                                        [1.0,1.0,0.0,-2.0], 
                                        tri_arr0, nor_arr0, col_arr0)
                                    drawtriangle_strip(
                                        [1.0,1.0,0.0,-2.0], 
                                        tri_arr1, nor_arr1, col_arr1)
                                    drawtriangle_strip(
                                        [1.0,1.0,0.0,-2.0], 
                                        tri_arr2, nor_arr2, col_arr2)
                                    drawtriangle_strip([1.0,1.0,0.0,-2.0], 
                                                       tri_arr3, nor_arr3, col_arr3)
                                    
                                    # Fill in the strand N-terminal end.
                                    quad_tri = []
                                    quad_nor = []
                                    quad_col = []
                                    quad_tri.append(tri_arr2[0])
                                    quad_tri.append(tri_arr3[0])
                                    quad_tri.append(tri_arr2[1])
                                    quad_tri.append(tri_arr3[1])
                                    quad_nor.append(nor_arr2[0])
                                    quad_nor.append(nor_arr3[0])
                                    quad_nor.append(nor_arr2[1])
                                    quad_nor.append(nor_arr3[1])
                                    quad_col.append(col_arr2[0])
                                    quad_col.append(col_arr3[0])
                                    quad_col.append(col_arr2[1])
                                    quad_col.append(col_arr3[1])
                                    drawtriangle_strip(
                                        [1.0,1.0,1.0,-2.0], quad_tri, quad_nor,quad_col)

                                if (secondary == 1 and self.proteinStyle == PROTEIN_STYLE_FANCY_CARTOONS):
                                    # Draw smooth tubes at the edges of the
                                    # helices. 
                                    drawtriangle_strip(
                                        [1.0,1.0,0.0,-2.0], 
                                        tri_arr0, nor_arr0, col_arr0)
                                    drawtriangle_strip([
                                        1.0,1.0,0.0,-2.0], 
                                        tri_arr1, nor_arr1, col_arr1)
                                    drawpolycone_multicolor(
                                        [0,0,0,-2], 
                                        tube_pos_left, tube_col, tube_rad)
                                    drawpolycone_multicolor(
                                        [0,0,0,-2], 
                                        tube_pos_right, tube_col, tube_rad)
                                    
                    if (secondary == 1 and style == PROTEIN_STYLE_SIMPLE_CARTOONS):
                        drawcylinder(tube_col[0][0], 
                                     tube_pos[1], 
                                     tube_pos[-3], 2.5, capped=1)

                    if style == PROTEIN_STYLE_LADDER or \
                       style == PROTEIN_STYLE_TUBE:
                        # Draw a smooth tube connecting alpha carbon positions.
                        drawpolycone_multicolor([0,0,0,-2], 
                                                tube_pos, 
                                                tube_col, 
                                                tube_rad)

            # Increase secondary structure element counter (for coloring
            # by "secondary structure elements order").
            current_sec += 1

    def drawchunk_selection_frame(self, glpane, chunk, selection_frame_color, memo, highlighted):
        """
        Given the same arguments as drawchunk, plus selection_frame_color, 
        draw the chunk's selection frame.

        (Drawing the chunk itself as well would not cause drawing errors
        but would presumably be a highly undesirable slowdown, especially if
        redrawing after selection and deselection is optimized to not have to
        redraw the chunk at all.)

        @note: in the initial implementation of the code that calls this method,
        the highlighted argument might be false whether or not we're actually
        hover-highlighted. And if that's fixed, then just as for drawchunk, 
        we might be called twice when we're highlighted, once with 
        highlighted = False and then later with highlighted = True.
        
        This method seems to be obsolete. piotr 080803
        """
        self.drawchunk(self, glpane, chunk, selection_frame_color, memo, highlighted)
        return

    def drawchunk_realtime(self, glpane, chunk, highlighted=False):
        """
        Draws protein rotamers. 
        
        This is a hack for having atomistic and reduced models displayed
        simultenaously. This method creates its own display list to store
        "expanded" rotamers drawn as tubes. Different colors can be assigned
        to individual rotamers. 
        
        piotr 080801: Backbone atoms are omitted.
        
        """
        # Draw rotamers using a display list. Create it if necessary.

        # Note: the only command that uses this feature is Edit
        # Rotamers. The purpose of this feature is to have 
        # an atomistic-like display style on top of a reduced
        # representation.
        
        # Note: this implementation may have bugs. The major problem
        # is that the display list is never explicitly deleted,
        # so using this feature may introduce memory leaks (I am
        # not sure about that).  
        
        # The rotamer is rendered using a style resembling "Tubes".
        
        if chunk.protein:
            if highlighted:
                # If highlighhting, just draw everything without using
                # the display list.
                color = yellow
                aa_list = chunk.protein.get_amino_acids()
                glMaterialfv(
                    GL_FRONT_AND_BACK, 
                    GL_AMBIENT_AND_DIFFUSE, 
                    color[:3])                    
                for aa in aa_list:
                    if chunk.protein.is_expanded(aa):
                        aa_atom_list = aa.get_side_chain_atom_list()
                        for atom in aa_atom_list:
                            pos1 = atom.posn()
                            drawsphere_worker((pos1, 0.2, 1, 1))
                            for bond in atom.bonds:
                                if atom == bond.atom1:
                                    if bond.atom2 in aa_atom_list:
                                        pos2 = bond.atom2.posn()
                                        drawcylinder_worker((
                                            pos1, 
                                            pos1 + 0.5*(pos2 - pos1), 
                                            0.2, 
                                            True))
                                else: 
                                    if bond.atom1 in aa_atom_list:
                                        pos2 = bond.atom1.posn()
                                        drawcylinder_worker((
                                            pos1, 
                                            pos1 + 0.5*(pos2 - pos1), 
                                            0.2, 
                                            True))
            else:
                """
                from PyQt4.Qt import QFont, QString, QColor, QFontMetrics
                labelFont = QFont( QString("Lucida Grande"), 16)
                fm = QFontMetrics(labelFont)
                """
                if not chunk.protein.residues_dl:                    
                    # Create a new residues display list if one is not present.
                    chunk.protein.residues_dl = glGenLists(1)
                    glNewList(chunk.protein.residues_dl, GL_COMPILE)
                    aa_list = chunk.protein.get_amino_acids()
                    for aa in aa_list:
                        # Iterate over amino acids and check if any rotamer
                        # is in 'expanded' state.
                        if chunk.protein.is_expanded(aa):
                            aa_atom_list = aa.get_side_chain_atom_list()
                            for atom in aa_atom_list:
                                pos1 = chunk.abs_to_base(atom.posn())
                                if aa.color:
                                    color = aa.color
                                else:
                                    color = atom.drawing_color()
                                glMaterialfv(
                                    GL_FRONT_AND_BACK, 
                                    GL_AMBIENT_AND_DIFFUSE, 
                                    color[:3])

                                ##### TODO: FIX: The *_worker functions should never be
                                # called directly from outside the drawing code. See longer
                                # comment where they are imported. [bruce 090304 comment]
                                
                                drawsphere_worker((pos1, 0.2, 1, 1))
                                
                                ### _name = aa.get_atom_name(atom)
                                ### textpos = chunk.abs_to_base(atom.posn()) + 2.0 * glpane.out
                                ### glColor3f(1,1,1)
                                ### chunk.glpane.renderText(textpos[0], textpos[1], textpos[2], _name, labelFont)                    
                                
                                # Draw bonds                                
                                for bond in atom.bonds:
                                    if bond.atom2 in aa_atom_list:
                                        if atom == bond.atom1:
                                            if bond.atom2 in aa_atom_list:
                                                pos2 = chunk.abs_to_base(
                                                    bond.atom2.posn())
                                                drawcylinder_worker((
                                                    pos1, 
                                                    pos1 + 0.5*(pos2 - pos1), 
                                                    0.2, 
                                                    True))
                                        else:
                                            if bond.atom1 in aa_atom_list:
                                                pos2 = chunk.abs_to_base(
                                                    bond.atom1.posn())
                                                drawcylinder_worker((
                                                    pos1, 
                                                    pos1 + 0.5*(pos2 - pos1), 
                                                    0.2, 
                                                    True))
                    glEndList()
                    
                # Call the residues display list
                glCallList(chunk.protein.residues_dl)
            
        return

    def writepov(self, chunk, memo, file):
        """
        Renders the chunk to a POV-Ray file.
        
        Not implemented yet.
        """
        return

    def compute_memo(self, chunk):
        """
        If drawing chunks in this display mode can be optimized by precomputing
        some info from chunk's appearance, compute that info and return it.

        If this computation requires preference values, access them as 
        env.prefs[key], and that will cause the memo to be removed (invalidated)
        when that preference value is changed by the user.

        This computation is assumed to also depend on, and only on, chunk's
        appearance in ordinary display modes (i.e. it's invalidated whenever
        havelist is). There is not yet any way to change that, so bugs will 
        occur if any ordinarily invisible chunk info affects this rendering,
        and potential optimizations will not be done if any ordinarily visible
        info is not visible in this rendering. These can be fixed if necessary
        by having the real work done within class Chunk's _recompute_ rules,
        with this function or drawchunk just accessing the result of that
        (and sometimes causing its recomputation), and with whatever 
        invalidation is needed being added to appropriate setter methods of 
        class Chunk. If the real work can depend on more than chunk's ordinary
        appearance can, the access would need to be in drawchunk;
        otherwise it could be in drawchunk or in this method compute_memo().

        @param chunk: The chunk.
        @type  chunk: chunk
        """

        def _get_ss(aa):
            """
            Returns secondary structure for a residue, or SS_COIL if 
            aa is None
        
            @param aa: amino acid
            @type aa: Residue
            """
            if aa:
                return aa.get_secondary_structure()

            return SS_COIL # BUG: Undefined variable

        def _get_aa(aa):
            """
            Returns a three-letter amino acid code for a residue,
            or "UNK" if aa is None.
            
            @param aa: amino acid
            @type aa: Residue
            """
            if aa:
                return aa.get_three_letter_code()
            
            return "UNK"

        # Return None if the chunk is None
        if chunk is None:
            return None

        # Return None if the chunk is not a protein.
        if chunk.protein is None:
            return None

        # List of secondary structure elements
        structure = []

        # Retrieve protein style properties from user preferences.
        self.proteinStyle =  env.prefs[proteinStyle_prefs_key] + 1
        self.proteinStyleSmooth = env.prefs[proteinStyleSmooth_prefs_key]
        self.proteinStyleQuality = 2 * env.prefs[proteinStyleQuality_prefs_key]
        self.proteinStyleScaling = env.prefs[proteinStyleScaling_prefs_key]
        self.proteinStyleScaleFactor = env.prefs[proteinStyleScaleFactor_prefs_key]
        self.proteinStyleColors = env.prefs[proteinStyleColors_prefs_key] 
        self.proteinStyleAuxColors = 0
        self.proteinStyleCustomColor = gray
        self.proteinStyleAuxCustomColor = gray
        self.proteinStyleColorsDiscrete = False
        self.proteinStyleHelixColor = env.prefs[proteinStyleHelixColor_prefs_key]
        self.proteinStyleStrandColor = env.prefs[proteinStyleStrandColor_prefs_key]
        self.proteinStyleCoilColor = env.prefs[proteinStyleCoilColor_prefs_key]

        # Extract secondary structure elements
        # Every element is a list of consecutive C-alpha atoms of the same 
        # secondary structure conformation. The list also includes
        # two "dummy" atoms - either preceding and following residues, or 
        # pre-computed dummy atoms extensions.

        # Empty SS element.
        sec = []

        # Extract a list of alpha carbon atoms and corresponding C-O vectors.
        # The C-O vectors are rotated to avoid sudden orientation changes.
        ca_list = []

        # "dpos" in the ProteinChunk code corresponds to a vector perpendicular
        # to Ca-Ca vector and laying in a peptide plane. Roughly, this vector
        # corresponds to a normalized C=O bond of a peptide carbonyl.
        # "dpos" vectors can be flipped so the angle between consecutive 
        # "dpos" vectors is less than 90 degree to avoid visual problems.
        
        # dictionary of corresponding Ca-Cb atoms for rendering of the
        # "Ladder" style. 
        ca_cb = {}

        n_ca = 0
        last_c_atom = None
        last_o_atom = None
        last_dpos = None
        last_ca_atom = None

        # Calculate "dpos" vectors paralles to the peptide planes.
        
        for aa in chunk.protein.get_amino_acids():
            last_c_atom = aa.get_c_atom()
            last_o_atom = aa.get_o_atom()
            last_cb_atom = aa.get_c_beta_atom()
            ca_atom = aa.get_c_alpha_atom()
            if ca_atom:
                dpos = None
                if last_o_atom and last_c_atom:
                    dpos = norm(last_o_atom.posn() - last_c_atom.posn())
                    if last_dpos:
                        dca = ca_atom.posn() - last_ca_atom.posn()
                        npep = cross(dca, dpos) # normal to the peptide plane
                        dpos = norm(cross(npep, dca))
                        n0 = last_dpos
                        n1 = dpos
                        d = dot(n0, n1)
                        # Flip dpos if the angle between consecutive planes 
                        # is > 90 deg.
                        if d < 0.0:
                            dpos = -1.0 * dpos
                    last_dpos = dpos
                ca_list.append((ca_atom, 
                                chunk.abs_to_base(ca_atom.posn()), 
                                _get_ss(aa), 
                                _get_aa(aa), 
                                dpos))
                last_ca_atom = ca_atom
                n_ca += 1

            if last_cb_atom:
                ca_cb[ca_atom] = chunk.abs_to_base(last_cb_atom.posn())
            elif last_ca_atom:
                ca_cb[ca_atom] = chunk.abs_to_base(last_ca_atom.posn())

        for p in range(len(ca_list)-1):
            atom, pos, ss, aa, dpos = ca_list[p]
            if dpos == None:
                atom2, pos2, ss2, aa2, dpos2 = ca_list[p+1]
                ca_list[p] = (atom, pos, ss, aa, dpos2)


        anum = 0

        # Smoothing alpha-helices and beta-strands. The consecutive "dpos"
        # vectors are smoothed using a sliding windows and weighted average.
        # Beta-strands use longer averaging window than alpha-helices.
        
        if self.proteinStyleSmooth and \
           (self.proteinStyle == PROTEIN_STYLE_TUBE or 
            self.proteinStyle == PROTEIN_STYLE_LADDER or 
            self.proteinStyle == PROTEIN_STYLE_ZIGZAG or
            self.proteinStyle == PROTEIN_STYLE_FLAT_RIBBON or
            self.proteinStyle == PROTEIN_STYLE_SOLID_RIBBON or \
            self.proteinStyle == PROTEIN_STYLE_SIMPLE_CARTOONS or \
            self.proteinStyle == PROTEIN_STYLE_FANCY_CARTOONS):

            smooth_list = [] 

            for i in range(len(ca_list)):
                if i > 0:
                    prev_ca, prev_ca_pos, prev_ss, prev_aa, prev_dpos = ca_list[i - 1]
                else:
                    prev_ca = None
                    prev_ca_pos = None
                    prev_ss = 0
                    prev_aa = None
                    prev_dpos = None

                ca, ca_pos, ss, aa, dpos = ca_list[i]

                if i < n_ca - 1:
                    next_ca, next_ca_pos, next_ss, next_aa, next_dpos = ca_list[i + 1]
                else:
                    next_ca = None
                    next_ca_pos = None
                    next_ss = 0
                    next_aa = None
                    next_dpos = None

                if (ss == 1 or prev_ss == 1 or next_ss == 1) and prev_ca and next_ca:
                    if prev_dpos and next_dpos:
                        dpos = norm(prev_dpos + dpos + next_dpos)
                    smooth_list.append((ca, ca_pos, ss, aa, dpos, i))

                if (ss == 2 or prev_ss == 2 or next_ss == 2) and prev_ca and next_ca:
                    ca_pos = 0.5 * (0.5 * (prev_ca_pos + next_ca_pos) + ca_pos)
                    if next_ss == 2 and prev_ss == 2:
                        dpos = norm(prev_dpos + dpos + next_dpos)
                    smooth_list.append((ca, ca_pos, ss, aa, dpos, i))

            for ca, ca_pos, ss, aa, dpos, i in smooth_list:
                ca_list[i] = (ca, ca_pos, ss, aa, dpos)

        # Build the list of secondary structure elements.
        
        n_sec = 0
        for i in range( n_ca ):

            ca, ca_pos, ss, aa, dpos = ca_list[i]

            if i > 0:
                prev_ca, prev_ca_pos, prev_ss, prev_aa, prev_dpos = ca_list[i - 1]
            else:
                prev_ca = ca
                prev_ca_pos = ca_pos
                prev_ss = ss
                prev_aa = aa                        
                prev_dpos = dpos

            if i > 1:
                prev2_ca, prev2_ca_pos, prev2_ss, prev2_aa, prev2_dpos = ca_list[i - 2]
            else:
                prev2_ca = prev_ca
                prev2_ca_pos = prev_ca_pos
                prev2_ss = prev_ss
                prev2_aa = prev_aa
                prev2_dpos = prev_dpos

            if len(sec) == 0:
                sec.append((prev2_ca_pos, prev2_ss, prev2_aa, i - 2, prev2_dpos, ca_cb[prev2_ca]))
                sec.append((prev_ca_pos, prev_ss, prev_aa, i - 1, prev_dpos, ca_cb[prev_ca]))

            sec.append((ca_pos, ss, aa, i, dpos, ca_cb[ca]))

            if i < n_ca - 1:
                next_ca, next_ca_pos, next_ss, next_aa, next_dpos = ca_list[i + 1]
            else:
                next_ca = ca
                next_ca_pos = ca_pos
                next_ss = ss
                next_aa = aa
                next_dpos = dpos

            if next_ss != ss or i == n_ca-1:                

                if i < n_ca - 2:
                    next2_ca, next2_ca_pos, next2_ss, next2_aa, next2_dpos = ca_list[i + 2]
                else:
                    next2_ca = next_ca
                    next2_ca_pos = next_ca_pos
                    next2_ss = next_ss
                    next2_aa = next_aa                
                    next2_dpos = next_dpos

                # Preasumably, the sec list includes all atoms
                # inside a continuous secondary structure chain fragment
                # (ss element) and FOUR dummy atom positions (two at
                # each of both terminals).
                
                # The dummy atom positions can't be None and therefore
                # the spline interpolator has to compute fake positions
                # of the terminal atoms.

                sec.append((next_ca_pos, next_ss, next_aa, i + 1, dpos, ca_cb[next_ca]))                
                sec.append((next2_ca_pos, next2_ss, next2_aa, i + 2, dpos, ca_cb[next2_ca]))                

                # Fix the endings.
                pos1, ss1, aa1, idx1, dpos1, cbpos1 = sec[1]
                pos2, ss2, aa2, idx2, dpos2, cbpos2 = sec[2]
                pos3, ss3, aa3, idx3, dpos3, cbpos3 = sec[3]
                ### pos4, ss4, aa4, idx4, dpos4, cbpos4 = sec[4]
                if pos1 == pos2:
                    pos1 =  pos1 - (pos3 - pos2)
                    sec[1] = (pos1, ss1, aa1, idx1, dpos1, cbpos1)

                pos1, ss1, aa1, idx1, dpos1, cbpos1 = sec[-2]
                pos2, ss2, aa2, idx2, dpos2, cbpos2 = sec[-3]
                pos3, ss3, aa3, idx3, dpos3, cbpos3 = sec[-4]
                ### pos4, ss4, aa4, idx4, dpos4, cbpos4 = sec[-5]
                if pos1 == pos2:
                    pos1 =  pos1 - (pos3 - pos2)
                    sec[-2] = (pos1, ss1, aa1, idx1, dpos1, cbpos1)                

                # Make sure that the interior surface of helices 
                # is properly oriented. This is important for "Fancy Cartoons"
                # display style.

                if ss == 1:
                    pos2, ss2, aa2, idx2, dpos2, cbpos2 = sec[2]
                    pos3, ss3, aa3, idx3, dpos3, cbpos3 = sec[3]
                    pos4, ss4, aa4, idx4, dpos4, cbpos4 = sec[4]

                    xvec = cross(pos4-pos3, pos3-pos2)
                    sign = dot(xvec, dpos3)

                    if sign > 0: 
                        # Wrong helix face orientation, invert peptide plates
                        for n in range(2, len(sec)-2):
                            (pos1, ss1, aa1, idx1, dpos1, cbpos1) = sec[n]
                            dpos1 *= -1
                            sec[n] = (pos1, ss1, aa1, idx1, dpos1, cbpos1)
                            pass
                        
                # Append the secondary structure element.
                structure.append((sec, ss))
                n_sec += 1

                sec = []                            

        return (structure, n_ca, ca_list, n_sec)

ChunkDisplayMode.register_display_mode_class(ProteinChunks)
