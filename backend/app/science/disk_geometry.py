"""Deterministic equal projected-area disk quadrature on the unit sky sphere."""
import math
import numpy as np
from app.science.kernels import ScienceError


def angular_radius(radius_km, distance_km):
    if not all(math.isfinite(x) for x in (radius_km, distance_km)) or not 0 < radius_km < distance_km:
        raise ScienceError('DISK_GEOMETRY_INVALID', 'Require 0 < radius < distance in kilometres')
    return math.degrees(math.asin(radius_km / distance_km))


def basis(azimuth_deg, elevation_deg):
    if not math.isfinite(elevation_deg) or not -90 <= elevation_deg <= 90:
        raise ScienceError('DISK_GEOMETRY_INVALID', 'Invalid elevation')
    if azimuth_deg is None:
        if abs(elevation_deg) != 90:
            raise ScienceError('DISK_GEOMETRY_INVALID', 'Missing nonpolar azimuth')
        azimuth_deg = 0  # basis orientation only; never returned as a polar direction
    if not math.isfinite(azimuth_deg) or not 0 <= azimuth_deg < 360:
        raise ScienceError('DISK_GEOMETRY_INVALID', 'Invalid azimuth')
    a,e=np.deg2rad([azimuth_deg,elevation_deg])
    centre=np.array([np.cos(e)*np.sin(a),np.cos(e)*np.cos(a),np.sin(e)])
    horizontal=np.array([np.cos(a),-np.sin(a),0.])
    vertical=np.cross(horizontal,centre)
    return centre,horizontal,vertical


def disk_samples(azimuth_deg, elevation_deg, radius_deg, count):
    """Antipodal pairs in equal projected-area annuli, golden-angle orientations.

    Coordinates x,y are on the orthographic apparent disk. z=sqrt(1-x²-y²)
    puts each direction on the sphere. Weights describe apparent projected
    area, NOT surface area, solar flux, or Earth illuminated fraction.
    """
    if type(count) is not int or count < 4 or count > 1024 or count % 2:
        raise ScienceError('DISK_GEOMETRY_INVALID', 'Even sample count in [4,1024] required')
    if not math.isfinite(radius_deg) or not 0 < radius_deg < 90:
        raise ScienceError('DISK_GEOMETRY_INVALID', 'Radius must be in (0,90) degrees')
    c,u,v=basis(azimuth_deg,elevation_deg)
    m=count//2
    r=np.sqrt((np.arange(m)+.5)/m)*math.sin(math.radians(radius_deg))
    t=(np.arange(m)+.5)*math.pi*(3-math.sqrt(5))
    x=np.r_[r*np.cos(t),-r*np.cos(t)]
    y=np.r_[r*np.sin(t),-r*np.sin(t)]
    vectors=np.sqrt(1-x*x-y*y)[:,None]*c+x[:,None]*u+y[:,None]*v
    result=[]
    for east,north,up in vectors:
        h=math.hypot(east,north)
        az=None if h<1e-14 else math.degrees(math.atan2(east,north))%360
        result.append((az,math.degrees(math.atan2(up,h)),1/count))
    return result


def sampled_fraction(samples, lookup):
    """Exact-direction evidence only. Partial maxima prove blockage, not visibility."""
    if not samples or any(not math.isfinite(el) or not -90<=el<=90 or
        not math.isfinite(w) or w<=0 or (az is not None and (not math.isfinite(az) or not 0<=az<360))
        for az,el,w in samples) or not math.isclose(sum(w for az,el,w in samples),1,abs_tol=1e-12):
        raise ScienceError('DISK_GEOMETRY_INVALID','Invalid quadrature directions or weights')
    visible=blocked=unknown=0.
    for az,el,weight in samples:
        ray=lookup(az) if az is not None else None
        if ray is None or ray.coverage_status=='UNKNOWN': unknown+=weight
        elif ray.coverage_status=='COMPLETE_SAMPLED_RANGE':
            if el>ray.horizon_elevation_deg: visible+=weight
            else: blocked+=weight
        elif el<=ray.partial_max_obstruction_deg: blocked+=weight
        else: unknown+=weight
    state='UNKNOWN' if unknown else 'FULL' if not blocked else 'NONE' if not visible else 'PARTIAL'
    return dict(state=state,visible_fraction=None if unknown else visible,
                known_visible_fraction=visible,known_blocked_fraction=blocked,unknown_fraction=unknown,
                visible_fraction_lower_bound=visible,visible_fraction_upper_bound=min(1.,visible+unknown))
