"""
demo_drag.py

$Id$

demo not only some drag actions, but some ways of setting up new model types
and their edit tools and behaviors. [Eventually.]
"""

from basic import *
from basic import _self, _this, _my


import Overlay
reload_once(Overlay)
from Overlay import Overlay

import transforms
reload_once(transforms)
from transforms import Translate

import Rect
reload_once(Rect)
from Rect import Rect

import Highlightable
reload_once(Highlightable)
from Highlightable import Highlightable ## Button, print_Expr


import draw_utils
reload_once(draw_utils)
from draw_utils import DZ ##e move DZ etc to basic??

# ==

Alias = mousepos = Stub
Position = 'stub type position'

class ModelObject(InstanceOrExpr,DelegatingMixin): # stub ##e will we need Widget2D for some reason?
    """#doc
    """
    pass

class Node(ModelObject): ##e should rename - not the same as in Utility.py. see below about what to rename it...
    """It has a position, initializable from arg1 but also settable as state under name pos, and an arb appearance.
    Position is relative to whatever coords it's drawn in.
    """
    ###e about what to rename it... Hmm, is it a general "Draggable"? .lookslike arg2 -> .islike or .thing arg1?
    
    # BTW, the highlightability is not yet specified here ###nim; it relates to the fact that we can bind commands to it
    # (as opposed to things it contains or is contained in, tho that should be permitted at the same time,
    #  tho implem requires nested glnames to sometimes ignore inner ones, when those are inactive);
    # but we might add it in a wrapper which makes it into a view of it that lets commands be bound to it,
    # except that World.draw assumes we draw the actual model objs, not wraps of them - also an issue if env says they
    # look different -- so maybe World needs to wrap all it draws with glue to add looks and behavior to it, in fact.

    # but for now, can we do this here?
    
    pos0 = Arg(Position)
    pos = State(Position, pos0) ###BUG -- does this work -- is pos0 set in time for this? not sure it's working... 061205 1009p
    #e we probably want to combine pos0/pos into one ArgState or StateArg so it's obvious how they relate,
    # and only one gets saved in file, and only one self.attr name is used up and accessible
    lookslike = ArgOrOption(Anything) # OrOption is so it's customizable
    ## delegate = _self.lookslike #k
    delegate = Highlightable( Translate( lookslike, pos ) )
                #e actions? or do this in a per-tool wrapper which knows the actions?
                # or, do this here and make the actions delegate to the current tool for the current parent? guess: the latter.
                
        ##e digr: will we want to rename delegate so it's only for appearance? *is it*? does it sim like this too?
        # Guess: it's for everything -- looks, sim qualities, etc -- except what we override or grab from special members.
        # [if so, no need to rename, except to clarify, leaving it general.]
    #e might need something for how to save it in a file, Undo policy, etc
    pass

# ==

class Command(InstanceMacro): #k super is prob wrong
    """#doc
    a subclass can make exprs that are specific available commands:
    - when they get args they know their param-formulas relative to event sources they're bound to
    - when instantiated, they are a potential real command, all decisions made, offerable (eg in a context menu)
    - some further protocol (not yet designed, but controlled by the event source)
      decides to start doing them, binding them to a real event (perhaps a long-running one like drag,
        or an even longer one if they are wizard-like commands that take over a window for awhile, with lots of mode like variables,
        lots of controls, etc -- in that case the "event" is just "all user events to this subwindow while this wizard is active"
        or "all user events controlled by this wizard" -- they're like a mode, in the old NE1)
      and letting them control what's shown (graphics area, in their own optional separate panes, etc),
      and what is left (as their side effect, changed or created stuff) at the end.
    """
    pass

class DragCommand(Command):
    """Commands that are bound to (give behavior/action to) a single drag-event
    (starting when the user-event-processing-system decides it's a real drag (not just a click),
    ending when the mouse goes up and the resulting intended effect (if any) can be done by this command).
    """
    pass

_PERMIT_SETS_INSIDE_ = attrholder # temporary kluge

