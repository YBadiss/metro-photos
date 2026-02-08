import L from "leaflet";

export const MAPTILER_KEY = import.meta.env.VITE_MAPTILER_KEY || "PL2jHQqSB8xZ7Bp6aXpF";

export function createTileLayer(maxZoom: number): L.TileLayer {
  return L.tileLayer(
    `https://api.maptiler.com/maps/streets-v4/{z}/{x}/{y}.png?key=${MAPTILER_KEY}`,
    {
      attribution:
        '&copy; <a href="https://www.maptiler.com/copyright/">MapTiler</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom,
    },
  );
}

export function createPieChartIcon(colors: string[], size: number, dimmed = false): L.DivIcon {
  const radius = size / 2;
  const center = size / 2;

  if (!colors || colors.length === 0) {
    colors = ["#ff7800"];
  }

  let svgSegments = "";
  const opacity = dimmed ? 0.2 : 1;

  if (colors.length === 1) {
    svgSegments = `<circle cx="${center}" cy="${center}" r="${radius - 1}" fill="${colors[0]}" stroke="#000" stroke-width="1" opacity="${opacity}"/>`;
  } else {
    const anglePerSegment = 360 / colors.length;

    colors.forEach((color, index) => {
      const startAngle = index * anglePerSegment;
      const endAngle = (index + 1) * anglePerSegment;
      const startRad = ((startAngle - 90) * Math.PI) / 180;
      const endRad = ((endAngle - 90) * Math.PI) / 180;
      const x1 = center + (radius - 1) * Math.cos(startRad);
      const y1 = center + (radius - 1) * Math.sin(startRad);
      const x2 = center + (radius - 1) * Math.cos(endRad);
      const y2 = center + (radius - 1) * Math.sin(endRad);
      const largeArcFlag = anglePerSegment > 180 ? 1 : 0;
      const pathData = `M ${center},${center} L ${x1},${y1} A ${radius - 1},${radius - 1} 0 ${largeArcFlag},1 ${x2},${y2} Z`;
      svgSegments += `<path d="${pathData}" fill="${color}" stroke="#000" stroke-width="0.5" opacity="${opacity}"/>`;
    });

    svgSegments += `<circle cx="${center}" cy="${center}" r="${radius - 1}" fill="none" stroke="#000" stroke-width="1" opacity="${opacity}"/>`;
  }

  const svg = `<svg width="${size}" height="${size}" xmlns="http://www.w3.org/2000/svg">${svgSegments}</svg>`;

  return L.divIcon({
    html: svg,
    className: "pie-chart-marker",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

export function createEntranceIcon(color: string, size: number): L.DivIcon {
  const r = size / 2;
  const svg = `<svg width="${size}" height="${size}" xmlns="http://www.w3.org/2000/svg">
    <circle cx="${r}" cy="${r}" r="${r - 1.5}" fill="white" stroke="${color}" stroke-width="2.5"/>
    <circle cx="${r}" cy="${r}" r="${r * 0.25}" fill="${color}"/>
  </svg>`;

  return L.divIcon({
    html: svg,
    className: "entrance-marker",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}
