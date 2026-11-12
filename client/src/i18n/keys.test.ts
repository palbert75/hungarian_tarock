import { describe, expect, it } from 'vitest'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import en from './en.json'
import hu from './hu.json'

function flatten(obj: Record<string, unknown>, prefix = ''): string[] {
  return Object.entries(obj).flatMap(([key, value]) =>
    value && typeof value === 'object' ? flatten(value as Record<string, unknown>, `${prefix}${key}.`) : [`${prefix}${key}`]
  )
}

function sources(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name)
    if (statSync(path).isDirectory()) return sources(path)
    return /\.tsx?$/.test(name) && !/\.test\./.test(name) ? [path] : []
  })
}

describe('translations', () => {
  const enKeys = flatten(en).sort()
  const huKeys = flatten(hu).sort()

  it('has the same keys in Hungarian and English', () => {
    expect(huKeys).toEqual(enKeys)
  })

  it('has no empty text', () => {
    for (const [name, dict] of [['en', en], ['hu', hu]] as const) {
      const flat = JSON.stringify(dict)
      expect(flat.includes('""'), `${name} has an empty text`).toBe(false)
    }
  })

  it('has every key the code uses', () => {
    const used = new Set<string>()
    for (const file of sources(join(__dirname, '..'))) {
      const text = readFileSync(file, 'utf8')
      for (const match of text.matchAll(/\bt\(\s*'([a-zA-Z0-9_.]+)'/g)) used.add(match[1])
      for (const match of text.matchAll(/'((?:error|toast|hint)\.[a-zA-Z0-9_]+)'/g)) used.add(match[1])
    }
    const missing = [...used].filter((key) => !enKeys.includes(key))
    expect(missing).toEqual([])
    expect(used.size).toBeGreaterThan(80)
  })

  it('keeps the same placeholders in both languages', () => {
    const get = (dict: unknown, key: string) =>
      key.split('.').reduce<any>((node, part) => node?.[part], dict) as string
    const holes = (text: string) => (text.match(/\{\{\w+\}\}/g) || []).sort()
    for (const key of enKeys) {
      expect(holes(get(hu, key)), key).toEqual(holes(get(en, key)))
    }
  })
})
