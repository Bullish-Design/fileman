# fileman

**Simple lsd JSON wrapper** - A minimalist tool that wraps the `lsd` command and outputs parsed filetree information as JSON.

## Overview

This project provides a simple wrapper around the `lsd` command that produces JSON-structured output. The parser is pre-built and imported via devenv.yaml - no grammar development or compilation needed!

## Features

- ✅ JSON output from `lsd --long`
- ✅ Pre-built parser (imported via devenv)
- ✅ No build steps required
- ✅ Simple Justfile commands
- ✅ Ready to use in minutes

## Quick Start

```bash
# Enter devenv shell (parser auto-imported)
devenv shell

# Use the wrapper
just lsd-parse /tmp

# Pretty print output
just demo /home/user

# Validate JSON
just test-json-valid .
```

## Documentation

- `CONCEPT_MVP_LSD.md` - MVP specification
- `AGENTS.md` - Agent guide for LLM assistants
- `.skills/` - Skill documentation

## Commands

- `just lsd-parse <path>` - Parse directory and output JSON
- `just demo <path>` - Pretty print JSON output with jq
- `just test-json-valid <path>` - Validate JSON output
- `just count <path>` - Count entries
- `just names <path>` - List filenames

## Project Structure

```
fileman/
  scripts/
    lsd-json                # Simple wrapper script
  .skills/                  # Skill documentation
  Justfile                  # Task automation
  devenv.yaml               # Parser import
  devenv.nix                # Package management
  README.md
  CONCEPT_MVP_LSD.md
  AGENTS.md
```

## Key Advantage

**No complex setup!** Parser is pre-built and imported - just use it.

Setup time: **15 minutes**
