from .reader import read_source
from . import handoff
FIELDS=['id', 'subject', 'visit', 'at', 'enrolled', 'kind', 'parent', 'value', 'unit', 'protocol', 'revision']
OPTIONAL=['center', 'handoff']
def apply(state):
    read_source(state,FIELDS,{'编号':'id','中心':'center','交接单':'handoff'},OPTIONAL)
    handoff.apply(state)
