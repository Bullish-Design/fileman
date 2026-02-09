# fileman.just — import from a repo's Justfile
# Usage:
#   import ".devman/fileman/just/fileman.just"
#
# Then run:
#   just fileman:snapshot

fileman:snapshot root="." out=".devman/out/fileman/snapshot.jsonl" depth="" include_hidden="false":
  mkdir -p .devman/out/fileman

  if [ "${DEV_MAN_SIMULATE:-0}" = "1" ]; then     echo "[simulate] would run fileman snapshot --root {{root}} --out {{out}} --jsonl";     echo "DEV_MAN_ARTIFACT: {{out}}";     exit 0;   fi

  EXTRA=""
  if [ -n "{{depth}}" ]; then EXTRA="$EXTRA --depth {{depth}}"; fi
  if [ "{{include_hidden}}" = "true" ]; then EXTRA="$EXTRA --include-hidden"; fi

  fileman snapshot --root "{{root}}" --out "{{out}}" --jsonl --print $EXTRA

  echo "DEV_MAN_ARTIFACT: {{out}}"
