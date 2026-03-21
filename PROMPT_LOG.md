# PROMPT_LOG.md

This file stores verbatim user prompts for Codex work in this repository.

- New entries should be appended, not rewritten.
- Prompts should be logged verbatim in fenced `text` blocks.
- Logging begins with the request that introduced this file; older prompts were not backfilled automatically.

## 2026-03-21 - add AGENTS guidance and prompt logging
Branch: main

```text
this repo doesn't have an AGENTS.md file for agents for codex to reference. can you read through the repo and the webstie and try to use that information to write an AGENTS.md file to speed up future work. one thing i would like it to include is a prompt log that logs the verbatim promplts that i give codex.
```

## 2026-03-21 - fix ruff syntax errors in drone pipeline
Branch: main

```text
Run ruff check src tests
invalid-syntax: Expected a newline after line continuation character
   --> src/spectralbridge/pipelines/drone.py:404:51
    |
402 |     try:
403 |         files = ", ".join(
404 |             [f"'{str(Path(path)).replace(chr(39), \"''\")}'" for path in outputs]
    |                                                   ^
405 |         )
406 |         con.execute(
    |

invalid-syntax: Cannot use an escape sequence (backslash) in f-strings on Python 3.10 (syntax was added in Python 3.12)
   --> src/spectralbridge/pipelines/drone.py:404:51
    |
402 |     try:
403 |         files = ", ".join(
404 |             [f"'{str(Path(path)).replace(chr(39), \"''\")}'" for path in outputs]
    |                                                   ^
405 |         )
406 |         con.execute(
    |

invalid-syntax: Unparenthesized generator expression cannot be used here
   --> src/spectralbridge/pipelines/drone.py:404:52
    |
402 |     try:
403 |         files = ", ".join(
404 |             [f"'{str(Path(path)).replace(chr(39), \"''\")}'" for path in outputs]
    |                                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
405 |         )
406 |         con.execute(
    |

invalid-syntax: Cannot reuse outer quote character in f-strings on Python 3.10 (syntax was added in Python 3.12)
   --> src/spectralbridge/pipelines/drone.py:404:52
    |
402 |     try:
403 |         files = ", ".join(
404 |             [f"'{str(Path(path)).replace(chr(39), \"''\")}'" for path in outputs]
    |                                                    ^
405 |         )
406 |         con.execute(
    |

invalid-syntax: Cannot use an escape sequence (backslash) in f-strings on Python 3.10 (syntax was added in Python 3.12)
   --> src/spectralbridge/pipelines/drone.py:404:55
    |
402 |     try:
403 |         files = ", ".join(
404 |             [f"'{str(Path(path)).replace(chr(39), \"''\")}'" for path in outputs]
    |                                                       ^
405 |         )
406 |         con.execute(
    |

invalid-syntax: Expected `,`, found `]`
   --> src/spectralbridge/pipelines/drone.py:404:81
    |
402 |     try:
403 |         files = ", ".join(
404 |             [f"'{str(Path(path)).replace(chr(39), \"''\")}'" for path in outputs]
    |                                                                                 ^
405 |         )
406 |         con.execute(
    |

invalid-syntax: f-string: unterminated string
   --> src/spectralbridge/pipelines/drone.py:405:10
    |
403 |         files = ", ".join(
404 |             [f"'{str(Path(path)).replace(chr(39), \"''\")}'" for path in outputs]
405 |         )
    |          ^
406 |         con.execute(
407 |             "COPY (SELECT * FROM read_parquet(["
    |

invalid-syntax: f-string: expecting `}`
   --> src/spectralbridge/pipelines/drone.py:406:9
    |
404 |             [f"'{str(Path(path)).replace(chr(39), \"''\")}'" for path in outputs]
405 |         )
406 |         con.execute(
    |         ^^^
407 |             "COPY (SELECT * FROM read_parquet(["
408 |             + files
    |

invalid-syntax: Expected `,`, found `finally`
   --> src/spectralbridge/pipelines/drone.py:412:5
    |
410 |             [str(output_path)],
411 |         )
412 |     finally:
    |     ^^^^^^^
413 |         con.close()
414 |     return output_path
    |

invalid-syntax: Expected `,`, found `:`
   --> src/spectralbridge/pipelines/drone.py:412:12
    |
410 |             [str(output_path)],
411 |         )
412 |     finally:
    |            ^
413 |         con.close()
414 |     return output_path
    |

invalid-syntax: Expected `]`, found newline
   --> src/spectralbridge/pipelines/drone.py:413:20
    |
411 |         )
412 |     finally:
413 |         con.close()
    |                    ^
414 |     return output_path
    |

invalid-syntax: Expected `)`, found dedent
   --> src/spectralbridge/pipelines/drone.py:414:5
    |
412 |     finally:
413 |         con.close()
414 |     return output_path
    |     ^
    |

Found 12 errors.
Error: Process completed with exit code 1.
```

## 2026-03-21 - add drone-specific QA plot workflow
Branch: main

```text
can you fix that? build off of the neon qa plot and do it for the drone. we want to confirm that the original ENVI was created correctly and that the bands are faithful, then we want to plot the BRDF correction so that we can see what and how much was adjusted. We get a bunch of -9999 from those first steps and we need to plot wehre all the -9999 are to make sure that went OK. Then we need to see the polygons are over the flightline so we're extracting real data and then we want to show a preview of the merged table to confirm that it worked. This is a special modification for the drone pipeline that differes a bit from the neon pipeline
```
