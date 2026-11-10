"""Offline retrieval and semantic benchmark harness with explicit per-query evidence.
Benchmarks are not proof of general AI intelligence or genuine model weight updates.
"""
import json
import math
from collections import Counter
from pathlib import Path
from .semantic import grams
from .training import sha256_file


def rank_bm25(query,records,k=20):
    """Character-bigram BM25 (Thai-friendly approximate lexical baseline)."""
    q=list(grams(query))
    documents=[list(grams(x['text'])) for x in records]
    df=Counter(t for doc in documents for t in set(doc))
    avgdl=sum(len(x) for x in documents)/max(1,len(documents))
    n=len(documents);r=[]
    for x,doc in zip(records,documents):
        tf=Counter(doc)
        score=0
        for token in q:
            if token not in tf:continue
            idf=math.log(1+(n-df[token]+0.5)/(df[token]+0.5))
            score+=idf*tf[token]*2.2/(tf[token]+1.2*(0.25+0.75*len(doc)/max(avgdl,1)))
        r.append((score,x['cid']))
    return [cid for s,cid in sorted(r,key=lambda x:(-x[0],x[1]))[:k]]


def metric_ranking(predicted, relevant, k):
    rel=set(relevant)
    ranked=predicted[:k]
    recall=len(set(ranked)&rel)/len(rel) if rel else 0.0
    dcg=sum((1 if cid in rel else 0)/math.log2(i+2) for i,cid in enumerate(ranked))
    ideal=sum(1/math.log2(i+2) for i in range(min(k,len(rel))))
    return {'recall':recall,'ndcg':dcg/ideal if ideal else 0}


def evaluate_retrieval(eval_path,search_fn,k_list=(5,20)):
    """JSONL: {'query':str,'relevant_cids':[str]}; callable search_fn(q,k)->cid list."""
    rows=[]
    with open(eval_path,encoding='utf-8') as f:
        for line_no,line in enumerate(f,1):
            if not line.strip():continue
            item=json.loads(line)
            if not isinstance(item.get('query'),str) or not isinstance(item.get('relevant_cids'),list):
                raise ValueError(f'bad_eval_item:{line_no}')
            pred=search_fn(item['query'],max(max(k_list),10))
            metrics={f'Recall@{k}':metric_ranking(pred,item['relevant_cids'],k)['recall'] for k in k_list}
            metrics['nDCG@10']=metric_ranking(pred,item['relevant_cids'],10)['ndcg']
            rows.append({'query_id':item.get('id',str(line_no)),'predicted':pred,
                         'reference':item['relevant_cids'],'metrics':metrics})
    if not rows:return {'status':'BLOCKED','reason':'empty_eval'}
    keys=rows[0]['metrics']
    summary={m:sum(row['metrics'][m] for row in rows)/len(rows) for m in keys}
    return {'status':'EVALUATED','items':len(rows),'aggregate':summary,
            'examples':rows,'eval_sha256':sha256_file(eval_path),
            'blind_evaluation_certified':False,'data_leakage_audit':'NOT_TESTED'}
