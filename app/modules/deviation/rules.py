from collections import defaultdict

def detect(windows,context,center_blocks=None,center_evidence=None):
    center_blocks=center_blocks or []
    center_evidence=center_evidence or []
    primary=defaultdict(list)
    for row in windows:
        if row['kind']=='PRIMARY':primary[(row['subject'],row['visit'])].append(row)
    suppressed=defaultdict(list)
    for row in center_evidence:
        if row['code']=='CENTER_DUPLICATE' and row['kind']=='PRIMARY':
            suppressed[(row['subject'],row['visit'])].append(row)
    issues=[];completed=[]
    for subject in sorted(context['subjects']):
        for visit in context['required_visits']:
            items=primary.get((subject,visit),[])
            if not items:
                shadows=suppressed.get((subject,visit),[])
                if shadows:
                    shadow=shadows[0]
                    issues.append({'subject':subject,'visit':visit,'id':shadow['id'],'code':'CENTER_OWNER_MISSING',
                        'owner_center':shadow['owner_center'],'center':shadow['center'],'handoff':shadow['handoff'],
                        'detail':f"仅{shadow['center']}中心报送，责任中心{shadow['owner_center']}无记录，交接依据{shadow['handoff'] or '无'}"})
                else:
                    issues.append({'subject':subject,'visit':visit,'id':'','code':'MISSING_PRIMARY'})
                continue
            if len(items)>1:issues.append({'subject':subject,'visit':visit,'id':','.join(r['id'] for r in items),'code':'DUPLICATE_PRIMARY','owner_center':items[0].get('owner_center','')});continue
            row=items[0]
            if row['code']!='IN_WINDOW':issues.append({**row,'code':'WINDOW_'+row['code']})
            else:completed.append(row)
    issues.extend(center_blocks)
    return issues,completed

def apply(state):
    issues,completed=detect(state['windows'],state['context'],state.get('center_blocks'),state.get('center_evidence'));state.update(deviations=issues,completed=completed)
    state['views']['deviation']={'title':'偏离复核','rows':issues,'metrics':{'完成访视':len(completed),'缺失或偏离':len(issues),'缺首次访视':sum(x['code']=='MISSING_PRIMARY' for x in issues),'交接阻断':sum(x['code'] in ('CENTER_CONFLICT','CENTER_OWNER_MISSING') for x in issues)}}
