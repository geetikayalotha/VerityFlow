# Input contract

`verityflow` accepts one JSON object. The reader rejects anything else with the source path in the
message, so a wrong file is a one-line error rather than a traceback.

A note must carry a `claim`; sources, quotations and links are optional. Every link's `confidence` is
a weight: a finite number in `[0, 1]`, with `null` meaning "use the default".

Run `python -m unittest discover -s tests -v` to check the boundary.
