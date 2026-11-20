import pytest
from copy import deepcopy
from app.engine import evaluate
from app.modules.intake.handoff import owner_for, fingerprint
from app.coerce import instant

HO='HO-20261010-00001'

def test_transfer_dataset_lockable_with_unique_owner():
    s=evaluate({'dataset':'transfer'})
    assert s['balance']['status']=='可锁库'
    assert s['balance']['completed']==s['balance']['expected']==40
    v2=next(r for r in s['selected_results'] if r['subject']=='00001' and r['visit']=='V2')
    assert v2['owner_center']=='02' and v2['handoff']==HO
    v1=next(r for r in s['selected_results'] if r['subject']=='00001' and r['visit']=='V1')
    assert v1['owner_center']=='01'

def test_owner_adjudication_half_open():
    ctx=evaluate({'dataset':'transfer'})['context']
    assert owner_for(ctx,'00001',instant('2026-10-09T23:59:59+08:00'))[0]=='01'
    owner,handoff=owner_for(ctx,'00001',instant('2026-10-10T00:00:00+08:00'))
    assert (owner,handoff)==('02',HO)
    assert owner_for(ctx,'00002',instant('2026-10-15T08:00:00+08:00'))[0]=='01'

def test_handoff_retry_does_not_add_visit():
    s=evaluate({'dataset':'transfer'})
    assert s['counts']['handoff_retry']==1
    ids=[r['id'] for r in s['records']]
    assert '00001-V2-RETRY' not in ids
    assert '00001-V2' in ids
    v2_primaries=[r for r in s['windows'] if r['subject']=='00001' and r['visit']=='V2' and r['kind']=='PRIMARY']
    assert len(v2_primaries)==1
    evidence=next(e for e in s['center_evidence'] if e['id']=='00001-V2-RETRY')
    assert evidence['code']=='HANDOFF_RETRY' and evidence['owner_center']=='02'

def test_non_owner_submission_kept_as_raw_evidence():
    s=evaluate({'dataset':'transfer'})
    assert s['counts']['center_duplicate']==1
    ev=next(e for e in s['center_evidence'] if e['id']=='00001-V2-S01')
    assert ev['code']=='CENTER_DUPLICATE' and ev['center']=='01' and ev['owner_center']=='02'
    assert s['balance']['quarantined']==0
    assert s['balance']['row_balanced'] is True

def test_handoff_conflict_quarantines_and_blocks():
    text=open('/workspace/sample_data/transfer.csv',encoding='utf-8').read()
    conflict=text.replace('00001-V2-RETRY,','00001-V2-RETRYX,',1).replace(
        '00001-V2-RETRYX,00001,V2,2026-10-15T08:00:00+08:00',
        '00001-V2-RETRYX,00001,V2,2026-10-15T09:30:00+08:00',1)
    s=evaluate({'csv_text':conflict})
    codes={q['code'] for q in s['quarantine']}
    assert 'HANDOFF_CONFLICT' in codes
    assert s['balance']['status']=='待处理'
    assert any(q['id'].startswith('00001-V2') for q in s['quarantine'] if q['code']=='HANDOFF_CONFLICT')

def test_center_conflict_without_transfer_basis_blocks():
    overrides={'transfers':{}}
    s=evaluate({'dataset':'transfer','overrides':overrides})
    codes={b['code'] for b in s['center_blocks']}
    assert 'CENTER_CONFLICT' in codes
    assert s['balance']['status']=='待处理'
    block=next(b for b in s['center_blocks'] if b['subject']=='00001' and b['visit']=='V2')
    assert block['detail']

def test_owner_missing_when_only_non_owner_reports():
    # 删掉责任中心02的V2记录，仅保留01中心报送
    text=open('/workspace/sample_data/transfer.csv',encoding='utf-8').read()
    lines=[l for l in text.splitlines() if not (l.startswith('00001-V2,') or l.startswith('00001-V2-RETRY,'))]
    overrides={'transfers':{'00001':[{'at':'2026-10-10T00:00:00+08:00','from':'01','to':'02','handoff':HO,'reason':'转中心'}]}}
    s=evaluate({'csv_text':'\n'.join(lines)+'\n','overrides':overrides})
    issue=next(d for d in s['deviations'] if d['subject']=='00001' and d['visit']=='V2')
    assert issue['code']=='CENTER_OWNER_MISSING'
    assert issue['owner_center']=='02' and issue['id']=='00001-V2-S01'
    assert s['balance']['status']=='待处理'

