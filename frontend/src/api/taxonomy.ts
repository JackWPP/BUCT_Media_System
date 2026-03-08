import request from './index'

export interface TaxonomyAlias {
  id: number
  alias: string
  created_at: string
}

export interface TaxonomyNode {
  id: number
  facet_id: number
  parent_id: number | null
  key: string
  name: string
  description: string | null
  sort_order: number
  is_active: boolean
  created_at: string
  updated_at: string
  aliases: TaxonomyAlias[]
  children: TaxonomyNode[]
}

export interface TaxonomyFacet {
  id: number
  key: string
  name: string
  description: string | null
  selection_mode: 'single' | 'multiple'
  is_system: boolean
  is_active: boolean
  sort_order: number
  created_at: string
  updated_at: string
  nodes: TaxonomyNode[]
}

export interface TaxonomyFacetCreate {
  key: string
  name: string
  description?: string
  selection_mode?: 'single' | 'multiple'
  is_system?: boolean
  is_active?: boolean
  sort_order?: number
}

export interface TaxonomyNodeCreate {
  key: string
  name: string
  description?: string
  parent_id?: number | null
  sort_order?: number
  is_active?: boolean
  aliases?: string[]
}

export function getPublicTaxonomy() {
  return request.get<TaxonomyFacet[]>('/api/v1/taxonomy/public')
}

export function getTaxonomyFacets() {
  return request.get<TaxonomyFacet[]>('/api/v1/taxonomy/facets')
}

export function createTaxonomyFacet(data: TaxonomyFacetCreate) {
  return request.post<TaxonomyFacet>('/api/v1/taxonomy/facets', data)
}

export function updateTaxonomyFacet(facetId: number, data: Partial<TaxonomyFacetCreate>) {
  return request.patch<TaxonomyFacet>(`/api/v1/taxonomy/facets/${facetId}`, data)
}

export function createTaxonomyNode(facetId: number, data: TaxonomyNodeCreate) {
  return request.post<TaxonomyNode>(`/api/v1/taxonomy/facets/${facetId}/nodes`, data)
}

export function updateTaxonomyNode(nodeId: number, data: Partial<TaxonomyNodeCreate>) {
  return request.patch<TaxonomyNode>(`/api/v1/taxonomy/nodes/${nodeId}`, data)
}

export function deleteTaxonomyNode(nodeId: number) {
  return request.delete(`/api/v1/taxonomy/nodes/${nodeId}`)
}
