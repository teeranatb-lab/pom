"""Incremental non-destructive 3D graph placement for new meaning cores.

Distance is topology-inspired, NOT an embedding-validated semantic distance.
Existing CID positions are never automatically moved, reclassified or erased.
"""
import hashlib
import json
import math
import sqlite3


class GraphPlacement:
    def __init__(self,meaning_space):self.ms=meaning_space

    def propose(self,cid,near_cids=(),min_distance=0.01):
        if self.ms.get_core(cid):raise ValueError('cannot relocate existing CID')
        if min_distance<=0:raise ValueError('min_distance must be positive')
        with self.ms._conn() as db:
            raw=db.execute('SELECT cid,semantic_coordinates FROM meaning_cores WHERE semantic_coordinates IS NOT NULL').fetchall()
        positions={r['cid']:json.loads(r['semantic_coordinates']) for r in raw}
        anchors=[positions[c] for c in near_cids if c in positions]
        if anchors:
            centroid=[sum(v[i] for v in anchors)/len(anchors) for i in range(3)]
        else:centroid=[0.0,0.0,0.0]
        digest=hashlib.sha256(cid.encode('utf-8')).digest()
        theta=2*math.pi*int.from_bytes(digest[:8],'big')/(2**64)
        z=2*int.from_bytes(digest[8:16],'big')/(2**64)-1
        radius=math.sqrt(max(0,1-z*z))
        direction=[math.cos(theta)*radius,math.sin(theta)*radius,z]
        for attempt in range(1,10000):
            delta=min_distance*(2+attempt*0.75)
            proposal=[round(centroid[i]+direction[i]*delta,8) for i in range(3)]
            if all(math.dist(proposal,other)>=min_distance for other in positions.values()):
                return {'status':'PROPOSED_3D_PLACEMENT','cid':cid,'coords':proposal,
                        'neighbor_cids':list(near_cids),'repositioned_existing':False,
                        'semantic_accuracy':'NOT_TESTED_GRAPH_HEURISTIC'}
        raise RuntimeError('unable to find free placement')

    def add_new(self,cid,language,surface,definition,origin_ref,near_cids=()):
        p=self.propose(cid,near_cids)
        self.ms.add_core(cid,language,surface,definition,coords=p['coords'],origin_ref=origin_ref)
        return {'status':'PLACED_CANDIDATE_MEANING','cid':cid,'coords':p['coords'],
                'semantic_validation':'NOT_TESTED','existing_positions_unchanged':True}
