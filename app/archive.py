import io, csv, json, zipfile
from app.errors import BusinessError

def serialize(result):
    if not result.get('manifest') or not result.get('views'):
        raise BusinessError('INCOMPLETE_RUN','批次尚未完成')
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('manifest.json',json.dumps({**result['manifest'],'revision':result.get('revision',1),'status':result.get('status','待复核')},ensure_ascii=False,indent=2))
        archive.writestr('evidence.json',json.dumps({'counts':result['counts'],'views':result['views'],'quarantine':result['quarantine']},ensure_ascii=False,indent=2))
        archive.writestr('handoff.json',json.dumps({'transfers':result['context'].get('transfers',{}),'centers':result['context'].get('centers',{}),
            'center_evidence':result.get('center_evidence',[]),'center_blocks':result.get('center_blocks',[])},ensure_ascii=False,indent=2))
        stream=io.StringIO()
        writer=csv.writer(stream)
        writer.writerow(['id','subject','visit','center','owner_center','handoff','code','detail','line'])
        for row in result.get('center_evidence',[]):
            writer.writerow([row.get(k,'') for k in ('id','subject','visit','center','owner_center','handoff','code','detail','line')])
        archive.writestr('handoff_evidence.csv',stream.getvalue())
    return buffer.getvalue()
