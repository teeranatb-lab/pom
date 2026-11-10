"""Optional BigMap/GIS coordinate transformation. Requires pyproj.

Separate GIS geography coordinates from OLGM abstract 3D semantic coordinates.
Check transform quality/accuracy against survey control points before field use.
"""
import csv
from pathlib import Path


class BigMapGIS:
    WGS84='EPSG:4326'
    INDIAN_1975_UTM48N='EPSG:24048'
    def __init__(self):
        try:
            from pyproj import CRS,Transformer
            self.source=CRS.from_user_input(self.WGS84)
            self.target=CRS.from_user_input(self.INDIAN_1975_UTM48N)
            self.trans=Transformer.from_crs(self.source,self.target,always_xy=True)
            self.reverse=Transformer.from_crs(self.target,self.source,always_xy=True)
        except Exception as exc:
            raise RuntimeError('pyproj_required_or_CRS_unavailable') from exc

    def wgs84_to_indian_utm48(self,lat,lon,height=None):
        lat=float(lat);lon=float(lon)
        if not -90<=lat<=90 or not -180<=lon<=180:
            raise ValueError('latitude or longitude out of range')
        x,y=self.trans.transform(lon,lat)
        if not (0<x<2000000 and 0<y<11000000):
            raise ValueError('unexpected projected coordinate')
        return {'X':x,'Y':y,'Z':None if height is None else float(height),
                'target_crs':self.INDIAN_1975_UTM48N,'input_crs':self.WGS84,
                'transform_description':str(self.trans.description),
                'accuracy_m_reported':self.trans.accuracy,
                'field_accuracy_certified':False}

    def indian_utm48_to_wgs84(self,x,y):
        lon,lat=self.reverse.transform(float(x),float(y))
        return {'lat':lat,'lon':lon,'crs':self.WGS84}

    def convert_csv(self,source_file,destination_file,lat_col='lat',lon_col='lon',height_col=None):
        src=Path(source_file);dst=Path(destination_file)
        if src.resolve()==dst.resolve():raise ValueError('source and output must differ')
        n=0
        with src.open(encoding='utf-8-sig',newline='') as f, dst.open('w',encoding='utf-8',newline='') as g:
            reader=csv.DictReader(f)
            if not reader.fieldnames or not {lat_col,lon_col}.issubset(set(reader.fieldnames)):
                raise ValueError('latitude longitude columns not present')
            writer=csv.writer(g);writer.writerow(['X','Y','Z'])
            for row in reader:
                pt=self.wgs84_to_indian_utm48(row[lat_col],row[lon_col],
                      row[height_col] if height_col and row.get(height_col) not in ('',None) else None)
                writer.writerow([f'{pt["X"]:.3f}',f'{pt["Y"]:.3f}',
                                  '' if pt['Z'] is None else pt['Z']]);n+=1
        return {'status':'EXPORTED','points':n,'path':str(dst),
                'target_crs':self.INDIAN_1975_UTM48N,'survey_validation':'NOT_TESTED'}
