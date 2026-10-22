#!/bin/bash
set -e
R=src/rbook_met_estad; B=libro
for pair in "index:index" "intro:01-intro" "reglas:02-reglas" "eda:03-eda" "estparynopar:04-estparynopa" "tabcontingencia:05-tabcontingencia" "correglin:06-correglineal" "rls:07-rls"; do
  h=${pair%%:*}; r=${pair##*:}; python3 html2rmd.py $R/docs/$h.html $B/$r.Rmd images/recuperadas
done
python3 html2rmd.py hist/rlm.html $B/08-rlm.Rmd images/recuperadas
sed -i 's#~/Books_CienciaDatos/rbook_metodos_estadisticos/data/#data/#' $B/08-rlm.Rmd
rm -f $B/*.json
cat index_header.txt $B/index.Rmd > $B/index.tmp && mv $B/index.tmp $B/index.Rmd
python3 ajustes_manual.py
