# Versionierung

Zunder Zapfe verwendet für fachliche Releases eine semantische Version und
ergänzt sie in laufenden Installationen um Git-Informationen. Der vollständige
Buildstring wird auf der Idle-Oberfläche und am Health-Endpunkt angezeigt.

## Anzeigeformat

```text
zzapfe_v<major>.<minor>.<patch>_<phase>.<iteration>_<commit-number>_g<short-hash>
```

Beispiel:

```text
zzapfe_v0.2.0_alpha.1_14_g2700c1a
```

Die Bestandteile bedeuten:

- `0.2.0`: fachlicher Releaseumfang nach `MAJOR.MINOR.PATCH`;
- `alpha.1`: Reifegrad und Iteration;
- `14`: fortlaufende Anzahl der Git-Commits im Repository;
- `g2700c1a`: kurzer Git-Commit-Hash, eingeleitet durch `g`.

Unterstriche trennen die für Menschen sichtbaren Abschnitte. Die technische
Python-Paketversion verwendet weiterhin die von Python-Werkzeugen erwartete
PEP-440-Schreibweise und kann deshalb anders normalisiert dargestellt werden.

## Erhöhungsregeln

- Vor der ersten Hardwarefreigabe bleibt die Major-Version `0`.
- Ein neuer abgeschlossener Milestone erhöht in der Regel `MINOR`.
- Eine reine kompatible Fehlerkorrektur erhöht `PATCH`.
- Sichtbare Reviewstände eines Milestones erhöhen die Alpha-Iteration.
- `1.0.0` ist erst nach realer Hardwareintegration, Kalibrierung und
  Sicherheitsabnahme vorgesehen.

Commitanzahl und Hash werden zur Laufzeit aus dem Checkout ermittelt und nicht
manuell gepflegt. Ein unbekannter Git-Stand wird deutlich als `unknown`
gekennzeichnet; er darf nicht als freigegebener Zielsystemstand gelten.