class DragANode(DragCommand):
    """this runs on a new Node made by the click which started this drag (assumed made before this drag starts)
    [whether we can or should really separate click and drag actions like that, in this example, is not clear ###k]
    [but if we can, then this *same* command can also drag an *old* node, which would be nice, if we rename it. #e]
    [I think we can sep them, by noticing that the node-maker on click can then decide what to do with "the rest of its drag". #k
     In fact, I bet it will continue to exist as an ongoing command, delegating its remaining user-event stream to the subcommand
     it selects for handling that "rest". #k]
    """
    # the new Node is an Arg, I guess. How does caller know its name? or is it always arg1?
    node = Arg(Node)
    # it has a position which we will drag.
    # This is really its posn in a specific space... for now assume it (or our view of it, anyway)
    # owns that pos and knows that space.
    pos = Alias( node.pos) # Alias is so we can set or change pos as a way of changing node.pos [#nim, & not even fully decided on]

    # Q: if system decides it's a drag only after it moves a little bit, does the object then jump, or start smoothly,
    # as it starts to move?
    # A: what does NE1 do? what do I prefer? should it be a user pref? If so, can this code not even know about it somehow?
    # What would make this code simplest?
    # Does this code need a dragpoint on the new object (perhaps with a depth)? Does it need a drag-delta instead? (At what depth?)
    # Can this code work w/o change if someone hooks up a 3d drag device? (Meaning, it accepts a 3d drag path, for now always planar.)

    # ok, now it's time to specify our effect, which is basically, set node pos to mouse pos. How simple can it be, in that case?

    ## pos = mousepos # won't work, since erases above other set of pos in the class namespace.

    node.pos = mousepos # won't work -- syntax error [predicted] .. wait, turns out it's not one!!!
        # But what does it do? It ought to be doing setattr on an expr returned by Arg(Node) -- which does what?
        # Oh, just sets the attr in there, silently! Can we capture it? If the attrname is arbitrary (seems likely, not certain),
        # then only with expensive code (on all symbolic exprs?) to notice all sets of attrs not starting with _e_ etc...
        # (hmm, maybe we don't need to notice them except later? that is, it's just a formula sitting inside the value of node,
        #  created by Arg just for us after all, which we can notice from dir(node) since the attrname doesn't start _e_??
        # As experiment just try printing them all. But first keep deciding if we want this syntax, since it's kind of weird.
        # E.g. it implies we do this continuously, *all the time* that this instance exists [wrong, see below] --
        # which might be what we want... hmm.
        # It also naturally only lets us assign a specific thing as one formula... at least at the whole-class level. Hmm.

        # actually it doesn't have to mean we do the action continuously. The formulas could get grabbed and stored,
        # for whole class or per-symbol or per-symbol.attr.attr (or all of those), and then done by a specific method call,
        # either once at the end or continuosly, and in various "modes of doing them" like accept or offer or reject/cancel...
        # this would let us set up the side effects, then do them tentatively during the command, do them fully after it,
        # or reject/cancel them in an automatic way using a single call (doing right thing re history, undo, etc).
        # If the command-end method didn't exist, the standard super one could just accept the changes
        # (and same with setting up to tentatively accept them during the command, showing that in std ways).
        #
        # BTW the way tentativeness can be shown is to store metainfo with the attr-set side effects
        # (eg obj._tentativeness_of_attr = True # (paraphrased)), then for display styles to notice that and let it affect them,
        # maybe noticing it automatically for all attrs they use -- i.e. "or" some caveat-flags (incl warnings, uncertainties...)
        # as you usage-track so you'll know what caveats apply to some value you compute. (Or actually use them, in case they change.
        # I guess only use them for a parallel computation of your own caveats.)
    
    print "our node symexpr has:",node._e_dir_added()
