export interface GeoPoint {
  lon: number
  lat: number
}

export interface Access {
  id: string
  name: string
  short_name: number | null
  x_lambert_93: number
  y_lambert_93: number
  geo_point: GeoPoint
}

export interface Line {
  id: string
  name: string
  icon_url: string | null
  color?: string
}

export interface Zone {
  id: string
  name: string
  type: string | null
  town: string
  postal_region: string
  x_lambert_93: number
  y_lambert_93: number
  accesses: Access[]
  lines: Line[]
}
