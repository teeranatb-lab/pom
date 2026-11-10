"""Executable, bounded graph operations behind 1+18 cognitive method labels.
These graph operations are not generalized autonomous logical inference or a human brain.
"""
from collections import Counter
from math import dist
from .methods import METHODS,select_methods

TRANSITIVE={'is_a','part_of'}


class CognitiveMethods:
    def __init__(self,ms,semantic):self.ms,self.sem=ms,semantic

    def run(self,intent_tag,seed_cids,goal_cid=None,budget='normal',force_ids=None):
        ids=select_methods(intent_tag,budget) if force_ids is None else list(dict.fromkeys(force_ids))
        if any(i not in METHODS for i in ids):raise ValueError('unknown cognitive method id')
        nodes=self.sem.resonance(seed_cids,depth=2,limit=80)['candidates']
        cids=[x['cid'] for x in nodes]
        with self.sem._db() as db:
            rows=db.execute('SELECT * FROM semantic_edges').fetchall()
            edges=[dict(x) for x in rows if x['source_cid'] in cids or x['target_cid'] in cids]
        degrees=Counter()
        for e in edges:
            degrees[e['source_cid']]+=1;degrees[e['target_cid']]+=1
        by_type=Counter(e['relation_type'] for e in edges)
        outputs=[]
        for ident in ids:
            label=METHODS[ident];data={};valid='COMPUTED_GRAPH_OPERATION'
            if ident==1: data={'focus':'user-intent-origin-ref-only','core0_access':False}
            elif ident==2:data={'observed_graph_edges':[e['edge_id'] for e in edges[:30]],'note':'edges are stored assertions'}
            elif ident==3:
                nbrs={c:{e['target_cid'] for e in edges if e['source_cid']==c} for c in seed_cids}
                data={'common_neighbors':sorted(set.intersection(*nbrs.values())) if nbrs else []}
            elif ident==4:data={'categories':{c:self.ms.get_categories(c) for c in seed_cids},
                               'is_a_edges':[e['edge_id'] for e in edges if e['relation_type']=='is_a']}
            elif ident==5:
                coords={}
                for c in seed_cids:
                    obj=self.ms.get_core(c)
                    if obj and obj['semantic_coordinates']:
                        import json
                        coords[c]=json.loads(obj['semantic_coordinates'])
                pairs=[{'pair':[a,b],'semantic_euclidean_distance':dist(coords[a],coords[b])}
                       for i,a in enumerate(coords) for b in list(coords)[i+1:]]
                data={'coordinates':coords,'pairs':pairs,'warning':'latent semantic geometry is not geographical distance'}
            elif ident==6:data={'graph_degree':dict(degrees),'relation_counts':dict(by_type)}
            elif ident==7:
                chains=[]
                for x in edges:
                    if x['relation_type'] not in TRANSITIVE or self.sem.edge_status(x['edge_id'])!='VERIFIED':continue
                    for y in edges:
                        if y['relation_type']==x['relation_type'] and y['source_cid']==x['target_cid'] and self.sem.edge_status(y['edge_id'])=='VERIFIED':
                            chains.append({'from':x['source_cid'],'via':x['target_cid'],'to':y['target_cid'],
                                           'relation':x['relation_type'],'source_edges':[x['edge_id'],y['edge_id']],
                                           'status':'STRUCTURAL_DEDUCTION_NOT_REAL_WORLD_PROOF'})
                data={'derived_paths':chains[:30]}
            elif ident==8:data={'repeated_relation_patterns':by_type.most_common(10),
                               'epistemic_status':'HYPOTHESIS_NOT_CAUSAL_PROOF'}
            elif ident==9:data={'hypothesized_predecessors':[e['source_cid'] for e in edges if e['target_cid'] in seed_cids],
                               'epistemic_status':'HYPOTHESIS'}
            elif ident==10:data={'unverified_edges':[e['edge_id'] for e in edges if self.sem.edge_status(e['edge_id'])!='VERIFIED'],
                                'potential_conflicts':self.sem.detect_conflicts()[:20]}
            elif ident==11:data={'candidate_neighbors':list(dict.fromkeys(e['target_cid'] for e in edges))[:40]}
            elif ident==12:data={'lateral_two_hop':[x['path_cids'] for x in nodes if x['distance_hops']==2][:20]}
            elif ident==13:
                sigs={c:{e['relation_type'] for e in edges if e['source_cid']==c} for c in cids}
                data={'structural_analogies':[{'a':a,'b':b,'shared_types':sorted(sigs[a]&sigs[b])}
                    for i,a in enumerate(cids) for b in cids[i+1:] if sigs[a]&sigs[b]][:20]}
            elif ident==14:
                data={'assembled_relations':[{'from':e['source_cid'],'type':e['relation_type'],'to':e['target_cid']}
                                            for e in edges[:30]]}
            elif ident==15:data={'system_boundary':cids,'graph_degree':dict(degrees)}
            elif ident==16:data={'causal_hypotheses':[{'edge_id':e['edge_id'],'status':self.sem.edge_status(e['edge_id'])}
                                                     for e in edges if e['relation_type']=='causes'],
                                  'note':'causal edge alone does not establish causality'}
            elif ident==17:data={'what_if_paths':self.sem.candidate_paths(seed_cids[0],goal_cid,4)['candidate_paths']
                                 if seed_cids and goal_cid else [],'epistemic_status':'SCENARIO_ONLY'}
            elif ident==18:data={'graph_coverage':len(cids),'unknown_edges':sum(self.sem.edge_status(e['edge_id'])!='VERIFIED' for e in edges),
                                'unsupported_generalization':False}
            elif ident==19:data={'decision':'PENDING_EVIDENCE_POLICY_APPROVAL','selected_action':None}
            else:valid='NOT_TESTED'
            outputs.append({'method_id':ident,'method':label,'status':valid,'result':data})
        return {'selected':ids,'executions':outputs,'disclosure':'Structural methods are heuristics, not LLM reasoning or factual certification'}
