# Ajustes puntuales detectados al compilar y comparar con el HTML publicado
import re
def fix(path, old, new):
    s = open(path, encoding="utf8").read()
    assert old in s, (path, old[:60])
    open(path, "w", encoding="utf8").write(s.replace(old, new, 1))

# Plantilla de sintaxis (no ejecutable)
fix("libro/04-estparynopa.Rmd", "```{r}\n  pairwise.wilcox.test(variable, grupo)",
    "```{r eval=FALSE}\n  pairwise.wilcox.test(variable, grupo)")
# En el HTML original este chunk no mostraba salida
fix("libro/01-intro.Rmd", "```{r}\n2 + 3\n```", "```{r eval=FALSE}\n2 + 3\n```")
# Chunk oculto reconstruido a partir de su salida publicada (Titanic) ;
# la prueba chi-cuadrado publicada (X-squared = 190.4, df = 3) lo confirma
s = open("libro/05-tabcontingencia.Rmd", encoding="utf8").read()
s = re.sub(r"```\{r echo=FALSE, eval=FALSE\}\n# TODO: chunk oculto.*?```",
           "```{r titanic-datos, echo=FALSE}\ndf <- as.data.frame(Titanic)\nhead(df)\n```", s, count=1, flags=re.S)
open("libro/05-tabcontingencia.Rmd", "w", encoding="utf8").write(s)
fix("libro/05-tabcontingencia.Rmd", r"(\^2\_{(3)}=19.4, p-valor \< 0.001)",
    r"($\chi^2_{(3)}=190.4$, p-valor $< 0.001$)")
# Corchetes literales que pandoc escapó y MathJax interpretaba como ecuación
s = open("libro/02-reglas.Rmd", encoding="utf8").read()
s = s.replace(r"\[media muestral ± 1,96 EEM (error estándar de la media)\]", "[media muestral ± 1,96 EEM (error estándar de la media)]")
open("libro/02-reglas.Rmd", "w", encoding="utf8").write(s)
