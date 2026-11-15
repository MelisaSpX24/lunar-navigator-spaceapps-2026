"""Optional genuine uploaded LOLA integrations; synthetic fixtures never substitute."""
import os
from pathlib import Path
import pytest
from rasterio.windows import Window
from app.data.dem import open_dem
from app.data.coordinates import validate_coordinates
from app.data.quality import QualityLayer
from app.data.lola import lola_reference
from app.data.errors import DemError
from data_pipeline.lola_validation import inspected_reference, inspected_product, HASHES
from test_dem_quality import quality

@pytest.fixture
def directory():
 value=os.environ.get('NASA_LOLA_VALIDATION_DIR')
 if not value: pytest.skip('Genuine four-file LOLA validation package absent')
 return Path(value)

def test_real_site01_height_quality_and_coverage(directory):
 path=directory/'Site01_final_adj_5mpp_surf.tif'
 ref=inspected_reference(path)
 layers=[QualityLayer(path=directory/n,product=inspected_product(directory/n),sha256=HASHES[n]) for n in HASHES if 'toterr' in n or 'ldec' in n]
 with open_dem(path,ref) as dem:
  sample=dem.sample(validate_coordinates(-89.468,222.6),allow_unverified_registration=True,quality_layers=layers)
  assert sample.status=='VALID' and sample.surface_elevation_m==pytest.approx(1942.1014404296875,abs=1e-8)
  assert (sample.row_zero_based,sample.column_zero_based)==(1574,1616)
  assert sample.quality.status=='QUALITY_LAYERS_PRESENT'
  values={q.kind:q.value for q in sample.quality.layers}
  assert values['COUNT']==0
  assert values['HEIGHT_ERROR']==pytest.approx(0.22997184097766876,abs=1e-10)
  assert ref.product_version is None and ref.version_evidence
  for radius in (1000,3000,5000):
   result=dem.coverage(sample.location,radius,allow_unverified_registration=True)
   assert result.fractions()['raster_bounds_fraction']==1
   assert result.fractions()['valid_height_fraction']==1

def test_real_product90_80m_identity_sample_and_window(directory):
 path=directory/'LDEM_80S_80MPP_ADJ.TIF'
 with open_dem(path,inspected_reference(path)) as dem:
  assert dem.ds.res==(80,80) and dem.ds.width==7600
  sample=dem.sample(validate_coordinates(-89.468,222.6),allow_unverified_registration=True)
  assert sample.status=='VALID' and sample.surface_elevation_m==pytest.approx(1942.8433837890625,abs=1e-8)
  a,_=dem.read_elevation_window(Window(sample.column_zero_based-100,sample.row_zero_based-100,200,200))
  assert a.count()==a.size

def test_unknown_lola_version_requires_explicit_evidence(tmp_path):
 layer=quality(tmp_path,kind='HEIGHT_ERROR')
 p=layer.product.model_copy(update={'kind':'ELEVATION','family':'PGDA Product 78','height_datum':'HEIGHT_ABOVE_REFERENCE_SPHERE','version':None})
 with pytest.raises(DemError,match='SOURCE_METADATA_INCOMPLETE'):
  lola_reference(layer.path,p,vertical_evidence='Synthetic explicit datum evidence')
 r=lola_reference(layer.path,p,vertical_evidence='Synthetic explicit datum evidence',version_evidence='Synthetic absence of release number')
 assert r.product_version is None and not r.product_specific_frame_verified

def test_pinned_identity_rejects_wrong_file(tmp_path):
 p=tmp_path/'Site01_final_adj_5mpp_surf.tif';p.write_bytes(b'wrong')
 with pytest.raises(DemError,match='SOURCE_HASH_MISMATCH'): inspected_reference(p)
