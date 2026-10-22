# Notas de métodos estadísticos: fuentes recuperadas

Estos `.Rmd` se reconstruyeron a partir del HTML publicado en GitHub Pages
(`cdeoroaguado/rbook_met_estad/docs`). Los nombres de archivo son los originales: salen
del enlace "Edit" de cada página.

## Compilar

1. Abre `rbook_met_estad.Rproj` en RStudio.
2. Instala los paquetes:
   ```r
   install.packages(c("bookdown", "tidyverse", "readxl", "fst", "car", "GGally", "rstatix",
                      "lmtest", "patchwork", "effsize", "Amelia", "scatterplot3d", "plotly",
                      "openintro", "olsrr", "nortest", "mctest", "gridExtra", "kableExtra"))
   ```
3. Ejecuta `bookdown::render_book("index.Rmd")`. El sitio queda en `docs/`, como antes.

## Qué se recuperó

- **Capítulos 1 a 7**: texto, ecuaciones, cajas (definición, teorema, ejemplo, etc.),
  tablas, referencias cruzadas y los 270 chunks de código, con sus etiquetas y `fig.cap`.
- **Capítulo 8, Regresión lineal múltiple (`08-rlm.Rmd`)**: ya no estaba publicado,
  pero se rescató del historial de git (commit `0d76372`, nov. 2025).
- **`data/`**: los 11 archivos de datos, tomados de tu repo `cdeoroaguado/Datos`.
- **`images/`, `style.css`**: copiados de `docs/`.

## Para revisar

- `book.bib`: `navidi2021` y `montgomery2012` se reconstruyeron a partir de las citas,
  porque la página de referencias publicada estaba vacía. Verifica edición y editorial.
- Chunks ocultos: solo había uno (`df <- as.data.frame(Titanic)` en tablas de contingencia),
  y se reconstruyó a partir de su salida.
- Las opciones de chunk que no dejan rastro en el HTML (`message=FALSE`, `fig.width`, …)
  no se pueden recuperar. Se usan los valores por defecto.
- Las cajas de color ahora usan sintaxis de pandoc (`::: {.admon-box .definicion}`) en
  lugar de `<div>` en HTML. Se ven igual.

**Importante:** sube también los `.Rmd` al repositorio, no solo `docs/`, para que esto no
vuelva a pasar.
