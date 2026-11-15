import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach, vi } from 'vitest'

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockImplementation(async () => new Response(JSON.stringify({status:'ok',science_ready:false,dem_ready:false,kernels_ready:false,reason_codes:['SCIENCE_ENGINE_NOT_READY']}))))
})
afterEach(() => { cleanup(); vi.unstubAllGlobals() })
