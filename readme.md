# scraping-retail

Repositorio: [lovera00/scraping-retail](https://github.com/lovera00/scraping-retail)

## Descripción

Este proyecto es un scraper diseñado para extraer información de productos de tiendas online de retail. Actualmente soporta la extracción de datos desde sitios como "Superseis" y "Stock". Utiliza Selenium para automatizar la navegación y extracción de datos, aplicando patrones CSS y expresiones regulares para identificar y procesar la información relevante de productos, como el nombre, precio, id, categoría, y más.

## Instalación

1. Clona el repositorio a tu máquina local:
    ```bash
    git clone https://github.com/lovera00/scraping-retail.git
    cd scraping-retail
    ```

2. Crea y activa un entorno virtual (opcional, pero recomendado):
    ```bash
    python -m venv env
    source env/bin/activate   # En Linux/Mac
    env\Scripts\activate      # En Windows
    ```

3. Instala las dependencias necesarias:
    ```bash
    pip install -r requirements.txt
    ```
    Asegúrate de tener instalado [Google Chrome](https://www.google.com/chrome/) y de disponer del [ChromeDriver](https://sites.google.com/chromium.org/driver/) compatible con tu versión de Chrome en tu PATH.

## Uso

El scraper se ejecuta desde la línea de comandos y requiere dos parámetros: el identificador del scraper a utilizar y el archivo de salida para almacenar los datos extraídos.

### Ejemplo

Para utilizar el scraper de "Superseis":
```bash
python main.py s6 salida_superseis.json
```

Para utilizar el scraper de "Stock":
```bash
python main.py stock salida_stock.json
```

