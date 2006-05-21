# Standard imports
from sets import Set as set

# External imports
import numpy as N
import enthought.traits as traits
from attributes import readonly, constant

# Package imports
from neuroimaging import haslength

itertypes = ("slice", "parcel", "slice/parcel", "all")


##############################################################################
class Slicer(traits.HasTraits):
    '''
    This class is an iterator that steps through the slices
    of a N-dimensional array of shape shape, along a particular axis, with a
    given step and an optional start.

    The attribute nslicedim determines how long a slice is returned, only
    step[0:nslicedim] and start[0:nslicedim] is used, where self.step
    defaults to [1]*(nslicedim).

    More than one slice can be output at a time, using nslice.
    '''

    axis = traits.Int(0)
    end = traits.List()
    step = traits.Any()
    start = traits.Any()
    ndim = traits.Int()
    nslicedim = traits.Int()
    nslice = traits.Int(1)
    
    type = traits.String('slice')

    def _end_changed(self):
        self.ndim = len(self.end)

    def __init__(self, end, **keywords):
        traits.HasTraits.__init__(self, **keywords)
        self.end = list(end)

        self.nslicedim = max(self.nslicedim, self.axis+1)

        if self.step is None:
            self.step = N.array([1]*self.nslicedim)

        if self.start is None:
            self.start = N.array([0]*self.nslicedim)

    def __iter__(self):
        self.isend = False
        self.slice = self.start[self.axis]
        self.last = self.end[self.axis]
        return self

    def next(self):
        if self.isend:
            raise StopIteration
        _slices = []
        for i in range(self.nslicedim):
            if self.axis != i:
                _slice = slice(self.start[i], self.end[i], self.step[i])
                _slices.append(_slice)
            else:
                _slice = slice(self.slice,
                               self.slice + self.nslice * self.step[i],
                               self.step[i])
                self.slice += self.nslice * self.step[i]
                _slices.append(_slice)

        if self.slice >= self.last: self.isend = True
        return _slices, self.isend


##############################################################################
class SliceIteratorNext (object):
    class type (constant): default="slice"
    class slice (readonly): pass
    def __init__(self, slice): self.slice = slice


##############################################################################
class SliceIterator(Slicer):

    #-------------------------------------------------------------------------
    def __init__(self, shape, **keywords):
        traits.HasTraits.__init__(self, **keywords)
        Slicer.__init__(self, shape, **keywords)
        self.allslice = [slice(self.start[i],
                               self.end[i],
                               self.step[i]) for i in range(self.nslicedim)]

    #-------------------------------------------------------------------------
    def next(self):
        _slice, isend = Slicer.next(self)
        return SliceIteratorNext(_slice)


##############################################################################
class AllSliceIterator(Slicer):

    type = traits.Str('all')

    #-------------------------------------------------------------------------
    def __iter__(self):
        self.isend = False
        return self

    #-------------------------------------------------------------------------
    def __init__(self, shape, **keywords):
        traits.HasTraits.__init__(self, **keywords)
        self.shape = shape
        self.isend = False

    #-------------------------------------------------------------------------
    def next(self):
        if self.isend: raise StopIteration
        _slice = slice(0, self.shape[0], 1)
        self.isend = True
        return SliceIteratorNext(_slice)


##############################################################################
class ParcelIteratorNext (object):
    class type (constant): default="parcel"
    class label (readonly): pass
    class where (readonly): pass
    def __init__(self, label, where): self.label, self.where = label, where


##############################################################################
class ParcelIterator (object):
    class labels (readonly): pass
    class labelset (readonly): pass

    #-------------------------------------------------------------------------
    def __init__(self, labels, keys):
        self.labels = N.asarray(labels)
        if keys == None: labelset = N.unique(self.labels.flat)
        else: labelset = list(set(keys))
        self.labelset = iter(labelset)
        self.labels.shape = haslength(keys[0]) and\
          (self.labels.shape[0], N.product(self.labels.shape[1:])) or\
          N.product(self.labels.shape)

    #-------------------------------------------------------------------------
    def __iter__(self): return self

    #-------------------------------------------------------------------------
    def next(self):
        label = self.labelset.next()
        if not haslength(label):
            wherelabel = N.equal(self.labels, label)
        else:
            wherelabel = N.product([N.equal(labeled, label)\
              for labeled,label in zip(self.labels, label)])
        return ParcelIteratorNext(label, wherelabel)

 
##############################################################################
class SliceParcelIteratorNext (ParcelIteratorNext, SliceIteratorNext):
    class type (constant): default="slice/parcel"
    def __init__(self, label, where, slice):
        SliceIteratorNext.__init__(slice)
        ParcelIteratorNext.__init__(label, where)

       
##############################################################################
class SliceParcelIterator (ParcelIterator):
    """
    This iterator assumes that labels is a list of lists (or an array)
    and the keys is a sequence of length labels.shape[0] (=len(labels)).
    It then goes through the each element in the sequence
    of labels returning where the unique elements are from keys.
    """
    #-------------------------------------------------------------------------
    def __init__(self, labels, keys, **keywords):
        self.labels = labels
        self.labelset = iter(keys)

        if len(labels) != len(labelset):
            raise ValueError, 'labels and labelset do not have the same length'

    #-------------------------------------------------------------------------
    def __iter__(self):
        self.curslice = -1
        return self

    #-------------------------------------------------------------------------
    def next(self):
        try:
            label = self.curlabelset.next()
        except:
            self.curlabelset = iter(self.labelset.next())
            label = self.curlabelset.next()
            self.curslice += 1
            pass

        self.curlabels = self.labels[self.curslice]

        if not isinstance(self.curlabels, N.ndarray):
            self.curlabels = N.array(self.curlabels)
            
        self.curlabels.shape = N.product(self.curlabels.shape)
        wherelabel = N.equal(self.curlabels, label)
        return SliceParcelIteratorNext(label, wherelabel, self.curslice)