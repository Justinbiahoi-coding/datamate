import sys,json; sys.path.insert(0,'code')
from agent import exec_code, infer_type
from loader import load_business
from scorer import match_answer
Q={json.loads(l)['id']:json.loads(l) for l in open('batches_retry4/retry4_000.jsonl')}
def run(qid,code):
    q=Q[qid]; biz=load_business(__import__('pathlib').Path('train/data/'+q['business_id']))
    try:
        r=exec_code(code,biz,q['as_of_date'])
    except Exception as e:
        print(qid,'ERR',repr(e)[:300]); return None
    pt,pv=infer_type(r)
    ok=match_answer(pt,pv,q['_gold_type'],q['_gold_answer'],q['_gold_alias'])
    print(qid,pt,pv,'->',ok); 
    # log
    v='correct' if ok else 'wrong'
    return dict(id=qid,type=pt,answer=pv,_code=code,_verdict=v,ok=bool(ok))
def save(r,att=1):
    if r is None: return
    r=dict(r); r.pop('ok',None); r['_attempts']=att
    open('/tmp/w/res.jsonl','a').write(json.dumps(r,ensure_ascii=False)+'\n')
