# Uppsala 2012 — reproducibility note

The frozen runners have been preserved byte-for-byte from the publication
package. The package used to build this repo snapshot did **not** contain every
runner-local prerequisite that exists in the original research working tree.
Those files are therefore not fabricated or reconstructed here.

## Missing runner-local archived inputs

The following files are referenced by one or more runners but are not present in
the supplied publication package:

- `RESCUE_UPPSALA_CONTROL_PREMATCH_DATA_v0.1.csv`
- `RESCUE_FIRE_B20_MUNICIPALITY_YEAR_WITH_POP_v0.1.1.csv`
- `RESCUE_UPPSALA_2012_SECONDARY_DIAGNOSTIC_REQUESTS_v0.1.csv`
- `RESCUE_UPPSALA_2012_HALMSTAD_SENSITIVITY_ACTIVATION_PATCH_v0.1.json`
- `RESCUE_UPPSALA_2011_ANTICIPATION_ACTIVATION_PATCH_v0.1.json`
- `RESCUE_UPPSALA_2015_MEASUREMENT_EDGE_ACTIVATION_PATCH_v0.1.json`

The first two are shared pre-treatment inputs. The others document later
prespecified activation/diagnostic steps.

## Already included

Where an exact dependency *was* present elsewhere in the supplied package, it
has been copied into the appropriate runner directory without modification,
including locked primary estimates, primary post data and the augmented control
pre-match file.

## Policy

Do not regenerate missing frozen inputs from newer data. Add the original files
byte-for-byte from the working archive and verify them against their associated
manifests/hashes where available.
