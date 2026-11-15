"""Pinned user-uploaded LOLA identities and reviewed documentation declarations.

No version number is invented. No NASA download or scientific READY promotion.
"""
from pathlib import Path
from app.data.manifest import Manifest, sha256_file
from app.data.lola import lola_reference
from app.data.errors import DemError

HASHES = {
 'Site01_final_adj_5mpp_surf.tif':'3ba7b97cb00a2bcf21189c3aeb535f65afc21207154ab9f0d43c5bdc1f7e747e',
 'Site01_final_adj_5mpp_toterr.tif':'cf2cf52f52d2aa51e60d058010d10b0ebfb1d3e920f5a2b9a46eb6c51054ab1c',
 'Site01_final_adj_5mpp_ldec.tif':'16d6ed21020ad48fa71d94e7437492acf5bf04118f52bcd292f57f22ead4cd23',
 'LDEM_80S_80MPP_ADJ.TIF':'82030dcbdd7c4bb0c7d858e9b4b293b9f2cda5a543ba31ec0f42784bd6beee5a',
}
VERTICAL_EVIDENCE = ('PGDA products/78 and products/90 document metre surface heights; '
 'NASA https://svs.gsfc.nasa.gov/4720 documents the LRO 1737.4 km reference sphere; '
 'actual GeoTIFF spherical axes are 1737400 m. Product README could not be fetched. '
 'Evidence combines product unit documentation, mission reference convention and actual CRS; '
 'CRS alone is not vertical datum evidence.')
VERSION_EVIDENCE = 'No explicit release version found in inspected TIFF or reviewed PGDA page; exact file identified by supplied manifest SHA-256.'

def inspected_product(path):
 path=Path(path)
 if path.name not in HASHES or sha256_file(path)!=HASHES[path.name]:
  raise DemError('SOURCE_HASH_MISMATCH','Not the pinned uploaded LOLA product')
 manifest=Manifest.model_validate_json((Path(__file__).parent/'manifests/lola.json').read_text())
 product=next(p for p in manifest.products if p.filename==path.name)
 values=product.model_dump()
 values.update(local_path=str(path),sha256=HASHES[path.name],status='FILE_INSPECTED',version=None,
  limitations=['No explicit product release version; identity pinned by SHA-256.',
   'Source page documents MOON_ME DE421; absolute registration accuracy not independently measured.',
   'Metre/reference-sphere evidence from product pages, NASA LRO convention and actual CRS.'])
 if product.kind=='ELEVATION': values['height_datum']='HEIGHT_ABOVE_REFERENCE_SPHERE'
 return type(product).model_validate(values)

def inspected_reference(path):
 return lola_reference(path,inspected_product(path),vertical_evidence=VERTICAL_EVIDENCE,version_evidence=VERSION_EVIDENCE)
