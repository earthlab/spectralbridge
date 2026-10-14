"""Research labels must include unlabeled-species patches and preserve identity."""
import numpy as np
import pandas as pd
import pytest

from spectralbridge.researcher_pft_statistics import category_metadata, run_researcher_statistics
from spectralbridge.pft_method_audit import AuditConfig


def test_category_audit_accepts_missing_species_but_rejects_conflict(tmp_path):
    source = tmp_path/'input.parquet'
    frame = pd.DataFrame({'GlobalID':['a','a','b'],'cover_category':['Herbaceous','Herbaceous','Woody shrub'],'species':[None,None,'Species one']})
    frame.to_parquet(source)
    assert len(category_metadata(source)) == 2
    frame.loc[1,'cover_category']='Evergreen'
    frame.to_parquet(source)
    with pytest.raises(ValueError,match='Conflicting'):
        category_metadata(source)


def test_researcher_run_keeps_species_null_polygons_and_reuses_results(tmp_path):
    rows=[]
    flight='NEON_D13_NIWO_DP1_20230701_120000_reflectance'
    for category,offset in [('Herbaceous',0),('Evergreen',5)]:
        for i in range(4):
            for pixel in range(2):
                rows.append(dict(GlobalID=f'{category}{i}',cover_category=category,species=None,
                                 flight_id=flight,source_image=flight,source_parquet=flight+'_merged.parquet',
                                 polygon_id=i,aop_site='NIWO',
                                 **{f'corr_b{j:03}_wl{w}nm':offset+i*.1+pixel*.02+j*.03
                                    for j,w in enumerate([400,405,410,415],1)}))
    source=tmp_path/'input.parquet'
    pd.DataFrame(rows).to_parquet(source)
    original=source.read_bytes()
    out=tmp_path/'results'
    result=run_researcher_statistics(source,out,config=AuditConfig(permutations=19),minimum=2)
    assert set(result.status)=={'tested'}
    assert set(result.n_a)=={4}
    spectra=pd.read_parquet(out/'polygon_year_spectra.parquet')
    assert len(spectra)==8
    assert set(spectra.cover_category)=={'Herbaceous','Evergreen'}
    assert source.read_bytes()==original
    mtimes={p:p.stat().st_mtime_ns for p in out.rglob('*') if p.is_file()}
    again=run_researcher_statistics(source,out,config=AuditConfig(permutations=19),minimum=2)
    np.testing.assert_allclose(result.p_npc,again.p_npc)
    assert mtimes=={p:p.stat().st_mtime_ns for p in mtimes}


def test_missing_identity_or_category_is_rejected(tmp_path):
    source=tmp_path/'input.parquet'
    for field in ['GlobalID','cover_category']:
        frame=pd.DataFrame({'GlobalID':['a'],'cover_category':['Herbaceous'],'species':[None]})
        frame.loc[0,field]=None
        frame.to_parquet(source)
        with pytest.raises(ValueError,match='Missing'):
            category_metadata(source)
