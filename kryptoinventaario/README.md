# Kryptoinventaario – SOTE-palveluntarjoajan kyselypohja (v1.0)

Excel-pohja (`Kryptoinventaario_pohja_v1.0.xlsx`) kartoittaa palveluntarjoajan yksiköiden
oman ja asiakkaiden palvelutuotannon järjestelmät sekä niissä käytetyn kryptografian
(protokollat, algoritmit, avaimet, varmenteet, avainten hallinta, kvanttihaavoittuvuus).
Jokainen yksikkö (n. 30 kpl) saa oman kopion täytettäväksi.

Tässä hakemistossa xlsx on base64-muodossa osissa (`Kryptoinventaario_pohja_v1.0.xlsx.b64.001` … `.015`),
koska käytettävissä olevat GitHub-työkalut eivät tue binäärisiirtoa suoraan.

## Muunna xlsx:ksi

```bash
cd kryptoinventaario
cat Kryptoinventaario_pohja_v1.0.xlsx.b64.0* > Kryptoinventaario_pohja_v1.0.xlsx.b64
base64 -d Kryptoinventaario_pohja_v1.0.xlsx.b64 > Kryptoinventaario_pohja_v1.0.xlsx
# macOS: base64 -D -i Kryptoinventaario_pohja_v1.0.xlsx.b64 -o Kryptoinventaario_pohja_v1.0.xlsx
sha256sum Kryptoinventaario_pohja_v1.0.xlsx
# odotettu: b5b77f1d8bc3ba2d353c6db9e550af120cd8711b7b9edb3ed51229db8844c265
```

## Pohjan sisältö (7 välilehteä)

- **Ohjeet** – tarkoitus, täyttöohjeet, tietoturva, lyhenteet, ylläpitäjän täytettävät kohdat (kohta 5: palautuspäivä, yhteyshenkilö, palautuskanava – täytä ennen lähetystä)
- **Yksikön tiedot** – yksikön ja vastaajan tiedot (pakolliset merkitty `*`)
- **Järjestelmäinventaario** – yksi rivi per järjestelmä: nimi, käyttötarkoitus, omistaja, toimittaja, ympäristö, oma/asiakkaiden palvelutuotanto, henkilötiedot, erityiset tietoryhmät; ID:t (J01…) automaattiset; 25 riviä valmiina (kopioi rivi alaspäin tarvittaessa)
- **Kryptoinventaario** – yksi rivi per krypton käyttökohde: käyttötarkoitus (12 vaihtoehtoa), protokolla/algoritmi, avaimen pituus, kirjasto/versio, CA, avainten hallinta, voimassaolo, kvanttihaavoittuva (kyllä/ei/ei varma), korvaussuunnitelma, aikataulu; järjestelmän nimi haetaan automaattisesti ID:llä
- **Yhteenveto** – automaattiset COUNTIF-laskelmat
- **Esimerkki** – ohjeellinen täytetty esimerkki
- **Listat** – piilotettu välilehti pudotusvalikoiden arvoille (voi paljastaa muokattavaksi)

Pudotusvalikot on toteutettu nimetyillä alueilla; otsikkorivejä ja kaavasarakkeita ei tule muokata.
