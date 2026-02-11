default:
  @just --list

# Scan directory and write JSON output
scan PATH=".":
  fileman scan {{PATH}}

# List entries from saved JSON
list INPUT="filetree.json":
  fileman list {{INPUT}}

# Show detailed formatted output
show INPUT="filetree.json":
  fileman show {{INPUT}}

# Validate JSON output with jq
validate INPUT="filetree.json":
  jq empty {{INPUT}}

# Count total entries in output JSON
count INPUT="filetree.json":
  jq '.entries | length' {{INPUT}}
