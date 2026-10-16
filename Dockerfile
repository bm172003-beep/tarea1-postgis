# PostgreSQL 16 + PostGIS + hstore + herramientas de GDAL (ogr2ogr, ogrinfo).
# Igual al del Lab 05; solo se agrega hstore al script de inicio de un volumen nuevo
# (OSM guarda las etiquetas libres en other_tags, que se carga como hstore).
FROM postgres:16-bookworm

RUN apt-get update \
 && apt-get install -y --no-install-recommends gdal-bin postgis postgresql-16-postgis-3 \
 && rm -rf /var/lib/apt/lists/* \
 && printf 'CREATE EXTENSION IF NOT EXISTS postgis;\nCREATE EXTENSION IF NOT EXISTS hstore;\n' \
      > /docker-entrypoint-initdb.d/10_extensiones.sql
