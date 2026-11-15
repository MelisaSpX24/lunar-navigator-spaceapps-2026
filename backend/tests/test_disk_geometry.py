"""Analytic/synthetic checks; no NASA data fixtures."""
import math
from types import SimpleNamespace as Ray
import numpy as np
import pytest
from app.science.disk_geometry import angular_radius,basis,disk_samples,sampled_fraction

def flat(h=0):return lambda az:Ray(coverage_status='COMPLETE_SAMPLED_RANGE',horizon_elevation_deg=h)

@pytest.mark.parametrize('radius,distance',[(1,10),(6371,384400),(695700,149600000)])
def test_radius(radius,distance):
    assert angular_radius(radius,distance)==pytest.approx(math.degrees(math.asin(radius/distance)))

@pytest.mark.parametrize('r,d',[(0,1),(-1,2),(1,0),(1,1),(2,1),(float('nan'),10),(1,float('inf'))])
def test_invalid_radius(r,d):
    with pytest.raises(RuntimeError):angular_radius(r,d)

@pytest.mark.parametrize('az,el',[(0,0),(359.99,0),(90,45),(None,90),(None,-90)])
def test_basis_disk(az,el):
    c,u,v=basis(az,el);np.testing.assert_allclose(np.array([c,u,v])@np.array([c,u,v]).T,np.eye(3),atol=1e-14)
    points=disk_samples(az,el,.27,64)
    assert points==disk_samples(az,el,.27,64)
    assert sum(w for a,e,w in points)==1
    for a,e,w in points:
        d=basis(a,e)[0]
        assert np.dot(c,d)>=math.cos(math.radians(.27))-1e-14
        assert a is None or 0<=a<360

@pytest.mark.parametrize('n',[64,256,1024])
@pytest.mark.parametrize('ratio',[-2,-1,-.5,0,.5,1,2])
def test_analytic_segments(n,ratio):
    radius=.27
    f=sampled_fraction(disk_samples(0,ratio*radius,radius,n),flat())
    q=max(-1,min(1,ratio))
    expected=(math.acos(-q)+q*math.sqrt(1-q*q))/math.pi
    # Boundary-cell quadrature error O(N^-1/2); fixed envelope is 1/sqrt(N).
    # Small-angle planar/spherical discrepancy here is <1e-5.
    assert abs(f['visible_fraction']-expected)<=1/math.sqrt(n)+1e-5
    if ratio==0: assert f['visible_fraction']==.5
    if ratio>=1:assert f['state']=='FULL'
    if ratio<=-1:assert f['state']=='NONE'

@pytest.mark.parametrize('r',[.1,.27,1.,2.])
def test_half_disk_radius(r):assert sampled_fraction(disk_samples(359.99,0,r,256),flat())['visible_fraction']==.5

def test_unknown_and_partial_asymmetry():
    samples=[(0,1,.5),(90,-1,.5)]
    partial=lambda az:Ray(coverage_status='INCOMPLETE',partial_max_obstruction_deg=0)
    r=sampled_fraction(samples,partial)
    assert r['state']=='UNKNOWN' and r['visible_fraction'] is None
    assert (r['known_blocked_fraction'],r['unknown_fraction'])==(.5,.5)
    assert (r['visible_fraction_lower_bound'],r['visible_fraction_upper_bound'])==(0,.5)
    assert sampled_fraction(samples,lambda az:None)['unknown_fraction']==1

def test_variable_ridge():
    samples=disk_samples(90,0,1,256)
    assert sampled_fraction(samples,lambda a:flat(2 if a>90 else -2)(a))['state']=='PARTIAL'

@pytest.mark.parametrize('samples',[[],[(0,0,0)],[(0,0,2)],[(0,float('nan'),1)],[(None,0,-1)],[(360,0,1)]])
def test_invalid_quadrature(samples):
    with pytest.raises(RuntimeError):sampled_fraction(samples,flat())

@pytest.mark.parametrize('e,state',[(.1,'PARTIAL'),(-.1,'PARTIAL')])
def test_center_does_not_determine_disk(e,state):
    assert sampled_fraction(disk_samples(0,e,.27,256),flat())['state']==state
