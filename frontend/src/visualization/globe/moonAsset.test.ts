import { readFileSync } from 'node:fs'
import { createHash } from 'node:crypto'
import { expect, it } from 'vitest'
import { VERIFIED_TEXTURE_URL } from './moonTexture'

const bytes = readFileSync('public/assets/moon/lroc_color_2k.jpg')

it('keeps the exact user-supplied JPEG bytes and checksum', () => {
  expect(bytes.length).toBe(457942)
  expect([...bytes.subarray(0, 3)]).toEqual([0xff, 0xd8, 0xff])
  expect([...bytes.subarray(-2)]).toEqual([0xff, 0xd9])
  expect(createHash('sha256').update(bytes).digest('hex')).toBe('f7130a1822681fa7512d7dcfd40db8c10b9ba4f06777910348698260ed7a2170')
})

it('declares 2048 × 1024 in a valid JPEG start-of-frame segment', () => {
  let offset = 2
  let size: [number, number] | null = null
  while (offset < bytes.length - 4) {
    expect(bytes[offset]).toBe(0xff)
    const marker = bytes[offset + 1]!
    const length = bytes.readUInt16BE(offset + 2)
    expect(length).toBeGreaterThanOrEqual(2)
    if ([0xc0, 0xc1, 0xc2].includes(marker)) {
      size = [bytes.readUInt16BE(offset + 7), bytes.readUInt16BE(offset + 5)]
      break
    }
    if (marker === 0xda || marker === 0xd9) break
    offset += 2 + length
  }
  expect(size).toEqual([2048, 1024])
})

it('uses the Vite base for a local asset and never a remote NASA image request', () => {
  expect(VERIFIED_TEXTURE_URL).toBe(`${import.meta.env.BASE_URL}assets/moon/lroc_color_2k.jpg`)
  expect(VERIFIED_TEXTURE_URL).not.toMatch(/^https?:/)
})
