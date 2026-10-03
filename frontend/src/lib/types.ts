export type Result = 'applies' | 'superseded' | 'unknown' | 'not_yet_effective' | 'pending'

export interface AddressHit {
  address_id: string
  street_address: string
  postal_city: string
  state: string
  zip: string
  jurisdiction_city: string | null
  year_built: number | null
  units: number | null
  units_min: number | null
}

export interface ResultItem {
  team_rule_id: string
  result: Result
  explanation: string
  conflict_flag: boolean
  category: string
  category_label: string
  jurisdiction: string
  level: 'state' | 'city'
  title: string
  requirement: string
  requirement_es?: string | null
  title_es?: string | null
  key_value_es?: string | null
  key_value: string | null
  citation: string
  quoted_span: string
  source_url: string
  source_doc_id: string | null
  retrieved_at: string | null
  effective_date: string | null
  status: string
  confidence: number | null
  conflict_note: string | null
  interaction: string | null
  source_origin: string | null
}

export interface LookupAnswer {
  as_of: string
  disclaimer: string
  address: {
    address_id: string
    street_address: string
    postal_city: string
    state: string
    zip: string
    year_built: number | null
    units: number | null
    units_min: number | null
    units_basis: string
    use_description: string
    jurisdiction_state: string
    jurisdiction_city: string | null
    resolution_method: string
    matched_address: string | null
    census_place: string | null
    source_dataset: string
  }
  jurisdiction_stack: string[]
  results: ResultItem[]
  no_rule_findings: { jurisdiction: string; category: string; finding: string; quoted_span: string; source_url: string }[]
  categories_without_rules: { category: string; category_label: string }[]
  summary: Record<string, number>
}

export interface Rule {
  team_rule_id: string
  jurisdiction: string
  level: string
  category: string
  status: string
  instrument_status: string
  title: string
  requirement: string
  key_value: string | null
  coverage_conditions: string | null
  exemptions: string | null
  effective_date: string | null
  citation: string
  source_doc_id: string | null
  source_url: string
  quoted_span: string
  confidence: number | null
  conflict_flag: boolean
  conflict_note: string | null
  interaction: string | null
  overrides: string[]
  source_origin: string | null
  retrieved_at: string | null
}

export interface ChangeTest {
  test: { test_id: string; title?: string; type?: string; expected_behavior?: string; as_of?: string; as_of_before?: string; as_of_after?: string }
  affected_address_ids: string[]
  conflict_flag_address_ids: string[]
  notes: string
  mapped_rules: Record<string, string[]>
  detail: Record<string, Record<string, unknown>>
}

export interface Meta {
  default_as_of: string
  disclaimer: string
  categories: Record<string, string>
  n_rules: number
  n_addresses: number
  rules_by_status: Record<string, number>
  rules_by_jurisdiction: Record<string, number>
}