def test_bad_center_quarantined():
    text=open('/workspace/sample_data/transfer.csv',encoding='utf-8').read()
    bad=text.replace(',02,HO-20261010-00001',',09,HO-20261010-00001',1)
    s=evaluate({'csv_text':bad})
    assert any(q['code']=='BAD_CENTER' for q in s['quarantine'])
    assert s['balance']['status']=='待处理'

def test_legacy_11_column_header_still_accepted():
    from app.errors import BusinessError
    header='id,subject,visit,at,enrolled,kind,parent,value,unit,protocol,revision\n'
    with pytest.raises(BusinessError) as e:
        evaluate({'csv_text':header})
    assert e.value.code=='HEADER_ONLY'
    full=open('/workspace/sample_data/clean.csv',encoding='utf-8').read()
    stripped='\n'.join(','.join(l.split(',')[:11]) for l in full.splitlines() if l.strip())+'\n'
    s2=evaluate({'csv_text':stripped})
    assert s2['records'][0]['center']=='01' and s2['records'][0]['handoff']==''

def test_responsibility_propagates_to_windows_retest_archive():
    s=evaluate({'dataset':'transfer'})
    win=next(r for r in s['windows'] if r['id']=='00001-V2')
    assert win['owner_center']=='02' and win['handoff']==HO
    picked=next(r for r in s['selected_results'] if r['primary_id']=='00001-V1')
    assert picked['owner_center']=='01'
    assert s['archive']['status']=='可冻结'

def test_freeze_seal_changes_when_handoff_evidence_changes():
    from app.modules.archive.rules import freeze
    s=evaluate({'dataset':'transfer'})
    tampered=deepcopy(s);tampered['center_evidence'][0]['code']='TAMPERED'
    assert freeze(tampered)['seal']!=s['archive']['seal']

def test_rerun_failure_keeps_previous_version(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from app import main, store
    monkeypatch.setattr(main,'DB_PATH',str(tmp_path/'rerun.sqlite'))
    c=TestClient(main.app)
    run=c.post('/api/runs',json={'dataset':'transfer'}).json()
    rid=run['manifest']['run_id']
    original_sha=run['manifest']['sha256']
    import app.main as mainmod
    def boom(*a,**k): raise RuntimeError('simulated recompute failure')
    with monkeypatch.context() as patch:
        patch.setattr(mainmod,'evaluate',boom)
        resp=c.post(f'/api/runs/{rid}/rerun',json={})
        assert resp.status_code==422 and resp.json()['code']=='RERUN_FAILED'
    stored=store.get(main.DB_PATH,rid)
    assert stored['manifest']['sha256']==original_sha
    again=c.post(f'/api/runs/{rid}/rerun',json={})
    assert again.status_code==200 and again.json()['manifest']['run_id']==rid

def test_retry_idempotent_same_run_id():
    a=evaluate({'dataset':'transfer'})
    b=evaluate({'dataset':'transfer'})
    assert a['manifest']['run_id']==b['manifest']['run_id']
    assert a['counts']['handoff_retry']==b['counts']['handoff_retry']==1

def test_unknown_subject_not_masked_by_center_rule():
    text=open('/workspace/sample_data/transfer.csv',encoding='utf-8').read()
    text+='GHOST,99999,V1,2026-10-15T08:00:00+08:00,2026-10-01T00:00:00+08:00,PRIMARY,,1.2,g/L,auto,1,02,HO-X\r\n'
    s=evaluate({'csv_text':text})
    assert any(q['id']=='GHOST' and q['code']=='UNKNOWN_SUBJECT' for q in s['quarantine'])
    assert not any(e['id']=='GHOST' for e in s['center_evidence'])

def test_fingerprint_ignores_transport_id_and_line():
    base={'id':'A','_line':2,'subject':'00001','visit':'V2','at':'t','enrolled':'e','kind':'PRIMARY',
          'parent':'','value':'1.2','unit':'g/L','protocol':'auto','revision':'1','center':'02','handoff':HO}
    other=dict(base,id='B',_line=9)
    assert fingerprint(base)==fingerprint(other)
    changed=dict(base,id='C',value='1.3')
    assert fingerprint(base)!=fingerprint(changed)