##    for attr in dir(node):
##        if attr.startswith('_e_') or attr.startswith('__'):
##            pass
##        else:
##            print attr, # _init_e_serno_ [fixed?], pos
##        continue
##    print

    node.pos.subattr = 1
    node.pos2 = _PERMIT_SETS_INSIDE_()
    node.pos2.subattr2 = 1

    print "now it has:",node._e_dir_added() ###BUG [before i had _PERMIT_SETS_INSIDE_() above] - where is pos2?
    #print "dir is",dir(node) # it's not in here either! OH, I never made it, I only asked for it (for val of node.pos2)
     # and I got a getattr_Expr of node and pos2! Can that be fixed? As it is I can't even see that getattr_Expr,
     # it was discarded. Can/should I capture the setattr of attr in symbolic getattr_Expr? Guess: probably I can. ###k
     # (Alternatively I could capture the making of the getattr_Expr on a symbolic expr,
     #  and do something equiv to the set to _PERMIT_SETS_INSIDE_() above -- this might make basic sense...
     #  but it would only work if I didn't return the getattr_Expr itself, but whatever object I stored for it!
     #  But wait, why not just store that same getattr_Expr, so it's memoized (might save mem or help in other ways)? Hmm..
     #  note that the exact cond for doing this being ok is not _e_is_symbolic but something inherited from arg1 of some OpExprs...
     #  ###k
     #
     #  [digr: it might even have other uses, like a convenient record of how we use each symbol,
     #   which can be checked against its type later on,
     #   or checked against specific values passed in, or used in other ways....])
     #
     # [Then I could also warn if i thought it might be discarded -- if the set fails to know it "tells something it was done".]
     ####e First decide if i want to. My tentative guess is yes, but the idea is too new to be sure.
     # But I could test the idea without that, just by requiring kluge workaround of a set of node.pos2 to a special value; try above.

    node.blorg = node.blorg + 1 # hopefully this will set it to a OpExpr of a getattr_Expr, equiv to the expr node.blorg + 1

    #print "node.blorg is now",node.blorg # it does!
    
    pass # end of class DragANode

ClickDragCommand = DragCommand # STUB
    #e the idea is, one includes initial click, one only starts when real drag is recognized

class MakeANode(ClickDragCommand): #k super?
    #e will be bound to empty space, or guide surfaces/objects you can make nodes on
    # (but might want them as arg, to attach to -- hmm, not only the surface, but the space!
    #  same arg? -- what it's a feature of or on? or, feature of and feature on might both be space, or might be space and obj??
    #  related: what its saved pos is relative to. ####e decide that...)
    """
    """
    # hmm, they clicked, at some pos, and we know a kind of node to make... let's make it
    newnodepos = V_expr(0,0,0) #stub
    newnodepos = _self.pos # what other kind of pos can we have? well, we could have the continuously updated mousepos...
    newnodepos = _self.clickpos #e rename; note we have dragstart_posn or so in other files
    
    newnode = Node(newnodepos, 'some params') 
        ###PROBLEM: is that just an Expr (pure expr, not instance, not more symbolic than IorE) assigned to an attr?
        # is it symbolic enough to let us do newnode.pos = whatever later if we want?
        # see cmt below about how to list it as "_what_we_make".
    
    # (typically some params would be formulas)

        # - do those params say where in space, relative to mousepos? yes, they must, since it can vary for other commands,
        #   eg if it's built on top of something that exists (see above comment about attaching to an obj, too).
    
    # now we want to say:

    # - where to put it -- i mean, what collection to assign it to
    
    # - now permit it to be dragged (or in other kinds of commands, permit some aspect of it to be dragged)
    #   - maybe with some params of the node -- or of this command (temporary params not in the node itself) --
    #     being controlled during the drag
    #   by letting this event be taken over (after its side effects, maybe before its own wrapups) by another command

    #   but binding that other command to the event that a real drag starts -- HOW? ###e

    ## _value_if_a_real_drag_starts___is_made_from_this_expr = DragANode # ___is_made_from_this_expr should be implicit
    
        #e DragANode with what args? self? self.newnode? might need self if it needs to change the look based on self...
        # otoh it has access to the drag event, so maybe that would be rare...
        # except that self is probably controlling "tentativity". hmm.... ###k

        #e revise to look like a bunch of subevents bound to actions/behaviors (commands), when we know what that looks like
        # tho this special case might be common enough to have its own name, shorter than this one, e.g. _continue_drag
        
    _value_if_a_real_drag_starts = DragANode( newnode)

        # defect: this requires us to define DragANode first in the file; if a problem, replace it with _forward.DragANode or so

    _what_we_make = newnode # maybe we'll just name newnode so this is obvious...
        # btw this can be an exception to not allowing two attrs = one expr, since _what_we_make is a special name... so ignore this:
            ## warning: formula <Widget2D#12737(a)> already in replacements -- error??
            ## its rhs is <getattr_Expr#12741: (S._self, <constant_Expr#12740: '_what_we_make'>)>;
            ## new rhs would be for attr 'newnode'
        # should we make its specialness obvious (for it and _value and _continue_drag and all other special names)??
        # I mean by a common prefix or so. BTW are they all different kinds of "values" or "results"? Could use _V_ or _v_ or _r_...
        # ####e decide

    # an alternate way to say what we make, and to say where: some sort of side effect formula... maybe worse re POLS.
    if 0:
        _something.make(newnode)
        _something.add(newnode)
        _self.something.make(newnode)
        make(newnode)
        # etc
        
    pass # end of class MakeANode

