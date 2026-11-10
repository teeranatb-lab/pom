"""Licensed local dictionary connector via TSV with mandatory source & license references.
It only proposes candidate meanings and does not write into Meaning Space.
"""
import csv


def import_dictionary_tsv(path, source_ref, license_ref):
    if not source_ref or not license_ref:raise ValueError('source and license required')
    with open(path,encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f,delimiter='\t')
        required={'language','surface_form','definition'}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError('missing TSV columns')
        proposed=[]
        for row in reader:
            if not all(row.get(c) for c in required):continue
            proposed.append({'language':row['language'],'proposed_surface':row['surface_form'],
                             'definition':row['definition'],'source_ref':source_ref,
                             'license_ref':license_ref,'status':'PROPOSED_NOT_IMPORTED'})
        return {'status':'CANDIDATES_ONLY','count':len(proposed),'candidates':proposed}
