import numpy as np
import pytest

from spectralbridge.pft_method_audit import (
    AuditConfig, envelope_critical, method_statistics, npc_probability, wavelength_weights,
)
from spectralbridge.plant_pft_statistics import contrast


def test_weights_preserve_gaps_and_grid_invariance():
    np.testing.assert_allclose(wavelength_weights([400,405,410,1500,1505]),[.5/3,1/3,.5/3,.5/3,.5/3])
    with pytest.raises(ValueError):
        wavelength_weights([400,400])
    with pytest.raises(ValueError):
        wavelength_weights([400,1500])


def test_legacy_maximum_reproduced_and_envelope_matches_global_decision():
    rng=np.random.default_rng(6)
    z=np.tile([0,1],20)
    blocks=np.repeat([0,1],20)
    y=rng.normal(size=(40,8))+z[:,None]*.8
    cfg=AuditConfig(permutations=499)
    result=method_statistics(y,z,blocks,np.arange(400,440,5),config=cfg,seed=7)
    old=contrast(y,z,blocks,permutations=499,bootstraps=19,seed=7)
    assert result['p']['max']==old['p']
    c=envelope_critical(result['stats'][1:,0],.05)
    assert (result['stats'][0,0]>c)==(result['p']['max']<=.05)
    assert np.allclose(result['curves'][0],old['beta'])


def test_small_exact_randomization_and_conservative_ties():
    y=np.array([-1.,0.,2.,3.])[:,None]*np.array([1.,2.])[None,:]
    result=method_statistics(y,[0,0,1,1],[0]*4,[400,405],config=AuditConfig(permutations=9999),seed=8)
    assert abs(result['p']['max']-1/3)<.02
    assert abs(result['p']['npc']-1/3)<.02
    assert npc_probability(np.ones((10,2)))==1
    assert envelope_critical([1,2,3],.01)==float('inf')


def test_energy_detects_distribution_difference_without_large_mean_effect():
    rng=np.random.default_rng(11)
    z=np.repeat([0,1],30)
    a=rng.normal(size=(30,6))*.05
    b=np.repeat([-1.,1.],15)[:,None]+rng.normal(size=(30,6))*.05
    r=method_statistics(np.vstack([a,b]),z,np.zeros(60),np.arange(400,430,5),config=AuditConfig(permutations=999),seed=22)
    assert r['p']['energy']<=.01
    assert r['p']['max']>.05


def test_perfect_acquisition_confounding_not_treated_as_effect():
    z=np.array([0,0,0,1,0,1,1,1])
    blocks=np.repeat([0,1],4)
    y=np.repeat([0.,100.],4)[:,None]+np.array([0,-1,1,0,0,-1,1,0])[:,None]*[1.,2.,3.]
    r=method_statistics(y,z,blocks,[400,405,410],config=AuditConfig(permutations=199),seed=33)
    assert r['p']['npc']>.05
    assert r['pcs']<=3


def test_whole_curve_units_and_no_missing_imputation():
    rng=np.random.default_rng(8)
    y=rng.normal(size=(20,5))
    y[:,2]=np.nan
    r=method_statistics(y,np.tile([0,1],10),np.zeros(20),[400,405,1400,1500,1505],config=AuditConfig(permutations=39),seed=1)
    assert r['curves'].shape==(40,4)
    assert 2 not in r['columns']
    assert all(0<p<=1 for p in r['p'].values())


def test_npc_is_not_an_uncorrected_minimum_probability():
    stats=np.column_stack([np.arange(20)[::-1],np.arange(20)])
    # Observation is maximum for component 1; another row wins component 2.
    assert npc_probability(stats)==.1


def test_energy_matches_direct_two_sample_v_statistic():
    from scipy.spatial.distance import cdist
    y=np.array([[1.,2.],[2.,3.],[4.,5.],[7.,6.]])
    z=np.array([1,1,0,0])
    r=method_statistics(y,z,np.zeros(4),[400,405],config=AuditConfig(permutations=39),seed=4)
    centered=y-y.mean(axis=0)
    scale=np.sqrt((centered**2).sum(axis=0)/3)
    weighted=centered/scale*np.sqrt([.5,.5])
    aa,bb=weighted[:2],weighted[2:]
    expected=2*cdist(aa,bb).mean()-cdist(aa,aa).mean()-cdist(bb,bb).mean()
    assert np.isclose(r['stats'][0,2],expected)


def test_complete_audit_reproduces_legacy_and_validates_restart(tmp_path,monkeypatch):
    import pandas as pd
    import spectralbridge.pft_method_audit as audit
    import spectralbridge.plant_pft_statistics as legacy
    name='NEON_D13_NIWO_DP1_L001-1_20230815_directional_reflectance'
    records=[]
    for i,species in enumerate(['Abies grandis']*3+['Alnus rubra']*3):
        records.append(dict(GlobalID=str(i),species=species,flight_id=name,
                            source_image=name+'.img',source_parquet=name+'_polygons_merged_pixel_extraction.parquet',
                            polygon_id=i,corr_wl400nm=float(i),corr_wl405nm=-float(i),corr_wl410nm=float(i*i)))
    observations=pd.DataFrame(records)
    def inputs(_):
        return None,None,{'corr':(observations,[])},{},{'source':'synthetic'}
    monkeypatch.setattr(legacy,'_model_inputs',inputs)
    monkeypatch.setattr(audit,'_model_inputs',inputs)
    monkeypatch.setattr(legacy,'_plot_summary',lambda *_:None)
    monkeypatch.setattr(legacy,'_plot_effects',lambda *_:None)
    monkeypatch.setattr(audit,'_plot_envelopes',lambda *_:None)
    oldroot=tmp_path/'legacy'
    legacy.run_pft_statistics(tmp_path,oldroot,config=legacy.PFTStatisticsConfig(stages=('corr',),permutations=39,bootstraps=39,min_plants=2))
    root=tmp_path/'audit'
    result=audit.run_method_audit(tmp_path,oldroot,root,config=AuditConfig(permutations=39))
    assert len(result)==2 and result.status.eq('tested').all()
    np.testing.assert_allclose(result.p_max,result.legacy_max_p)
    before=(root/'method_comparison.csv').stat().st_mtime_ns
    audit.run_method_audit(tmp_path,oldroot,root,config=AuditConfig(permutations=39))
    assert before==(root/'method_comparison.csv').stat().st_mtime_ns
    checkpoint=next((root/'checkpoints').glob('*.npz'))
    checkpoint.write_bytes(b'invalid bytes')
    with pytest.raises(ValueError,match='checkpoint checksum'):
        audit.run_method_audit(tmp_path,oldroot,root,config=AuditConfig(permutations=39))
