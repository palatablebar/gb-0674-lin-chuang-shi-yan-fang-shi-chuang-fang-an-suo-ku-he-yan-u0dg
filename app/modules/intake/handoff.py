from collections import defaultdict
from app.coerce import instant
from app.reasons import reject

# 交接指纹只含业务内容；传输编号 id 与物理行号不参与，同一交接重试因此不会新增访视。
FINGERPRINT_KEYS=('subject','visit','at','enrolled','kind','parent','value','unit','protocol','revision','center','handoff')

def fingerprint(row):
    return tuple(row.get(k,'') for k in FINGERPRINT_KEYS)

def center_name(context,code):
    return context.get('centers',{}).get(code,code)

def owner_for(context,subject,at):
    """按受试者转移事件的半开生效窗裁决责任中心，依据为最近一次已生效交接。"""
    transfers=[t for t in context.get('transfers',{}).get(subject,[]) if instant(t['at'])<=at]
    if not transfers:
        return context.get('default_center',''), ''
    basis=sorted(transfers,key=lambda t:instant(t['at']))[-1]
    return basis['to'], basis['handoff']

def evidence_row(row,context,code,owner,handoff,detail):
    return {'id':row['id'],'subject':row['subject'],'visit':row['visit'],'kind':row.get('kind',''),
            'center':row.get('center',''),'owner_center':owner,'handoff':handoff or row.get('handoff',''),
            'basis':center_name(context,owner),'code':code,'line':row.get('_line',0),'detail':detail}

def apply(state):
    context=state['context']
    default=context.get('default_center','')
    state['center_evidence']=[]
    state['center_blocks']=[]
    rows=[]
    # 1. 缺省中心填充与在册校验
    for row in state['records']:
        if not row.get('center'): row['center']=default
        if row['center'] not in context.get('centers',{}):
            reject(state,row,'BAD_CENTER',f"报送中心{row.get('center','')}不在册");continue
        rows.append(row)
    # 2. 同一交接单在同一中心的重试：指纹相同去重，指纹不同整组阻断
    groups=defaultdict(list)
    for row in rows:
        if row.get('handoff'): groups[(row['handoff'],row['center'])].append(row)
    retry_ids=set();conflict_ids=set()
    for (handoff,center),members in groups.items():
        prints={fingerprint(r) for r in members}
        if len(prints)==1:
            keep=sorted(members,key=lambda r:(r['_line'],r['id']))[0]
            for r in members:
                if r is keep: continue
                retry_ids.add(r['id']);state['counts']['handoff_retry']+=1
                state['center_evidence'].append(evidence_row(r,context,'HANDOFF_RETRY',keep['center'],handoff,
                    f'交接单{handoff}同中心重试，沿用记录{keep["id"]}，不新增访视'))
        else:
            for r in members:
                conflict_ids.add(r['id'])
                reject(state,r,'HANDOFF_CONFLICT',f'交接单{handoff}在{center_name(context,center)}存在不同原值，需人工核对')
    rows=[r for r in rows if r['id'] not in retry_ids and r['id'] not in conflict_ids]
    # 3. 无转移依据却多中心同报：责任中心未定，整组阻断等待裁决
    slot=defaultdict(list)
    for row in rows: slot[(row['subject'],row['visit'])].append(row)
    unresolved=set()
    transfers=context.get('transfers',{})
    for (subject,visit),members in slot.items():
        if subject not in context.get('subjects',{}): continue
        if subject not in transfers and len({r['center'] for r in members})>1:
            for r in members:
                unresolved.add(r['id'])
                state['center_blocks'].append(evidence_row(r,context,'CENTER_CONFLICT',default,r.get('handoff',''),
                    '多中心同报且无转移交接依据，责任中心未定'))
    # 4. 责任中心裁决：非责任中心报送保留原始证据但不计访视
    #    未入组受试者不在此裁决，留给方案阶段按 UNKNOWN_SUBJECT 隔离，避免掩盖错误
    kept=[]
    for row in rows:
        if row['id'] in unresolved: continue
        if row['subject'] not in context.get('subjects',{}):
            row['owner_center']=default
            row['owner_basis']=''
            kept.append(row);continue
        owner,basis=owner_for(context,row['subject'],instant(row['at']))
        row['owner_center']=owner
        row['owner_basis']=basis
        if row['center']!=owner:
            state['counts']['center_duplicate']+=1
            state['center_evidence'].append(evidence_row(row,context,'CENTER_DUPLICATE',owner,basis,
                f'{center_name(context,row["center"])}非责任中心，原始记录保留，由{center_name(context,owner)}放行'))
            continue
        kept.append(row)
    state['records']=kept
    view=state['views']['intake']
    view['center_evidence']=state['center_evidence']
    view['center_blocks']=state['center_blocks']
    view['metrics'].update({'交接重试':state['counts']['handoff_retry'],
                            '非责任中心报送':state['counts']['center_duplicate'],
                            '交接阻断':len(state['center_blocks'])})
