# Metro Photos

This project aims to gather pictures of all metro entrances in Paris and link them to their entrance, station, and lines.

## Data

The data used in this repo originates from IDFM's efforts to open their internal data: https://data.iledefrance-mobilites.fr

You will find the source data in `./data/source_data_files`, and the result of my clean up/filter in `./data/generated_data_files`.

The final model we use is [zones_metro.json](./data/generated_data_files/zones_metro.json) which lists all metro stations, their entrances, and their lines.

### Model

```mermaid
erDiagram
  "Access<br>(acces.json)" }o--o{ "relations-acces.json" : "access.id"
  "Zone<br>(zones-d-arrets.json)" }o--o{ "relations-acces.json" : "zone.id"
  "Line<br>(emplacement-des-gares-idf.json)" }o--|| "Zone<br>(zones-d-arrets.json)" : "zone.id"
```

### Source Files

- [acces.json](./data/source_data_files/acces.json): [IDFM Link](https://data.iledefrance-mobilites.fr/explore/dataset/acces)
- [emplacement-des-gares-idf.json](./data/source_data_files/emplacement-des-gares-idf.json): [IDFM Link](https://data.iledefrance-mobilites.fr/explore/dataset/emplacement-des-gares-idf)
- [relations-acces.json](./data/source_data_files/relations-acces.json): [IDFM Link](https://data.iledefrance-mobilites.fr/explore/dataset/relations-acces)
- [zones-d-arrets.json](./data/source_data_files/zones-d-arrets.json): [IDFM Link](https://data.iledefrance-mobilites.fr/explore/dataset/zones-d-arrets)
