# Svensk Subsidiaritet — Evidence

Detta repo innehåller versionerade empiriska forskningsartefakter bakom delar av
[svensksubsidiaritet.se](https://svensksubsidiaritet.se): frysta protokoll,
institutionell treatment-historik, maskinläsbara resultat, reproducerbarhetskod
och evidenssynteser.

Målet är inte att samla alla arbetsfiler, utan att göra det möjligt att följa
hur en evidensbedömning har tagits fram, vilka designbeslut som låstes före
utfallsgranskning och vilka resultat som faktiskt observerades.

## Relation till simulations-repot

Beräkningsmodeller och simuleringar ligger separat i
`svensk-subsidiaritet-simulations`. Det repot svarar främst på *vad händer i
modellen?* Detta repo svarar främst på *vad stöder det empiriska och
metodologiska evidenskorpuset?*

## Innehåll

- [`evidence-matrix/`](evidence-matrix/) — aktuell versionerad evidensmatris.
- [`raddningstjanst/`](raddningstjanst/) — empiriskt forskningsprogram om svensk
  kommunal räddningstjänst, inklusive två oberoende kausala grenar:
  - Uppsala 2012: etablerad operativ samverkan `K` → formell pooled authority `A`;
  - Historical 2002: fem first-full-`A` institutionella transitions.

## Forskningsprincip

Frysta artefakter ändras inte i efterhand för att passa senare resultat.
Korrigeringar, amendments och nya analyser ska därför få nya versionsnummer och
behålla tidigare versioner när de är en del av den dokumenterade analyskedjan.

Detta är särskilt viktigt för:

- outcome-blind treatment reconstruction;
- estimator- och outcome-locks;
- post-unmask amendments;
- prespecificerade robustness-/sensitivity-steg;
- machine-readable manifests och hashes.

## Reproducerbarhet

Python-script använder huvudsakligen standardbiblioteket samt `requests` och
`numpy`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

En del runners hämtar data från externa svenska statistik-API:er och kräver
nätverksåtkomst. Körinstruktioner och eventuella saknade lokala arkivinputs
finns i respektive studiegren.

## GitHub Releases

Komprimerade frysta distributionspaket bör publiceras som **GitHub Release
assets**, inte checkas in som binära ZIP-filer i Git-historiken. Repo-trädet
innehåller därför de läsbara och maskinläsbara artefakterna, medan release-ZIP
kan byggas eller bifogas separat.

## Licens

- Kod: MIT, se [`LICENSE-CODE`](LICENSE-CODE).
- Data, resultat och text i detta repo: CC BY 4.0, se
  [`LICENSE-DATA`](LICENSE-DATA), om inte en enskild källfil anger annat.

Källdata från externa myndigheter behåller naturligtvis sina egna villkor; det
här repoets licens gör inte anspråk på externa rättigheter.

## Citering

Se [`CITATION.cff`](CITATION.cff).

---

## In English

Versioned empirical research artifacts behind parts of
svensksubsidiaritet.se: frozen protocols, institutional treatment histories,
machine-readable results, reproducibility code and evidence syntheses.
Computational simulation studies are maintained separately in
`svensk-subsidiaritet-simulations`.
