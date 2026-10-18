"""Repository-reviewed qualification trust root, outside receipt self-custody.

No accepted actual qualification exists. Adding an exact path/size/SHA tuple
requires a separate reviewed source change after independent outcome acceptance.
This module must never be part of the receipt's self-authenticated source roster:
that would make each receipt hash depend on the hash of its own embedded pin.
There are no caller-supplied paths, configuration or environment overrides.
"""

TRUSTED_QUALIFICATION_PINS = ()
