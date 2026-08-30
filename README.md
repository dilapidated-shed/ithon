# i-thon

ithon  
python with assignment arrows

companion to ick, icky, grease, ir, idriç

meant to be written with a programmers keyboard

## Checked execution receipt

Set `ITHON_CHECK_RECEIPT` to a file path when a consumer needs an executable
record of which Ithon source was checked. Each successful whole-module check
appends one JSON line containing the source path and SHA-256 digests of the
Ithon source and the lowered source. A failed check writes no receipt.
