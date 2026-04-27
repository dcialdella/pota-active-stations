# POTA Active Stations

Dashboard que muestra las estaciones POTA activas en tiempo real en las bandas de 20m, 40m, 15m y 17m en modo SSB.

## Funcionamiento

1. El script `fetch_pota.py` consulta la API pública de POTA (`https://api.pota.app/spot/activator`)
2. Filtra las estaciones según los criterios configurados
3. Genera un archivo HTML con una interfaz visual atractiva

## Filtros Aplicados

- **Bandas**: 20m (14.000-14.350 kHz), 40m (7.000-7.200 kHz), 15m (21.000-21.450 kHz), 17m (18.068-18.168 kHz)
- **Modo**: Solo SSB
- **Referencia**: Se excluyen referencias que empiezan con `US-` (estaciones desde USA)

## Instalacion

```bash
# Clonar el repositorio
git clone https://github.com/dcialdella/pota-active-stations.git
cd pota-active-stations

# Crear entorno virtual (opcional)
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependencias
pip install requests
```

## Uso

```bash
# Ejecutar manualmente
python3 fetch_pota.py

# O usar el script bash
./run_fetch.sh
```

Esto genera el archivo `pota_active_stations.html` que podés abrir en tu navegador.

## Ejecucion automatica con cron (cada 5 minutos)

```bash
# Editar crontab
crontab -e

# Agregar esta linea (ajusta la ruta a tu directorio)
*/5 * * * * /usr/bin/python3 /Users/cialdeld/Downloads/ia-pota-simple/fetch_pota.py >> /Users/cialdeld/Downloads/ia-pota-simple/fetch.log 2>&1
```

Tambien podés ejecutar el shell script directamente:

```bash
*/5 * * * * /Users/cialdeld/Downloads/ia-pota-simple/run_fetch.sh >> /Users/cialdeld/Downloads/ia-pota-simple/fetch.log 2>&1
```

## Archivo de salida

- `pota_active_stations.html` - Dashboard con las estaciones activas

## Dependencias

- Python 3.8+
- requests
- curl (incluido en macOS/Linux)