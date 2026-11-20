def decide(state):
    c=state['counts'];extra=c.get('handoff_retry',0)+c.get('center_duplicate',0)
    explained=len(state['records'])+len(state['quarantine'])+c['blank']+c['duplicate']+c['repeated_header']+extra
    handoff_blocks=len(state.get('center_blocks',[]))
    blocked=len(state['deviations'])+len(state['retest_issues'])+len(state['quarantine'])
    return {'input':c['input'],'accepted':len(state['records']),'quarantined':len(state['quarantine']),'row_balanced':c['input']==explained,'completed':len(state['completed']),'expected':len(state['context']['subjects'])*len(state['context']['required_visits']),'deviations':len(state['deviations']),'retest_issues':len(state['retest_issues']),'handoff_blocks':handoff_blocks,'blocked':blocked,'status':'可锁库' if not blocked and c['input']==explained else '待处理'}
def apply(state):
    state['balance']=decide(state);state['views']['locking']={'title':'锁库闸门','rows':[state['balance']],'metrics':{'应访视':state['balance']['expected'],'已完成':state['balance']['completed'],'阻断项':state['balance']['blocked'],'交接阻断':state['balance']['handoff_blocks']}}
