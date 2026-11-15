import { SRGBColorSpace, TextureLoader, type Texture } from 'three'

export const NASA_PAGE = 'https://svs.gsfc.nasa.gov/4720/'
export const NASA_IMAGE = 'https://svs.gsfc.nasa.gov/vis/a000000/a004700/a004720/lroc_color_2k.jpg'
// User-supplied original JPEG verified by bytes, decoding, dimensions and the
// user-provided checksum. This is not an independent NASA-server checksum.
export const VERIFIED_TEXTURE_URL = `${import.meta.env.BASE_URL}assets/moon/lroc_color_2k.jpg`
export const TEXTURE_UNAVAILABLE = 'NASA texture unavailable — geometric preview only'

export async function loadMoonTexture(url: string): Promise<Texture> {
  const texture = await new TextureLoader().loadAsync(url)
  texture.colorSpace = SRGBColorSpace
  texture.anisotropy = 1
  return texture
}
