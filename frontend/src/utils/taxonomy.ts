import type { TaxonomyFacet, TaxonomyNode } from '../api/taxonomy'

export interface TaxonomyOption<T extends string | number = number> {
  label: string
  value: T
  searchText: string
  disabled: boolean
  path: string[]
  node: TaxonomyNode
}

export const FACET_LABELS: Record<string, string> = {
  gallery_series: '专区',
  source_type: '来源',
  campus: '校区',
  photo_type: '类别',
  building: '楼宇',
  facility: '设施',
  landscape: '景观',
  gallery_year: '届次/年份',
  award_level: '奖项',
  season: '季节',
  natural_phenomenon: '自然现象',
  technique: '表现手法',
  animal: '动物',
  plant: '植物',
  documentary_topic: '纪实主题',
  tag: '补充标签',
  landmark: '楼宇',
}

export const TAXONOMY_FILTER_KEYS = [
  'gallery_series',
  'campus',
  'photo_type',
  'source_type',
  'building',
  'facility',
  'landscape',
  'gallery_year',
  'award_level',
  'season',
  'natural_phenomenon',
  'technique',
  'animal',
  'plant',
  'documentary_topic',
] as const

export const GALLERY_FILTER_KEYS = [
  'gallery_series',
  'campus',
  'photo_type',
  'building',
  'facility',
  'landscape',
  'gallery_year',
  'award_level',
  'season',
  'natural_phenomenon',
  'technique',
  'animal',
  'plant',
  'documentary_topic',
] as const

export function isNodeSelectable(node: TaxonomyNode) {
  return node.is_selectable ?? !(node.children || []).length
}

export function flattenTaxonomyOptions<T extends string | number = number>(
  nodes: TaxonomyNode[],
  valueFor: (node: TaxonomyNode) => T = (node) => node.id as T,
  parentPath: string[] = [],
): TaxonomyOption<T>[] {
  return nodes.flatMap((node) => {
    const path = [...parentPath, node.name]
    const aliases = (node.aliases || []).map((alias) => alias.alias).join(' ')
    return [
      {
        label: path.join(' / '),
        value: valueFor(node),
        searchText: `${path.join(' ')} ${aliases}`.toLowerCase(),
        disabled: !isNodeSelectable(node),
        path,
        node,
      },
      ...flattenTaxonomyOptions(node.children || [], valueFor, path),
    ]
  })
}

export function findTaxonomyNode(facet: TaxonomyFacet | undefined, nodeId: number | null | undefined) {
  if (!facet || !nodeId) return null
  const stack = [...facet.nodes]
  while (stack.length) {
    const node = stack.shift()
    if (!node) continue
    if (node.id === nodeId) return node
    stack.push(...(node.children || []))
  }
  return null
}

export function sanitizeTaxonomySelection(
  facets: TaxonomyFacet[],
  values: Record<string, number | number[]>,
) {
  const byKey = new Map(facets.map((facet) => [facet.key, facet]))
  const result: Record<string, number | number[]> = {}

  Object.entries(values).forEach(([facetKey, value]) => {
    const facet = byKey.get(facetKey)
    if (!facet || value == null) return
    const ids = Array.isArray(value) ? value : [value]
    const selectableIds = ids.filter((id) => {
      const node = findTaxonomyNode(facet, id)
      return node ? isNodeSelectable(node) : false
    })
    if (!selectableIds.length) return
    result[facetKey] = Array.isArray(value) ? selectableIds : selectableIds[0]
  })

  return result
}

export function facetLabel(facetKey: string, facets: TaxonomyFacet[] = []) {
  return facets.find((facet) => facet.key === facetKey)?.name || FACET_LABELS[facetKey] || facetKey
}