# ==

# for a quick implem, how does making a new node actually work? Let's assume the instance gets made normally,
# and then a side effect adds it to a list (leaving it the same instance). Ignore issues of "whether it knows its MT-parent" for now.
# We know it won't get modified after made, since the thing that modifies it (the command) is not active and not reused.
# (It might still exist enough to be revivable if we Undoed to the point where it was active, if it was a wizard... that's good!
#  I think that should work fine even if one command makes it, some later ones modify it, etc...)

# so we need a world object whose state contains a list of Nodes. And a non-stub Node object (see above I hope).

class World(ModelObject):
    nodelist = State(list_Expr, []) ###k ?? # self.nodelist is public for append (can that be changetracked???#####IMPLEM) or reset
    def draw(self):
        for node in self.nodelist:
            # print "%r is drawing %r at %r" % (self, node, node.pos) # suspicious: all have same pos ... didn't stay true, nevermind
            node.draw() # this assumes the items in the list track their own posns, which might not make perfect sense;
                # otoh if they didn't we'd probably replace them with container objs for our view of them, which did track their pos;
                # so it doesn't make much difference in our code. we can always have a type "Node for us" to coerce them to
                # which if necessary adds the pos which only we see -- we'd want this if one Node could be in two Worlds at diff posns.
                # (Which is likely, due to Configuration Management.)
        ###e see comment above: "maybe World needs to wrap all it draws with glue to add looks and behavior to it"
        return
    pass

# ok, now how do we bind a click on empty space to class MakeANode ?

# note, someday we might just as easily bind a click on some guide surface
# (onto which we've applied an active tool to interpret clicks)
# to that command, as binding a click on empty space to it. The point is, we have tools, with cmds in them,
# and we bind tools to objects or to pieces of space (see scratch6 and recent notesfiles).
#
# so we can separate this: #####IMPLEM all these
# - put this command and others (for other modkeys) into a tool, and
# - make a button for a pallette which can (when run on a selected space or surface, or on the current space)
#   - bind that tool to empty space or to a guide surface.
# - make a pallette with that button
# - show this pallette.
# - make a space object... is it that World object above, or only sometimes, or only temporarily?
#   well, the tool can change for the same world, the world concerns itself only with what kind of data it can hold
#   (and it may offer a set of tools, or have a default one, or have implems of std-named ones...)

# but for an initial test, we can always be in this kind of world, have one tool implicitly, on entire space --
# but this does require changing the click-action. OR we could create a big image as a guide shape, and put click action on that.
# Hmm, I think that's easier, I'll try that first.

# Let's do it with a DNA origami image... but first, just a rect. So, we want a modifier for a thing (the rect)
# which gives it the event bindings implied by this tool. I.e. a macro based on Highlightable.

# status 061205 1022p: works (in this initial klugy form, not using Command classes above) except for recording points in abs coords
# (wrong) but drawing them in arb rel coords (wrong), when both need to be in a specified coord sys, namely that of the bg rect object.
class GraphDrawDemo_FixedToolOnArg1(InstanceMacro):
    background = Arg(Widget2D, Rect(10))
    world = Instance( World() ) # has .nodelist I'm allowed to extend
    _value = Overlay(
        Highlightable( background, on_press = _self.on_press_bg, on_drag = _self.on_drag_bg ),
        ## Translate( world, DZ)### Translate needed?? not good once not needed... BUT will it even work?? I think so...
        world
    )
    _index_counter = State(int, 1000) # we have to use this for indexes of created thing, or they overlap state!
    def on_press_bg(self):
        ###e hmm, how can we find out the mouse pos of the event?? without having to accept an arg all the time? be an Action??
        # or is it ok for the caller to ask us how many args we take and pass one only if we take one?
        # (non-POLS I suppose; maybe ok if reliable. But it's a pain, and weird, and makes it hard to read and learn from the code...)
        # (Maybe it has to try passing one, see the exception... unsafe if bug *inside* ... same problems.)
        # So is there a simpler way, like looking in self.env or self.glpane here? yes.
        # Nothing really wrong with it (just a dynamic var).
        # It's just part of the API of these methods -- bind glpane.xxx while you call them.
##        pos = self.env.glpane._event.pos #####IMPLEM and maybe rename and maybe change type and maybe translate coords...
            # but wait, we have to turn it into a 3d point! Hmm, that point is being passed into Highlightable...
        point = self.current_event_mousepoint() # shorthand... which makes it easier to translate coords for now ###IMPLEM in Widget?
        # for initial test, don't use those Command classes above, just do a side effect right here
        # kluge: that's in abs coords for now

        print "event mousepoint:",point, ###
        newpos = point + DZ * PIXELS
        print "newpos",newpos
        node_expr = Node(newpos, Rect(0.2,0.2,red)) # kluge: move it slightly closer so we can see it in spite of bg
            ###e needs more principled fix -- not yet sure what that should be -- is it to *draw* closer? (in a perp dir from surface)
            #e or just to create spheres (or anything else with thickness in Z) instead? (that should not always be required)
        node = self.make(node_expr) ## , 'on_press_bg')
        ## self.world.nodelist.append(node)
        self.world.nodelist = self.world.nodelist + [node] # kluge: make sure it gets change-tracked. Inefficient when long!
        print "added",node,"ipath[0]",node.ipath[0]
##        print "at (should be newpos)",node.pos###
##        ###BUG: after reload, these new nodes share ipath with old ones, and that Arg/State code gets fooled (I conjecture)
##        # and inits state to the state of the old node, ignoring the arg!!!
##        # evidence: the recycled 101 in the following, the first 2 nodes with identical pos...
##            ##event mousepoint: [-5.90148889  5.16380219  0.01199794] newpos [-5.90148889  5.16380219  0.04699794]
##            ##added <Node#18254(i)> ipath[0] 101
##            ##at (should be newpos) [-3.3274351   2.6525307   0.04699794]
##        ### FIXED by recording self._index_counter in State, not just in self!
            

        ##e let new node be dragged, and use Command classes above for newmaking and dragging
        return
    def on_drag_bg(self):
        print "called on_drag_bg" # note: nothing useful is in the glpane env, yet ###IMPLEM
    def make(self, expr): ## , index = None):
        index = None
        #e rename? #e move to some superclass 
        #e worry about lexenv, eg _self in the expr, _this or _my in it... is expr hardcoded or from an arg?
        #e revise implem in other ways eg eval vs instantiate
        #e default unique index?? (unique in the saved stateplace, not just here)
        # (in fact, is reuse of index going to occur from a Command and be a problem? note *we* are acting as command...
        #e use in other recent commits that inlined it
        if index is None:
            # usual case I hope (due to issues mentioned above): allocate one
            if 0:
                index = getattr(self, '_index_counter', 100)
                index = index + 1
                setattr(self, '_index_counter', index)
            else:
                # try to fix bug
                index = self._index_counter
                index = index + 1
                self._index_counter = index
                ###e LOGIC ISSUE: should assert the resulting ipath has never been used,
                # or have a more fundamental mechanism to guarantee that
        env = self.env # maybe wrong, esp re _self
        ipath = (index, self.ipath)
        return expr._e_eval(self.env, ipath)
    def current_event_mousepoint(self): #e rename #e move to Widget or so #e or move to glpane, except might need self coord sys to work
        """return the 3d point (in abs coords for now ###FIX) corresponding to the click point
        of the current mousepress event (error if no current mousepress event);
        this is defined (for now) based on the depth buffer pixel clicked on,
        or is in the plane of the center-of-view otherwise.
           Naming note: point implies 3d; pos might mean 2d, especially in the context
        of a 2d mouse. So it's named mousepoint rather than mousepos.
        """
        return + self.env.glpane._point # the + is to make a copy for safety; we assume it's a Numeric array
# end
